"""Legales, órdenes, soporte, avisos, vinculación del equipo y administración de flota, soporte, equipos, administradores y ventas."""
import logging

from allauth.core import ratelimit
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from datos import services as datos
from datos import administradores as administradores_admin, equipos as equipos_admin, ventas as ventas_admin
from huerto import services as huerto
from privacidad import services as privacidad
from web.api import bounds, endpoint
from web.respuestas import EntradaInvalida, error, leer_json, respuesta_de_base

logger = logging.getLogger(__name__)


@endpoint(('POST',), ('documents',))
def accept_legal(request, data):
    return privacidad.aceptar_textos(request.user, data.get('documents'), request)


@endpoint()
def command_state(request, data, comando_id):
    return huerto.estado_comando(request.user, comando_id)


@endpoint(('GET', 'POST'), ('incident', 'note', 'diagnostic', 'consent'), vinculado=True)
def support(request, data, huerto_id):
    if request.method == 'POST':
        return datos.abrir_caso(request.user, huerto_id, data.get('incident'), data.get('note'), data.get('diagnostic'), data.get('consent'))
    bounds(request, allowed=())
    return datos.soporte(request.user, huerto_id)


@endpoint(('POST',), huerto=True)
def support_revoke(request, data, caso_id):
    return datos.revocar_caso(request.user, caso_id)


@endpoint(('POST',), huerto=True)
def support_cancel(request, data, caso_id):
    return datos.cancelar_caso(request.user, caso_id)


@endpoint()
def diagnostic(request, data, diagnostico_id):
    bounds(request, allowed=())
    return datos.autodiagnostico(request.user, diagnostico_id)


@endpoint()
def notices(request, data):
    pagina = bounds(request, allowed=('filtro', 'page'))
    return datos.avisos(request.user, request.GET.get('filtro', 'todos'), pagina)


@endpoint()
def notice(request, data, aviso_id):
    bounds(request, allowed=())
    return datos.aviso(request.user, aviso_id)


@endpoint(('POST',))
def notice_read(request, data, aviso_id):
    return datos.marcar_leido(request.user, aviso_id)


@endpoint(('POST',))
def notice_resolved(request, data, aviso_id):
    return datos.marcar_resuelto(request.user, aviso_id)


@endpoint(('POST',))
def notices_read_all(request, data):
    return datos.leer_todos(request.user)


@endpoint()
def notice_count(request, data):
    bounds(request, allowed=())
    return datos.contador_avisos(request.user)


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
        # B-3: tope global antes de PBKDF2 (check_password), para que muchas IP no agoten la CPU.
        if not ratelimit.consume(request, action='vincular_dispositivo_global', key='global'):
            return error(429, 'rate-limited')
        return JsonResponse({'status': 'ready', 'result': huerto.vincular_dispositivo(identificador, credencial, codigo)})
    except (EntradaInvalida, ValueError, TypeError, ValidationError, UnicodeError, RecursionError):
        return error(400, 'invalid-input')
    except DatabaseError as fallo:
        logger.exception('vinculacion-no-disponible')
        return respuesta_de_base(fallo) or error(503, 'service-unavailable')


# Administración: cada vista pide su capacidad (y el segundo factor) en @endpoint; el servicio la vuelve a exigir.
def _filtro(request, nombre):
    return request.GET.get(nombre) or None


@endpoint(('GET', 'POST'), ('identifier', 'mac', 'firmware'), cap='gestionar_dispositivos')
def admin_devices(request, data):
    if request.method == 'POST':
        return equipos_admin.crear(request.user, data.get('identifier'), data.get('mac'), data.get('firmware'))
    pagina = bounds(request, allowed=('busqueda', 'estado', 'conexion', 'vendido', 'page'))
    return equipos_admin.listar(request.user, _filtro(request, 'busqueda'), _filtro(request, 'estado'), _filtro(request, 'conexion'), _filtro(request, 'vendido'), pagina)


@endpoint(cap='gestionar_dispositivos')
def admin_device(request, data, equipo_id):
    return equipos_admin.detalle(request.user, equipo_id, bounds(request))


@endpoint(('POST',), cap='gestionar_dispositivos', reciente=True)
def admin_device_unlink(request, data, equipo_id):
    return equipos_admin.desvincular(request.user, equipo_id)


@endpoint(('POST',), cap='gestionar_dispositivos', reciente=True)
def admin_device_rotate(request, data, equipo_id):
    return equipos_admin.rotar_credencial(request.user, equipo_id)


@endpoint(('POST',), cap='gestionar_dispositivos')
def admin_device_retire(request, data, equipo_id):
    return equipos_admin.retirar(request.user, equipo_id)


@endpoint(cap='ver_flota')
def admin_fleet(request, data):
    pagina = bounds(request, allowed=('busqueda', 'estado', 'conexion', 'page'))
    return equipos_admin.flota(request.user, _filtro(request, 'busqueda'), _filtro(request, 'estado'), _filtro(request, 'conexion'), pagina)


@endpoint(cap='atender_soporte')
def admin_support(request, data):
    pagina = bounds(request, allowed=('estado', 'page'))
    return datos.bandeja_soporte(request.user, request.GET.get('estado', 'abierto'), pagina)


@endpoint(cap='atender_soporte')
def admin_support_case(request, data, folio):
    bounds(request, allowed=())
    return datos.detalle_soporte(request.user, folio)


@endpoint(('POST',), cap='atender_soporte')
def admin_support_attend(request, data, caso_id):
    return datos.atender_caso(request.user, caso_id)


@endpoint(('POST',), cap='atender_soporte')
def admin_support_connect(request, data, caso_id):
    return datos.conectar_caso(request.user, caso_id)


@endpoint(('POST',), ('result', 'note'), cap='atender_soporte')
def admin_support_resolve(request, data, caso_id):
    return datos.resolver_caso(request.user, caso_id, data.get('result'), data.get('note'))


@endpoint(cap='atender_soporte')
def admin_session(request, data, sesion_id):
    bounds(request, allowed=())
    return datos.estado_sesion(request.user, sesion_id)


@endpoint(('POST',), ('type', 'plant', 'duration'), cap='atender_soporte', reciente=True)
def admin_session_order(request, data, sesion_id):
    return datos.dar_orden(request.user, sesion_id, data.get('type'), data.get('plant'), data.get('duration'))


@endpoint(('POST',), cap='atender_soporte')
def admin_session_close(request, data, sesion_id):
    return datos.cerrar_sesion_tecnica(request.user, sesion_id)


@endpoint(cap='gestionar_administradores')
def admin_admins(request, data):
    return administradores_admin.listar(request.user, bounds(request))


@endpoint(cap='gestionar_administradores')
def admin_admins_history(request, data):
    pagina = bounds(request, allowed=('cuenta', 'capacidad', 'desde', 'hasta', 'page'))
    return administradores_admin.historial(request.user, _filtro(request, 'cuenta'), _filtro(request, 'capacidad'), _filtro(request, 'desde'), _filtro(request, 'hasta'), pagina)


@endpoint(cap='gestionar_administradores')
def admin_admins_activity(request, data):
    pagina = bounds(request, allowed=('cuenta', 'page'))
    return administradores_admin.actividad(request.user, _filtro(request, 'cuenta'), pagina)


@endpoint(('POST',), ('email', 'capabilities', 'reason'), cap='gestionar_administradores', reciente=True)
def admin_admins_change(request, data):
    return administradores_admin.cambiar_capacidades(request.user, data.get('email'), data.get('capabilities'), data.get('reason'))


CAMPOS_VENTA = ('device', 'buyer', 'email', 'municipality', 'price', 'received', 'reference', 'method', 'soldAt', 'plannedDelivery', 'note')


@endpoint(('GET', 'POST'), CAMPOS_VENTA, cap='gestionar_ventas')
def admin_sales(request, data):
    if request.method == 'POST':
        return ventas_admin.registrar(request.user, data)
    pagina = bounds(request, allowed=('desde', 'hasta', 'pago', 'entrega', 'municipio', 'busqueda', 'estado', 'page'))
    return ventas_admin.listar(request.user, *(_filtro(request, nombre) for nombre in ('desde', 'hasta', 'pago', 'entrega', 'municipio', 'busqueda', 'estado')), pagina)


@endpoint(cap='gestionar_ventas')
def admin_sales_summary(request, data):
    bounds(request, allowed=('desde', 'hasta'))
    return ventas_admin.resumen(request.user, _filtro(request, 'desde'), _filtro(request, 'hasta'))


@endpoint(('POST',), ('received', 'reference'), cap='gestionar_ventas')
def admin_sale_payment(request, data, venta_id):
    return ventas_admin.registrar_pago(request.user, venta_id, data.get('received'), data.get('reference'))


@endpoint(('POST',), ('deliveredAt',), cap='gestionar_ventas')
def admin_sale_delivery(request, data, venta_id):
    return ventas_admin.entregar(request.user, venta_id, data.get('deliveredAt'))


@endpoint(('POST',), ('note',), cap='gestionar_ventas')
def admin_sale_note(request, data, venta_id):
    return ventas_admin.editar_nota(request.user, venta_id, data.get('note'))


@endpoint(('POST',), cap='gestionar_ventas')
def admin_sale_cancel(request, data, venta_id):
    return ventas_admin.cancelar(request.user, venta_id)
