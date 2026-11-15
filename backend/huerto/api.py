"""Frontera JSON del huerto. El servicio valida y comprueba que el huerto sea de la cuenta; aquí solo se lee la petición."""
from web.api import bounds, endpoint

from . import services


@endpoint(('GET', 'POST'), ('name',))
def gardens(request, data):
    if request.method == 'POST':
        return services.crear(request.user, data.get('name'))
    bounds(request, allowed=())
    return services.listar(request.user)


@endpoint()
def garden(request, data, huerto_id):
    bounds(request, allowed=())
    return services.detalle(request.user, huerto_id)


@endpoint(('POST',), ('name',))
def garden_rename(request, data, huerto_id):
    return services.renombrar(request.user, huerto_id, data.get('name'))


@endpoint(('POST',))
def garden_archive(request, data, huerto_id):
    return services.archivar(request.user, huerto_id)


@endpoint()
def garden_summaries(request, data, huerto_id):
    pagina = bounds(request)
    return services.resumenes_ia(request.user, huerto_id, pagina)


@endpoint(('POST',))
def link_code(request, data, huerto_id):
    return services.generar_codigo(request.user, huerto_id)


@endpoint()
def link_state(request, data, huerto_id):
    bounds(request, allowed=())
    return services.estado_vinculacion(request.user, huerto_id)


@endpoint(('POST',))
def unlink(request, data, huerto_id):
    return services.desvincular(request.user, huerto_id)


@endpoint(('GET', 'POST'), ('name', 'sowingDate', 'stage'))
def plant(request, data, huerto_id, numero):
    if request.method == 'POST':
        return services.editar_planta(request.user, huerto_id, numero, data)
    bounds(request, allowed=('rango',))
    return services.detalle_planta(request.user, huerto_id, numero, request.GET.get('rango', '24h'))


@endpoint(('POST',), ('type', 'plant', 'duration'))
def commands(request, data, huerto_id):
    return services.crear_comando(request.user, huerto_id, data.get('type'), data.get('plant'), data.get('duration'))


@endpoint(('GET', 'POST'), ('type', 'plant', 'chiles', 'doneAt'))
def cares(request, data, huerto_id):
    if request.method == 'POST':
        return services.registrar_cuidado(request.user, huerto_id, data.get('type'), data.get('plant'), data.get('chiles'), data.get('doneAt'))
    pagina = bounds(request, allowed=('planta', 'tipo', 'desde', 'hasta', 'page'))
    filtro = lambda nombre: request.GET.get(nombre) or None
    return services.cuidados(request.user, huerto_id, filtro('planta'), filtro('tipo'), filtro('desde'), filtro('hasta'), pagina)


@endpoint()
def telemetry(request, data, huerto_id):
    bounds(request, allowed=('rango',))
    return services.telemetria(request.user, huerto_id, request.GET.get('rango', '24h'))


@endpoint()
def log(request, data, huerto_id):
    pagina = bounds(request, allowed=('tipo', 'page'))
    return services.bitacora(request.user, huerto_id, request.GET.get('tipo', 'ordenes'), pagina)
