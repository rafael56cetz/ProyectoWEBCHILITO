import re
from io import BytesIO

from django.conf import settings
from django.db import DatabaseError, connection, transaction

from .respuestas import error, respuesta_de_base


class SecurityHeaders:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        response['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response['X-Frame-Options']='DENY'
        if request.path.startswith(('/api/','/_allauth/')):
            response['Cache-Control']='no-store'
            response['Vary']='Cookie'
        return response


class LimiteDeSubida:
    """Tamaño máximo de cada petición, antes de que CSRF o la vista lean el cuerpo.

    Toda ruta usa DATA_UPLOAD_MAX_MEMORY_SIZE (32 KB), salvo los borradores legales (256 KB) y la subida del .docx (2 MB).
    Django solo conoce un límite global y no limita los archivos: por eso aquí se elige por ruta y, si la ruta admite más,
    se lee el cuerpo ya acotado para que `request.body` no vuelva a aplicar el límite global."""
    BORRADORES = re.compile(r'^/api/admin/legales(/vista-previa|/sanear|/[0-9a-f-]{36}/editar)?$')
    DOCX = '/api/admin/legales/importar'
    MAXIMO_BORRADOR = 256 * 1024
    MAXIMO_DOCX = 2 * 1024 * 1024 + 64 * 1024

    def __init__(self, get_response):
        self.get_response = get_response

    def _maximo(self, request):
        if request.method == 'POST' and request.path == self.DOCX:
            return self.MAXIMO_DOCX
        if request.method == 'POST' and self.BORRADORES.match(request.path):
            return self.MAXIMO_BORRADOR
        return settings.DATA_UPLOAD_MAX_MEMORY_SIZE

    def __call__(self, request):
        largo = request.META.get('CONTENT_LENGTH') or '0'
        maximo = self._maximo(request)
        if not largo.isdecimal() or (request.content_type == 'multipart/form-data' and largo == '0') or int(largo) > maximo:
            return error(413, 'request-too-large')
        if maximo > settings.DATA_UPLOAD_MAX_MEMORY_SIZE and request.content_type != 'multipart/form-data':
            request._body = request.read()
            request._stream = BytesIO(request._body)
        return self.get_response(request)


class ActorDeBase:
    """Fija en la transacción la cuenta que escribe; la base rechaza escrituras sin actor.

    Abre aquí la transacción de la petición porque este middleware corre antes de que ATOMIC_REQUESTS
    abra la de la vista, y set_config(…, true) solo vive dentro de una transacción. Sin sesión no fija nada."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT set_config('chilito.actor_id', %s, true)", [str(request.user.pk)])
            return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, DatabaseError):
            return respuesta_de_base(exception)
        return None
