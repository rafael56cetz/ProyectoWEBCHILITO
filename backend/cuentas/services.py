"""Identidad de correo. La base decide qué correos son el mismo buzón."""
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model
from django.db import connection
from django.db.models import CharField, F, Func, Value
from django.utils.crypto import constant_time_compare


def _identidad(expresion):
    return Func(expresion, function='public.chilito_identidad_correo', output_field=CharField())


def correo_registrado(email):
    """Correo guardado de la cuenta equivalente, o None. Nunca lo devuelvas al cliente."""
    return (get_user_model().objects.annotate(identidad=_identidad(F('email')))
            .filter(identidad=_identidad(Value(email, output_field=CharField())))
            .values_list('email', flat=True).first())


def correo_para_acceso(email):
    """Valor para acceso y recuperación: una sola forma por buzón, exista o no la cuenta.

    allauth usa este valor como clave de sus límites. Si solo se unificaran las variantes
    de cuentas existentes, un 429 revelaría cuáles existen. Nunca lo devuelvas al cliente.
    """
    registrado = correo_registrado(email)
    if registrado:
        return registrado
    with connection.cursor() as cursor:
        cursor.execute('SELECT public.chilito_identidad_correo(%s)', [email])
        return cursor.fetchone()[0]


def actor_de_sesion(sesion):
    """Identidad de la sesión de servidor, solo para cerrar lo suyo al salir.

    Django ve anónima una cuenta ya inactiva; su sesión antigua se identifica si la huella
    sigue siendo válida. No concede ninguna operación. Nunca se toma de la petición.
    """
    usuario, motor, huella = (sesion.get(k) for k in (SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY))
    if (not isinstance(usuario, str) or not usuario.isdecimal()
            or motor not in settings.AUTHENTICATION_BACKENDS or not isinstance(huella, str)):
        return None
    actor = get_user_model().objects.filter(pk=usuario).first()
    if actor and (constant_time_compare(huella, actor.get_session_auth_hash())
                  or any(constant_time_compare(huella, v) for v in actor.get_session_auth_fallback_hash())):
        return actor
    return None
