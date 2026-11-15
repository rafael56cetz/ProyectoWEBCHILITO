"""Legales, órdenes y vinculación del equipo."""
import logging

from allauth.core import ratelimit
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from huerto import services as huerto
from privacidad import services as privacidad
from web.api import endpoint
from web.respuestas import EntradaInvalida, error, leer_json, respuesta_de_base

logger = logging.getLogger(__name__)


@endpoint(('POST',), ('documents',))
def accept_legal(request, data):
    return privacidad.aceptar_textos(request.user, data.get('documents'), request)


@endpoint()
def command_state(request, data, comando_id):
    return huerto.estado_comando(request.user, comando_id)


@csrf_exempt
@never_cache
@require_POST
def link_device(request):
    """Lo llama el ESP32, no un navegador: no hay sesión ni cookies, así que no hay credencial ambiental que un
    tercero pueda aprovechar y el token CSRF no protege nada aquí. Se autentica con identificador, credencial del
    equipo y un código de un solo uso, con cuota por IP y por identificador. La respuesta es mínima."""
    try:
        data = leer_json(request, ('identifier', 'credential', 'code'))
        identificador, credencial, codigo = (data.get(campo) for campo in ('identifier', 'credential', 'code'))
        if not all(isinstance(valor, str) and 0 < len(valor) <= 128 for valor in (identificador, credencial, codigo)):
            raise EntradaInvalida
        if not ratelimit.consume(request, action='vincular_dispositivo', key=identificador):
            return error(429, 'rate-limited')
        return JsonResponse({'status': 'ready', 'result': huerto.vincular_dispositivo(identificador, credencial, codigo)})
    except (EntradaInvalida, ValueError, TypeError, ValidationError, UnicodeError, RecursionError):
        return error(400, 'invalid-input')
    except DatabaseError as fallo:
        logger.exception('vinculacion-no-disponible')
        return respuesta_de_base(fallo) or error(503, 'service-unavailable')
