"""Vida de la sesión web, decidida en el servidor. Control: ASVS V7."""
import logging
import time

from django.conf import settings
from django.contrib.auth import logout
from django.db import DatabaseError
from django.http import JsonResponse

from datos import services

logger = logging.getLogger(__name__)
INICIO = 'chilito_autenticada_en'
VISTO = 'chilito_vista_en'
PREFIJOS = ('/api/', '/_allauth/')
CONSULTA_DE_SESION = '/_allauth/browser/v1/auth/session'
RESOLUCION_ACTIVIDAD = 60


def registrar_autenticacion(sender, request, user, **kwargs):
    # user_logged_in se emite al terminar todos los pasos de acceso, no antes.
    ahora = int(time.time())
    request.session[INICIO] = ahora
    request.session[VISTO] = ahora


def es_sondeo(request):
    # El encabezado solo puede restar actividad: enviarlo nunca alarga una sesión.
    return (request.method == 'GET' and request.path == CONSULTA_DE_SESION) or 'X-Chilito-Sondeo' in request.headers


def vencida(ahora, inicio, visto, administrador):
    """`administrador` es una función: solo se consulta si la inactividad la hace relevante."""
    if not isinstance(inicio, int) or not isinstance(visto, int):
        return True
    inactiva = ahora - visto
    return (ahora - inicio >= settings.CHILITO_SESION_ABSOLUTA
            or inactiva >= settings.CHILITO_INACTIVIDAD_USUARIO
            or (inactiva >= settings.CHILITO_INACTIVIDAD_ADMIN and administrador()))


class SesionAcotada:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(PREFIJOS) and request.user.is_authenticated:
            try:
                self.atender(request)
            except DatabaseError:
                logger.exception('sesion-no-disponible')
                return JsonResponse({'status': 503, 'code': 'service-unavailable'}, status=503)
        return self.get_response(request)

    def atender(self, request):
        sesion, usuario, ahora = request.session, request.user, int(time.time())
        visto = sesion.get(VISTO)
        if vencida(ahora, sesion.get(INICIO), visto, lambda: services.is_admin(usuario)):
            logout(request)
        elif not es_sondeo(request) and ahora - visto >= RESOLUCION_ACTIVIDAD:
            sesion[VISTO] = ahora
