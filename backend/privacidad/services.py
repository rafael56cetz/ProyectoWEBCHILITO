"""Privacidad: toda decisión y su evento se guardan en la misma transacción.

El navegador se identifica con un valor firmado por el servidor, nunca con un ID
aceptado de la petición. Sin decisión válida, las estadísticas no se cuentan.
"""
import hashlib
import hmac
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from datos.services import identity
from huerto.models import Membresia

from . import politicas
from .documentos_html import sanear_html
from .models import (ConteoNavegacion, DecisionPrivacidad, DocumentoVersion, EventoPrivacidad,
                     FinalidadOpcional, PreferenciaFinalidad, SujetoPrivacidad)

COOKIE_PREFERENCIA = 'chilito_preferencia'
COOKIE_ESTADISTICA = 'chilito_estadistica'
SAL_PREFERENCIA = 'privacidad.preferencia'
SAL_ESTADISTICA = 'privacidad.estadistica'
SECCIONES = frozenset(codigo for codigo, _ in ConteoNavegacion.SECCIONES)
DOCUMENTOS_PUBLICOS = {'privacidad': 'aviso_privacidad', 'terminos': 'terminos', 'cookies': 'politica_cookies'}
CARPETA_HTML = Path(settings.PROJECT_ROOT, 'frontend', 'legales')
ARCHIVOS_HTML = {'privacidad': 'aviso-privacidad.html', 'terminos': 'terminos.html', 'cookies': 'politica-cookies.html'}
CAMPOS = {'firstName': ('first_name', 150), 'lastName': ('last_name', 150), 'alias': ('alias', 64)}


def documento_vigente(tipo):
    return DocumentoVersion.objects.filter(tipo=tipo).order_by('-registrado_en', '-version').first()


def texto_vigente(publico):
    """Lee el HTML editable de frontend/legales en cada petición.

    Solo los nombres del catálogo fijo pueden leerse. La huella corresponde a los
    bytes originales: guardar una edición no la convierte en una versión registrada.
    """
    tipo = DOCUMENTOS_PUBLICOS.get(publico)
    if tipo is None:
        return None
    ruta = CARPETA_HTML / ARCHIVOS_HTML[publico]
    contenido = ruta.read_bytes() if ruta.is_file() else b''
    html, texto = sanear_html(contenido.decode('utf-8', errors='replace'))
    documento = documento_vigente(tipo)
    registrado = documento is not None and hashlib.sha256(contenido).hexdigest() == documento.contenido_sha256
    return {'version': documento.version if registrado else None, 'registered': registrado,
            'text': texto, 'html': html,
            'draft': not registrado or 'borrador' in documento.version}


def _firmado(valor, sal, vigencia):
    if not isinstance(valor, str) or not valor:
        return None
    try:
        return signing.loads(valor, salt=sal, max_age=vigencia)
    except signing.BadSignature:
        return None


def _sujeto_navegador(valor, *, bloquear=False):
    identificador = _firmado(valor, SAL_PREFERENCIA, politicas.PREFERENCIA_COOKIES_SEGUNDOS)
    consulta = SujetoPrivacidad.objects.select_for_update() if bloquear else SujetoPrivacidad.objects
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
    """Sujeto que puede registrar una decisión nueva: el evento exige actor igual al titular."""
    sujeto = _sujeto_navegador(valor, bloquear=True)
    return sujeto if sujeto is not None and sujeto.usuario_id in (None, _usuario_id(actor)) else None


def _finalidad():
    return FinalidadOpcional.objects.get(codigo=politicas.FINALIDAD_ESTADISTICAS)


def _preferencia(sujeto):
    """Decisión vigente, o None si venció o cambió algún documento."""
    preferencia = (PreferenciaFinalidad.objects.select_related('decision')
                   .filter(sujeto=sujeto, finalidad=_finalidad()).first())
    if preferencia is None:
        return None
    decision = preferencia.decision
    aviso, politica = documento_vigente('aviso_privacidad'), documento_vigente('politica_cookies')
    edad = (timezone.now() - decision.registrada_en).total_seconds()
    if (decision.acto != 'cookies' or decision.documento_id != aviso.pk
            or decision.politica_cookies_id != politica.pk or edad >= politicas.PREFERENCIA_COOKIES_SEGUNDOS):
        return None
    return decision


def estado_cookies(valor, actor=None):
    sujeto = _sujeto_vigente(valor, actor)
    decision = _preferencia(sujeto) if sujeto else None
    aviso, politica = documento_vigente('aviso_privacidad'), documento_vigente('politica_cookies')
    return {'decided': decision is not None, 'statistics': bool(decision and decision.decision),
            'privacyVersion': aviso.version, 'cookiesVersion': politica.version}


@transaction.atomic
def decidir_cookies(actor, valor, acepta):
    """Devuelve el valor firmado que recuerda a este navegador."""
    if not isinstance(acepta, bool):
        raise ValidationError('Decisión no válida')
    usuario = identity(actor) if getattr(actor, 'is_authenticated', False) else None
    sujeto = _sujeto_para_decidir(valor, actor)
    if sujeto is None:
        sujeto = SujetoPrivacidad.objects.create(ambito='navegador', usuario=usuario)
    elif usuario is not None and sujeto.usuario_id is None:
        sujeto.usuario = usuario
        sujeto.save(update_fields=['usuario'])
    finalidad = _finalidad()
    decision = DecisionPrivacidad.objects.create(
        sujeto=sujeto, documento=documento_vigente('aviso_privacidad'),
        politica_cookies=documento_vigente('politica_cookies'), finalidad=finalidad,
        acto='cookies', decision=acepta)
    actualizadas = PreferenciaFinalidad.objects.filter(sujeto=sujeto, finalidad=finalidad).update(
        decision=decision, actualizada_en=timezone.now())
    if not actualizadas:
        PreferenciaFinalidad.objects.create(sujeto=sujeto, finalidad=finalidad, decision=decision)
    # La oposición exige actor: sin sesión queda como decisión de rechazo.
    accion = 'oposicion' if usuario is not None and not acepta else 'decision'
    EventoPrivacidad.objects.create(sujeto=sujeto, actor=usuario, accion=accion, resultado='completado',
                                    decision=decision, finalidad=finalidad)
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
    decision = _preferencia(sujeto) if sujeto else None
    if decision is None or decision.decision is not True or identificador is None:
        return False
    resumen = hmac.new(settings.SECRET_KEY.encode(), f'{identificador}:{seccion}'.encode(), hashlib.sha256).hexdigest()
    if not cache.add(f'estadistica:{resumen}', 1, politicas.IDENTIFICADOR_ESTADISTICAS_SEGUNDOS):
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO public.privacidad_conteonavegacion(dia,seccion,visitas) VALUES(%s,%s,1) '
            'ON CONFLICT(dia,seccion) DO UPDATE SET visitas=privacidad_conteonavegacion.visitas+1',
            [timezone.localdate(), seccion])
    return True


def _sujeto_cuenta(usuario):
    return SujetoPrivacidad.objects.get_or_create(usuario=usuario, ambito='cuenta')[0]


def registrar_actos_de_registro(usuario):
    """Guarda por separado la aceptación de términos y la lectura del aviso, con su versión.

    Debe llamarse dentro de la transacción que crea la cuenta. Sin un documento vigente la
    base lo rechaza y la cuenta no se crea: no se registra un acto sin versión.
    """
    sujeto = _sujeto_cuenta(usuario)
    for acto, tipo in (('aceptacion_terminos', 'terminos'), ('lectura_aviso', 'aviso_privacidad')):
        decision = DecisionPrivacidad.objects.create(
            sujeto=sujeto, documento=documento_vigente(tipo), acto=acto, decision=True)
        EventoPrivacidad.objects.create(sujeto=sujeto, actor=usuario, accion='decision',
                                        resultado='completado', decision=decision)


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
        sujeto = _sujeto_cuenta(usuario)
        for campo in cambios:
            # Se registra qué campo cambió, nunca sus valores.
            EventoPrivacidad.objects.create(sujeto=sujeto, actor=usuario, accion='rectificacion',
                                            resultado='completado', campo=campo)


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
    EventoPrivacidad.objects.create(sujeto=_sujeto_cuenta(usuario), actor=usuario, accion='acceso', resultado='completado')
    huertos = Membresia.objects.filter(usuario=usuario, activa=True).select_related('huerto')
    return {'email': usuario.email, 'firstName': usuario.first_name, 'lastName': usuario.last_name,
            'alias': usuario.alias, 'createdAt': usuario.date_joined.isoformat(),
            'gardens': [m.huerto.nombre for m in huertos]}
