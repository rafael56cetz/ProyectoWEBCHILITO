"""Transporte JSON de privacidad. Reglas y autorización: privacidad/services.py."""
import logging

from allauth.core import ratelimit
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from privacidad import consentimientos, legales, politicas, services
from web.api import InputError, body, bounds, endpoint, failure
from web.respuestas import respuesta_de_base

logger = logging.getLogger(__name__)
CAMPOS_PERFIL = tuple(services.CAMPOS)


def _cookie(respuesta, nombre, valor, vigencia):
    respuesta.set_cookie(nombre, valor, max_age=vigencia, httponly=True, samesite='Lax',
                         secure=settings.SESSION_COOKIE_SECURE)


def _publica(vista):
    """Rutas sin sesión: errores genéricos, cuerpo validado y sin revelar detalles."""
    def envuelta(request, *args, **kwargs):
        try:
            return vista(request, *args, **kwargs)
        except (InputError, ValueError, TypeError, ValidationError, UnicodeError, RecursionError):
            return failure(400, 'invalid-input')
        except DatabaseError as fallo:
            logger.exception('privacidad-no-disponible')
            return respuesta_de_base(fallo) or failure(503, 'service-unavailable')
    return envuelta


@endpoint(('POST',), CAMPOS_PERFIL)
def profile(request, data):
    services.rectificar_perfil(request.user, data)
    return {'status': 'accepted'}


@endpoint(('POST',), CAMPOS_PERFIL)
def welcome(request, data):
    services.atender_bienvenida(request.user, data)
    return {'status': 'accepted'}


@endpoint(('POST',))
def my_data(request, data):
    return {'status': 'accepted', 'data': services.consultar_mis_datos(request.user)}


@never_cache
@require_GET
@_publica
def document(request, kind):
    documento = services.texto_vigente(kind)
    return JsonResponse({'status': 'ready', **documento}) if documento else failure(404, 'not-found')


@never_cache
@require_http_methods(['GET', 'POST'])
@_publica
def cookies(request):
    valor = request.COOKIES.get(services.COOKIE_PREFERENCIA)
    if request.method == 'GET':
        return JsonResponse({'status': 'ready', **services.estado_cookies(valor, request.user)})
    if not ratelimit.consume(request, action='privacidad_cookies'):
        return failure(429, 'rate-limited')
    acepta = body(request, ('statistics',)).get('statistics')
    firmado = services.decidir_cookies(request, valor, acepta)
    respuesta = JsonResponse({'status': 'accepted', 'statistics': acepta})
    _cookie(respuesta, services.COOKIE_PREFERENCIA, firmado, politicas.PREFERENCIA_COOKIES_SEGUNDOS)
    if not acepta:
        respuesta.delete_cookie(services.COOKIE_ESTADISTICA, samesite='Lax')
    return respuesta


@never_cache
@require_http_methods(['POST'])
@_publica
def section(request):
    if not ratelimit.consume(request, action='estadistica_seccion'):
        return failure(429, 'rate-limited')
    seccion = body(request, ('section',)).get('section')
    identificador = services.identificador_valido(request.COOKIES.get(services.COOKIE_ESTADISTICA))
    nuevo = None if identificador else services.nuevo_identificador()
    contada = services.contar_seccion(request.user, request.COOKIES.get(services.COOKIE_PREFERENCIA),
                                      identificador or services.identificador_valido(nuevo), seccion)
    respuesta = JsonResponse({'status': 'accepted', 'counted': contada})
    # Solo existe tras un permiso válido, que contar_seccion ya comprobó.
    if contada and nuevo:
        _cookie(respuesta, services.COOKIE_ESTADISTICA, nuevo, politicas.IDENTIFICADOR_ESTADISTICAS_SEGUNDOS)
    return respuesta


@endpoint()
def acceptances(request, data):
    bounds(request, allowed=())
    return services.aceptaciones(request.user)


@endpoint(('POST',), ('password',))
def _delete_account(request, data):
    return services.solicitar_eliminacion(request.user, data.get('password'))


def delete_account(request):
    """La cuota se gasta antes de la transacción de la escritura: si no, un intento fallido se revertiría con ella y no contaría."""
    if request.method == 'POST' and request.user.is_authenticated and not ratelimit.consume(request, action='eliminar_cuenta', user=request.user):
        return failure(429, 'rate-limited')
    return _delete_account(request)


@endpoint(('POST',))
def cancel_deletion(request, data):
    return services.cancelar_eliminacion(request.user)


def _filtro(request, nombre):
    return request.GET.get(nombre) or None


@endpoint(('GET', 'POST'), ('type', 'version', 'title', 'content'), cap='gestionar_legales')
def admin_legal(request, data):
    if request.method == 'POST':
        return legales.crear(request.user, data.get('type'), data.get('version'), data.get('title'), data.get('content'))
    bounds(request, allowed=('tipo',))
    return legales.por_tipo(request.user, _filtro(request, 'tipo'))


@endpoint(cap='gestionar_legales')
def admin_legal_detail(request, data, documento_id):
    bounds(request, allowed=())
    return legales.detalle(request.user, documento_id)


@endpoint(('POST',), ('content',), cap='gestionar_legales')
def admin_legal_preview(request, data):
    return legales.vista_previa(request.user, data.get('content'))


@endpoint(('POST',), ('expectedAt', 'version', 'title', 'content'), cap='gestionar_legales')
def admin_legal_edit(request, data, documento_id):
    return legales.editar(request.user, documento_id, data.get('expectedAt'), data.get('version'), data.get('title'), data.get('content'))


@endpoint(('POST',), ('expectedAt',), cap='gestionar_legales')
def admin_legal_delete(request, data, documento_id):
    return legales.eliminar(request.user, documento_id, data.get('expectedAt'))


@endpoint(('POST',), ('expectedAt',), cap='gestionar_legales')
def admin_legal_publish(request, data, documento_id):
    return legales.publicar(request.user, documento_id, data.get('expectedAt'))


FILTROS_BITACORA = ('documento', 'decision', 'desde', 'hasta', 'cuenta', 'version')


@endpoint(cap='ver_consentimientos')
def admin_consents(request, data):
    pagina = bounds(request, allowed=(*FILTROS_BITACORA, 'page'))
    return consentimientos.bitacora(request.user, *(_filtro(request, nombre) for nombre in FILTROS_BITACORA), pagina)


@endpoint(cap='ver_consentimientos')
def admin_consents_summary(request, data):
    bounds(request, allowed=())
    return consentimientos.resumen(request.user)


@endpoint(cap='ver_consentimientos')
def admin_consents_export(request, data):
    bounds(request, allowed=FILTROS_BITACORA)
    return consentimientos.exportar(request.user, *(_filtro(request, nombre) for nombre in FILTROS_BITACORA))
