"""Privacidad: toda decisión se guarda en la bitácora de la base, en la misma transacción que su efecto.

El navegador se identifica con un valor firmado por el servidor, nunca con un ID
aceptado de la petición. Sin decisión válida, las estadísticas no se cuentan.
Datos mínimos (ASVS V14): IP recortada y navegador resumido, nunca el user-agent completo.
"""
import hashlib
import hmac
import ipaddress
import re
import secrets

from allauth.account.adapter import get_adapter
from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, connection, transaction
from django.middleware.csrf import rotate_token
from django.utils import timezone

from datos.services import aceptaciones_pendientes, auditar, capabilities, identity
from huerto.models import Huerto
from web import validacion as v
from web.respuestas import ReglaDeNegocio

from . import politicas
from .documentos_html import sanear_html
from .models import Decision, DocumentoLegal, Finalidad, Preferencia, Sujeto

COOKIE_PREFERENCIA = 'chilito_preferencia'
COOKIE_ESTADISTICA = 'chilito_estadistica'
SAL_PREFERENCIA = 'privacidad.preferencia'
SAL_ESTADISTICA = 'privacidad.estadistica'
MAXIMO_SUJETOS_NAVEGADOR = 10
SECCIONES = frozenset(('inicio', 'proyecto', 'prototipo', 'funcionamiento', 'huerto', 'panel_tecnico',
                       'mantenimiento', 'soporte', 'avisos', 'cuenta', 'privacidad'))
DOCUMENTOS_PUBLICOS = {'privacidad': 'aviso_privacidad', 'terminos': 'terminos', 'cookies': 'politica_cookies'}
CAMPOS = {'firstName': ('first_name', 60), 'lastName': ('last_name', 60), 'alias': ('alias', 64)}
NAVEGADORES = (('Edge', r'Edg(?:e|A|iOS)?/(\d+)'), ('Opera', r'OPR/(\d+)'), ('Firefox', r'(?:Firefox|FxiOS)/(\d+)'),
               ('Chrome', r'(?:Chrome|CriOS)/(\d+)'), ('Safari', r'Version/(\d+)[^ ]* (?:Mobile/\S+ )?Safari'))
SISTEMAS = (('Android', 'Android'), ('iOS', 'iPhone|iPad'), ('Windows', 'Windows'), ('macOS', 'Macintosh'),
            ('ChromeOS', 'CrOS'), ('Linux', 'Linux'))


def ip_recortada(request):
    """IPv4 con el último bloque en 0; IPv6 recortada a /48. Vacío si no hay una IP válida."""
    try:
        ip = ipaddress.ip_address(get_adapter().get_client_ip(request))
    except (PermissionDenied, ValueError):
        return ''
    if ip.version == 4:
        return '.'.join(str(ip).split('.')[:3] + ['0'])
    return str(ipaddress.ip_network(f'{ip}/48', strict=False).network_address)


def navegador_resumido(request):
    """«Chrome 130 · Android». El user-agent completo no se guarda."""
    agente = request.META.get('HTTP_USER_AGENT', '')[:512]
    navegador = next((f'{nombre} {m.group(1)}' for nombre, patron in NAVEGADORES if (m := re.search(patron, agente))), 'Otro')
    sistema = next((nombre for nombre, patron in SISTEMAS if re.search(patron, agente)), 'Otro')
    return f'{navegador} · {sistema}'


def documento_vigente(tipo):
    """Última versión publicada del tipo; la base decide cuál es."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT chilito_documento_vigente(%s)', [tipo])
        identificador = cursor.fetchone()[0]
    return DocumentoLegal.objects.filter(pk=identificador).first() if identificador else None


def texto_vigente(publico):
    """Versión vigente del texto legal, saneada con la lista blanca. Solo se leen los tipos del catálogo fijo."""
    tipo = DOCUMENTOS_PUBLICOS.get(publico)
    documento = documento_vigente(tipo) if tipo else None
    if documento is None:
        return None
    html, texto = sanear_html(documento.contenido)
    return {'version': documento.version, 'registered': True, 'text': texto, 'html': html, 'draft': False}


def _firmado(valor, sal, vigencia):
    if not isinstance(valor, str) or not valor:
        return None
    try:
        return signing.loads(valor, salt=sal, max_age=vigencia)
    except signing.BadSignature:
        return None


def _ids_navegador(valor):
    """Sujetos que recuerda este navegador, del más reciente al más antiguo: el anónimo y uno por cuenta que decidió aquí.
    Acepta el formato anterior de la cookie (un solo id)."""
    contenido = _firmado(valor, SAL_PREFERENCIA, politicas.PREFERENCIA_COOKIES_SEGUNDOS)
    ids = [contenido] if isinstance(contenido, str) else contenido if isinstance(contenido, list) else []
    return [identificador for identificador in ids if isinstance(identificador, str)][:MAXIMO_SUJETOS_NAVEGADOR]


def _sujetos_navegador(valor, *, bloquear=False):
    ids = _ids_navegador(valor)
    if not ids:
        return []
    consulta = Sujeto.objects.select_for_update() if bloquear else Sujeto.objects
    encontrados = {str(sujeto.pk): sujeto for sujeto in consulta.filter(pk__in=ids, ambito='navegador')}
    return [encontrados[identificador] for identificador in ids if identificador in encontrados]


def _usuario_id(actor):
    return actor.pk if getattr(actor, 'is_authenticated', False) else None


def _sujeto_vigente(valor, actor, *, bloquear=False):
    """Sujeto cuya decisión aplica a este navegador: consultar y contar.

    La preferencia es del navegador y sobrevive al cierre de sesión (sin sesión vale la más reciente). Con sesión vale
    la de la cuenta; si la cuenta aún no decidió aquí, la del navegador sin cuenta. Nunca la de otra cuenta.
    """
    sujetos = _sujetos_navegador(valor, bloquear=bloquear)
    usuario_id = _usuario_id(actor)
    if usuario_id is None:
        return sujetos[0] if sujetos else None
    return (next((sujeto for sujeto in sujetos if sujeto.usuario_id == usuario_id), None)
            or next((sujeto for sujeto in sujetos if sujeto.usuario_id is None), None))


def _sujeto_para_decidir(valor, actor):
    """Sujeto que registra una decisión nueva: el de la cuenta con sesión, o el anónimo sin ella.
    El anónimo no se vincula a una cuenta: sus decisiones siguen siendo de un visitante anónimo en la bitácora."""
    usuario_id = _usuario_id(actor)
    return next((sujeto for sujeto in _sujetos_navegador(valor, bloquear=True) if sujeto.usuario_id == usuario_id), None)


def _finalidad():
    return Finalidad.objects.get(codigo=politicas.FINALIDAD_ESTADISTICAS)


def _preferencia(sujeto, politica):
    """Decisión vigente, o None si venció o la política de cookies cambió."""
    preferencia = Preferencia.objects.select_related('decision').filter(sujeto=sujeto, finalidad=_finalidad()).first()
    if preferencia is None or politica is None:
        return None
    decision = preferencia.decision
    edad = (timezone.now() - decision.registrada_en).total_seconds()
    if decision.documento_id != politica.pk or edad >= politicas.PREFERENCIA_COOKIES_SEGUNDOS:
        return None
    return decision


def estado_cookies(valor, actor=None):
    sujeto = _sujeto_vigente(valor, actor)
    politica, aviso = documento_vigente('politica_cookies'), documento_vigente('aviso_privacidad')
    decision = _preferencia(sujeto, politica) if sujeto else None
    return {'decided': decision is not None, 'statistics': bool(decision and decision.decision),
            'privacyVersion': aviso.version if aviso else None, 'cookiesVersion': politica.version if politica else None}


@transaction.atomic
def decidir_cookies(request, valor, acepta):
    """Devuelve el valor firmado que recuerda a este navegador."""
    if not isinstance(acepta, bool):
        raise ValidationError('Decisión no válida')
    politica = documento_vigente('politica_cookies')
    if politica is None:
        raise ValidationError('Política de cookies no publicada')
    actor = request.user
    usuario = identity(actor) if getattr(actor, 'is_authenticated', False) else None
    sujeto = _sujeto_para_decidir(valor, actor)
    if sujeto is None:
        sujeto = Sujeto.objects.create(ambito='navegador', usuario=usuario)
    finalidad = _finalidad()
    decision = Decision.objects.create(sujeto=sujeto, acto='cookies', decision=acepta, documento=politica, finalidad=finalidad,
                                       usuario=usuario, ip_recortada=ip_recortada(request),
                                       navegador=navegador_resumido(request))
    actualizadas = Preferencia.objects.filter(sujeto=sujeto, finalidad=finalidad).update(
        decision=decision, actualizada_en=timezone.now())
    if not actualizadas:
        Preferencia.objects.create(sujeto=sujeto, finalidad=finalidad, decision=decision)
    otros = [identificador for identificador in _ids_navegador(valor) if identificador != str(sujeto.pk)]
    return signing.dumps([str(sujeto.pk), *otros][:MAXIMO_SUJETOS_NAVEGADOR], salt=SAL_PREFERENCIA)


def nuevo_identificador():
    return signing.dumps(secrets.token_urlsafe(16), salt=SAL_ESTADISTICA)


def identificador_valido(valor):
    return _firmado(valor, SAL_ESTADISTICA, politicas.IDENTIFICADOR_ESTADISTICAS_SEGUNDOS)


@transaction.atomic
def contar_seccion(actor, valor_preferencia, identificador, seccion):
    """Cuenta una visita por sección e identificador. Sin consentimiento vigente, no cuenta."""
    if seccion not in SECCIONES:
        raise ValidationError('Sección no válida')
    sujeto = _sujeto_vigente(valor_preferencia, actor, bloquear=True)
    decision = _preferencia(sujeto, documento_vigente('politica_cookies')) if sujeto else None
    if decision is None or decision.decision is not True or identificador is None:
        return False
    resumen = hmac.new(settings.SECRET_KEY.encode(), f'{identificador}:{seccion}'.encode(), hashlib.sha256).hexdigest()
    if not cache.add(f'estadistica:{resumen}', 1, politicas.IDENTIFICADOR_ESTADISTICAS_SEGUNDOS):
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO conteo_navegacion(dia,seccion,visitas) VALUES(%s,%s,1) '
            'ON CONFLICT(dia,seccion) DO UPDATE SET visitas=conteo_navegacion.visitas+1',
            [timezone.localdate(), seccion])
    return True


class TextosLegalesNoPublicados(ValidationError):
    """No hay términos o aviso de privacidad publicados: el registro está cerrado hasta publicarlos."""

    def __init__(self):
        super().__init__('Textos legales no publicados', code='legal-no-publicado')


ACTOS_DE_REGISTRO = (('aceptacion_terminos', 'terminos'), ('lectura_aviso', 'aviso_privacidad'))


def textos_de_registro_publicados():
    return all(documento_vigente(tipo) is not None for _, tipo in ACTOS_DE_REGISTRO)


def arranque_legal_permitido():
    """Arranque inicial: CHILITO_BYPASS_LEGAL_CHECK activo, sin textos de registro publicados y sin ninguna cuenta.
    La base (web.0008) repite las tres condiciones; con textos publicados u otra cuenta, la variable no tiene efecto."""
    return (getattr(settings, 'CHILITO_BYPASS_LEGAL_CHECK', False) and not textos_de_registro_publicados()
            and not get_user_model().objects.exists())


def registrar_actos_de_registro(usuario, request):
    """Guarda por separado la aceptación de términos y la lectura del aviso, con su versión vigente.

    Debe llamarse dentro de la transacción que crea la cuenta. Sin un documento vigente la
    base lo rechaza y la cuenta no se crea: no se registra un acto sin versión.

    Única excepción, el arranque inicial (`arranque_legal_permitido`, ya con la cuenta nueva como la única): se crea el
    sujeto sin actos y se avisa a la base para esta transacción. Los textos quedan pendientes de aceptar al publicarse.
    """
    documentos = [(acto, documento_vigente(tipo)) for acto, tipo in ACTOS_DE_REGISTRO]
    if any(documento is None for _, documento in documentos):
        unica = not get_user_model().objects.exclude(pk=usuario.pk).exists()
        if not (getattr(settings, 'CHILITO_BYPASS_LEGAL_CHECK', False) and unica):
            raise TextosLegalesNoPublicados
        Sujeto.objects.create(ambito='cuenta', usuario=usuario)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('chilito.arranque_legal', 'on', true)")
        return
    sujeto = Sujeto.objects.create(ambito='cuenta', usuario=usuario)
    for acto, documento in documentos:
        Decision.objects.create(sujeto=sujeto, acto=acto, decision=True, documento=documento, usuario=usuario,
                                ip_recortada=ip_recortada(request), navegador=navegador_resumido(request))


ACTO_POR_TIPO = {'terminos': 'aceptacion_terminos', 'aviso_privacidad': 'lectura_aviso'}


@transaction.atomic
def aceptar_textos(actor, documentos, request):
    """Guarda la aceptación de textos vigentes. Solo valen los que la base marca como pendientes para esta cuenta."""
    usuario = identity(actor)
    if (not isinstance(documentos, list) or not 1 <= len(documentos) <= len(ACTO_POR_TIPO)
            or not all(isinstance(identificador, str) for identificador in documentos)
            or len(set(documentos)) != len(documentos)):
        raise ValidationError('Documentos no válidos')
    pendientes = {pendiente['documentId']: pendiente for pendiente in aceptaciones_pendientes(usuario)}
    if not set(documentos) <= set(pendientes):
        raise ValidationError('Documento no pendiente')
    sujeto = Sujeto.objects.get(usuario=usuario, ambito='cuenta')
    for identificador in documentos:
        Decision.objects.create(sujeto=sujeto, acto=ACTO_POR_TIPO[pendientes[identificador]['type']], decision=True,
                                documento=DocumentoLegal.objects.get(pk=identificador), usuario=usuario,
                                ip_recortada=ip_recortada(request), navegador=navegador_resumido(request))
    auditar(usuario, 'aceptar_legales', entidad='documento_legal',
            detalle={'tipos': sorted(pendientes[identificador]['type'] for identificador in documentos)})
    return {'status': 'accepted', 'pendingLegal': aceptaciones_pendientes(usuario)}


MAXIMO_ACEPTACIONES = 50


def aceptaciones(actor):
    """Documentos que la cuenta aceptó: título, versión y fecha de cada decisión."""
    usuario = identity(actor)
    decisiones = (Decision.objects.filter(usuario=usuario, acto__in=ACTO_POR_TIPO.values())
                  .select_related('documento').order_by('-registrada_en')[:MAXIMO_ACEPTACIONES])
    return {'status': 'ready', 'items': [{'type': decision.documento.tipo, 'title': decision.documento.titulo,
                                          'version': decision.documento.version, 'at': decision.registrada_en.isoformat()}
                                         for decision in decisiones]}


class CuentaAdministrativa(ReglaDeNegocio):
    def __init__(self):
        super().__init__('cuenta-administrativa', 'Tu cuenta tiene capacidades de administración. Pide que te las retiren '
                                                  'antes de eliminarla.')


class CuentaConHistorialAdministrativo(ReglaDeNegocio):
    def __init__(self):
        super().__init__('cuenta-con-historial-administrativo', 'Tu cuenta atendió registros de otras personas y no puede '
                                                                'eliminarse desde aquí. Escribe a soporte.')


def _cerrar_otras_sesiones(usuario_id):
    """Borra las sesiones guardadas de la cuenta (otros navegadores). La de esta petición la vacía quien llama.

    También las caducadas: aún guardan el id y la huella de la contraseña de la cuenta hasta la purga periódica, que las
    mantiene pocas."""
    ajenas = [sesion.pk for sesion in Session.objects.iterator() if str(sesion.get_decoded().get(SESSION_KEY)) == str(usuario_id)]
    Session.objects.filter(pk__in=ajenas).delete()


@transaction.atomic
def eliminar_cuenta(request, password):
    """Borra la cuenta y todo lo suyo, de inmediato y sin vuelta atrás (chilito_eliminar_cuenta, en la base).

    Exige la contraseña actual. No admite cuentas con capacidades, lo que incluye al último superadministrador. La sesión
    se cierra en esta misma transacción. No se registra nada que identifique a la persona: el correo no va a los logs."""
    usuario = get_user_model().objects.select_for_update().get(pk=identity(request.user).pk)
    if not isinstance(password, str) or not 0 < len(password) <= 256 or not usuario.check_password(password):
        raise ValidationError('Contraseña no válida')
    if capabilities(usuario):
        raise CuentaAdministrativa
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SELECT chilito_eliminar_cuenta(%s)', [usuario.pk])
    except DatabaseError as fallo:
        mensaje = getattr(getattr(getattr(fallo, '__cause__', None), 'diag', None), 'message_primary', '') or ''
        if mensaje.startswith('La cuenta tiene historial administrativo'):
            raise CuentaConHistorialAdministrativo from None
        if mensaje.startswith('Una cuenta con capacidades'):
            raise CuentaAdministrativa from None
        raise
    _cerrar_otras_sesiones(usuario.pk)
    # Sin user_logged_out: sus receptores volverían a fijar como actor a la cuenta que ya no existe.
    request.session.flush()
    request.user = AnonymousUser()
    rotate_token(request)
    return {'status': 'deleted', 'message': 'Tu cuenta y todos sus datos se eliminaron definitivamente.'}


def _limpiar(datos):
    """Nombre y apellido: nombre de persona (2 a 60, o vacío para borrarlo). Alias: nombre de cosa (hasta 64, o vacío)."""
    limpios = {}
    for clave, (campo, maximo) in CAMPOS.items():
        if clave not in datos:
            continue
        valor = datos[clave]
        if not isinstance(valor, str):
            raise v.CampoInvalido(clave, 'texto-no-valido', 'Escribe un texto.')
        limpios[campo] = (v.nombre_cosa(valor, clave, maximo=maximo, requerido=False) if clave == 'alias'
                          else v.nombre_persona(valor, clave, requerido=False, maximo=maximo))
    return limpios


def _aplicar_perfil(usuario, datos):
    cambios = {campo: valor for campo, valor in _limpiar(datos).items() if getattr(usuario, campo) != valor}
    if cambios:
        for campo, valor in cambios.items():
            setattr(usuario, campo, valor)
        usuario.save(update_fields=list(cambios))
        for campo in cambios:
            # Se registra qué campo cambió, nunca sus valores.
            auditar(usuario, 'rectificar_perfil', entidad='cuenta', entidad_id=usuario.pk, detalle={'campo': campo})


def _bloqueado(actor):
    return get_user_model().objects.select_for_update().get(pk=identity(actor).pk)


@transaction.atomic
def rectificar_perfil(actor, datos):
    usuario = _bloqueado(actor)
    _aplicar_perfil(usuario, datos)
    return usuario


@transaction.atomic
def atender_bienvenida(actor, datos):
    """«Ahora no» llega sin datos y también cierra el paso. Nunca es un consentimiento."""
    usuario = _bloqueado(actor)
    _aplicar_perfil(usuario, datos)
    if usuario.bienvenida_atendida_en is None:
        usuario.bienvenida_atendida_en = timezone.now()
        usuario.save(update_fields=['bienvenida_atendida_en'])
    return usuario


@transaction.atomic
def consultar_mis_datos(actor):
    usuario = identity(actor)
    auditar(usuario, 'consultar_mis_datos', entidad='cuenta', entidad_id=usuario.pk)
    huertos = Huerto.objects.filter(propietario=usuario, estado='activo').order_by('id')
    return {'email': usuario.email, 'firstName': usuario.first_name, 'lastName': usuario.last_name,
            'alias': usuario.alias, 'createdAt': usuario.date_joined.isoformat(),
            'gardens': [huerto.nombre for huerto in huertos]}
