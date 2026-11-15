"""Frontera JSON del mismo origen. La autorización vive en los servicios de Django ya validados."""
import logging
import uuid
from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, RequestDataTooBig, ValidationError
from django.db import DatabaseError, IntegrityError
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from allauth.core import ratelimit

from datos import guias
from datos import services as s
from datos.paginacion import paginar

from . import services as operacion
from .respuestas import EntradaInvalida as InputError, ReglaDeNegocio, error as failure, leer_json as body, respuesta_de_base

logger = logging.getLogger(__name__)


def text(data, key, maximum=100, required=True):
    value = data.get(key, '' if not required else None)
    if not isinstance(value, str) or len(value) > maximum:
        raise InputError
    return value


def bounds(request, allowed=('page',)):
    # Lista blanca de parámetros: cualquier otro es entrada no válida.
    if set(request.GET) - set(allowed):
        raise InputError
    value = request.GET.get('page', '1')
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 10000:
        raise InputError
    return int(value)


def page(items, request, mapper=lambda row: row, allowed=('page',)):
    # Solo HTTP: validar `page`. Contar y recortar la consulta es trabajo de datos.paginacion.
    return {'status': 'ready', **paginar(items, bounds(request, allowed), mapper)}


def endpoint(methods=('GET',), fields=(), cap=None):
    def wrap(func):
        @wraps(func)
        def view(request, *args, **kwargs):
            if request.method not in methods:
                return failure(405, 'method-not-allowed')
            if not request.user.is_authenticated:
                return failure(401, 'unauthenticated')
            try:
                s.identity(request.user)
                if cap:
                    s.require_cap(request.user, cap)
                if request.method == 'GET':
                    resultado = func(request, {}, *args, **kwargs)
                    return resultado if isinstance(resultado, HttpResponse) else JsonResponse(resultado)
                data = body(request, fields)
                if not operacion.dentro_de_cuota(request.user, request.path):
                    return failure(429, 'rate-limited')
                key = uuid.UUID(request.headers.get('Idempotency-Key', ''))
                return JsonResponse(operacion.ejecutar_idempotente(request.user, key, request.path, operacion.huella_de(data),
                                                                   lambda: func(request, data, *args, **kwargs)))
            except (InputError, ValueError, TypeError, ValidationError, UnicodeError, RecursionError):
                return failure(400, 'invalid-input')
            except RequestDataTooBig:
                return failure(413, 'request-too-large')
            except operacion.Conflicto:
                return failure(409, 'idempotency-conflict')
            except s.RegistroDesactualizado:
                return failure(409, 'stale-record')
            except s.FactorRequerido:
                return failure(403, 'mfa-required')
            except ReglaDeNegocio as regla:
                return JsonResponse({'status': 409, 'code': regla.code, 'message': regla.message}, status=409)
            except Http404:
                return failure(404, 'not-found')
            except (PermissionDenied, ObjectDoesNotExist):
                return failure(403, 'access-denied')
            except IntegrityError as fallo:
                return respuesta_de_base(fallo) or failure(409, 'operation-conflict')
            except DatabaseError as fallo:
                logger.exception('operacion-no-disponible')
                return respuesta_de_base(fallo) or failure(503, 'service-unavailable')
        return view
    return wrap


@endpoint(cap='atender_consultas')
def inquiries(request, data):
    state = request.GET.get('state') or None
    return page(s.admin_inquiries(request.user, state), request, s.inquiry_dto, allowed=('page', 'state'))


@endpoint(('POST',), ('state',), cap='atender_consultas')
def inquiry_state(request, data, inquiry_id):
    return {'status': 'accepted', 'inquiry': s.inquiry_dto(s.update_inquiry(request.user, inquiry_id, text(data, 'state', 10)))}


# Guías de cuidado. El servicio valida y autoriza; aquí solo se lee la petición.
CAMPOS_GUIA = ('question', 'answer', 'order', 'sourceName', 'sourceUrl')


def guide_content(data):
    return {'pregunta': data.get('question'), 'respuesta': data.get('answer'), 'orden': data.get('order'),
            'fuente_nombre': data.get('sourceName', ''), 'fuente_url': data.get('sourceUrl', '')}


@endpoint()
def care_guides(request, data):
    bounds(request, allowed=())
    return guias.publicadas(request.user)


@endpoint(('GET', 'POST'), CAMPOS_GUIA, cap='gestionar_guias')
def admin_guides(request, data):
    if request.method == 'POST':
        return guias.crear(request.user, **guide_content(data))
    bounds(request, allowed=())
    return guias.panel(request.user)


@endpoint(('POST',), (*CAMPOS_GUIA, 'version'), cap='gestionar_guias')
def admin_guide_edit(request, data, guide_id):
    return guias.editar(request.user, guide_id, data.get('version'), **guide_content(data))


@endpoint(('POST',), ('version',), cap='gestionar_guias')
def admin_guide_publish(request, data, guide_id):
    return guias.publicar(request.user, guide_id, data.get('version'))


@endpoint(('POST',), ('version',), cap='gestionar_guias')
def admin_guide_withdraw(request, data, guide_id):
    return guias.retirar(request.user, guide_id, data.get('version'))


@never_cache
@require_POST
def contact(request):
    """Pública, con CSRF y cuota. El campo trampa, invisible para personas, descarta bots sin avisarles."""
    if not ratelimit.consume(request, action='contacto_producto'):
        return failure(429, 'rate-limited')
    try:
        data = body(request, ('name', 'email', 'message', 'website'))
        if not data.get('website'):
            operacion.enviar_contacto(data)
    except (InputError, ValueError, TypeError, ValidationError, UnicodeError, RecursionError):
        return failure(400, 'invalid-input')
    except RequestDataTooBig:
        return failure(413, 'request-too-large')
    except DatabaseError as fallo:
        logger.exception('contacto-no-guardado')
        return respuesta_de_base(fallo) or failure(503, 'service-unavailable')
    return JsonResponse({'status': 'accepted'})
