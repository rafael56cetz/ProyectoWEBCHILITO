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
from datetime import timedelta

from allauth.account.adapter import get_adapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.utils import timezone

from datos.services import DIAS_PARA_ELIMINAR, aceptaciones_pendientes, auditar, identity
from huerto.models import Huerto

from . import politicas
from .documentos_html import sanear_html
from .models import Decision, DocumentoLegal, Finalidad, Preferencia, Sujeto

COOKIE_PREFERENCIA = 'chilito_preferencia'
COOKIE_ESTADISTICA = 'chilito_estadistica'
SAL_PREFERENCIA = 'privacidad.preferencia'
SAL_ESTADISTICA = 'privacidad.estadistica'
SECCIONES = frozenset(('inicio', 'proyecto', 'prototipo', 'funcionamiento', 'huerto', 'panel_tecnico',
                       'mantenimiento', 'soporte', 'avisos', 'cuenta', 'privacidad'))
DOCUMENTOS_PUBLICOS = {'privacidad': 'aviso_privacidad', 'terminos': 'terminos', 'cookies': 'politica_cookies'}
CAMPOS = {'firstName': ('first_name', 150), 'lastName': ('last_name', 150), 'alias': ('alias', 64)}
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


def _sujeto_navegador(valor, *, bloquear=False):
    identificador = _firmado(valor, SAL_PREFERENCIA, politicas.PREFERENCIA_COOKIES_SEGUNDOS)
    consulta = Sujeto.objects.select_for_update() if bloquear else Sujeto.objects
    return consulta.filter(pk=identificador, ambito='navegador').first() if identificador else None


def _usuario_id(actor):
    return actor.pk if getattr(actor, 'is_authenticated', False) else None


def _sujeto_vigente(valor, actor, *, bloquear=False):
    """Sujeto cuya decisión aplica a este navegador: consultar y contar.

    La preferencia es del navegador y sobrevive al cierre de sesión. Lo único que no
    se hereda es la decisión vinculada a otra cuenta que esté con sesión abierta.
    """
    sujeto = _sujeto_navegador(valor, bloquear=bloquear)
    usuario_id = _usuario_id(actor)
    ajeno = sujeto is not None and usuario_id is not None and sujeto.usuario_id not in (None, usuario_id)
    return None if ajeno else sujeto


def _sujeto_para_decidir(valor, actor):
    """Sujeto que puede registrar una decisión nueva: la base exige que la cuenta coincida con el titular."""
    sujeto = _sujeto_navegador(valor, bloquear=True)
    return sujeto if sujeto is not None and sujeto.usuario_id in (None, _usuario_id(actor)) else None


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
    elif usuario is not None and sujeto.usuario_id is None:
        sujeto.usuario = usuario
        sujeto.save(update_fields=['usuario'])
    finalidad = _finalidad()
    decision = Decision.objects.create(sujeto=sujeto, acto='cookies', decision=acepta, documento=politica, finalidad=finalidad,
                                       usuario=usuario, ip_recortada=ip_recortada(request),
                                       navegador=navegador_resumido(request))
    actualizadas = Preferencia.objects.filter(sujeto=sujeto, finalidad=finalidad).update(
        decision=decision, actualizada_en=timezone.now())
    if not actualizadas:
        Preferencia.objects.create(sujeto=sujeto, finalidad=finalidad, decision=decision)
    return signing.dumps(str(sujeto.pk), salt=SAL_PREFERENCIA)


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


def registrar_actos_de_registro(usuario, request):
    """Guarda por separado la aceptación de términos y la lectura del aviso, con su versión vigente.

    Debe llamarse dentro de la transacción que crea la cuenta. Sin un documento vigente la
    base lo rechaza y la cuenta no se crea: no se registra un acto sin versión.
    """
    sujeto = Sujeto.objects.create(ambito='cuenta', usuario=usuario)
    for acto, tipo in (('aceptacion_terminos', 'terminos'), ('lectura_aviso', 'aviso_privacidad')):
        documento = documento_vigente(tipo)
        if documento is None:
            raise ValidationError('Textos legales no publicados')
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


def _plazo(momento):
    return (momento + timedelta(days=DIAS_PARA_ELIMINAR)).isoformat()


@transaction.atomic
def solicitar_eliminacion(actor, password):
    """Pide borrar la cuenta; la base la anonimiza a los 15 días. Exige la contraseña y siempre fija `now()`."""
    usuario = get_user_model().objects.select_for_update().get(pk=identity(actor).pk)
    if not isinstance(password, str) or not 0 < len(password) <= 256 or not usuario.check_password(password):
        raise ValidationError('Contraseña no válida')
    if usuario.anonimizacion_solicitada_en is None:
        usuario.anonimizacion_solicitada_en = timezone.now()
        usuario.save(update_fields=['anonimizacion_solicitada_en'])
        auditar(usuario, 'solicitar_eliminacion', entidad='cuenta', entidad_id=usuario.pk)
    return {'status': 'accepted', 'deletionRequestedAt': usuario.anonimizacion_solicitada_en.isoformat(),
            'deletionDate': _plazo(usuario.anonimizacion_solicitada_en)}


@transaction.atomic
def cancelar_eliminacion(actor):
    usuario = get_user_model().objects.select_for_update().get(pk=identity(actor).pk)
    if usuario.anonimizacion_solicitada_en is None or usuario.anonimizada_en is not None:
        raise ValidationError('No hay una eliminación que cancelar')
    usuario.anonimizacion_solicitada_en = None
    usuario.save(update_fields=['anonimizacion_solicitada_en'])
    auditar(usuario, 'cancelar_eliminacion', entidad='cuenta', entidad_id=usuario.pk)
    return {'status': 'accepted'}


def _limpiar(datos):
    limpios = {}
    for clave, (campo, maximo) in CAMPOS.items():
        if clave not in datos:
            continue
        valor = datos[clave]
        if not isinstance(valor, str) or len(valor) > maximo or not valor.isprintable():
            raise ValidationError('Texto no válido')
        limpios[campo] = valor.strip()
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
