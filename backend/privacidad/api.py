"""Transporte JSON de privacidad. Reglas y autorización: privacidad/services.py."""
import logging

from allauth.core import ratelimit
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from privacidad import politicas, services
from web.api import InputError, body, endpoint, failure
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
