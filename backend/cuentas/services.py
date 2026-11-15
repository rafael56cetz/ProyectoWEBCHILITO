"""Identidad de correo. La base decide qué correos son el mismo buzón."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import CharField, F, Func, Value


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
