from django.db import DatabaseError, connection, transaction

from .respuestas import respuesta_de_base


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
