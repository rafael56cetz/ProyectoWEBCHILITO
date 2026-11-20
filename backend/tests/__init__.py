"""Ayudas comunes de las pruebas: textos legales publicados y cuentas con sus aceptaciones.

La base exige, al confirmar, que toda cuenta nueva haya aceptado los textos vigentes."""
import secrets
import time

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection, transaction
from django.test import RequestFactory

from privacidad.models import Decision, Sujeto
from privacidad.services import documento_vigente, registrar_actos_de_registro

TEXTOS = (('terminos', 'Términos y condiciones'), ('aviso_privacidad', 'Aviso de privacidad'),
          ('politica_cookies', 'Política de cookies'))


def publicar_textos(version='1.0'):
    with connection.cursor() as cursor:
        for tipo, titulo in TEXTOS:
            cursor.execute('SELECT chilito_publicar_documento_legal(%s,%s,%s,%s)',
                           [tipo, version, titulo, f'<p>Texto de prueba de {titulo}.</p>'])


def cuenta(email, *capacidades, verificada=True, factor=None, password=None, **campos):
    """Cuenta con sus aceptaciones. Con capacidades, trae TOTP salvo que `factor` diga lo contrario."""
    with transaction.atomic():      # la base exige las aceptaciones al confirmar la creación de la cuenta
        usuario = get_user_model().objects.create_user(email, password or secrets.token_urlsafe(24), **campos)
        registrar_actos_de_registro(usuario, RequestFactory().get('/'))
    EmailAddress.objects.create(user=usuario, email=email, verified=verificada, primary=True)
    if capacidades:
        usuario.user_permissions.add(*Permission.objects.filter(content_type__app_label='cuentas', codename__in=capacidades))
    if bool(capacidades) if factor is None else factor:
        Authenticator.objects.create(user=usuario, type='totp', data={})
    return usuario


def aceptar_vigentes(usuario):
    """Acepta los textos vigentes con el sujeto que la cuenta ya tiene (tras publicar una versión nueva)."""
    sujeto = Sujeto.objects.get(usuario=usuario, ambito='cuenta')
    for acto, tipo in (('aceptacion_terminos', 'terminos'), ('lectura_aviso', 'aviso_privacidad')):
        Decision.objects.create(sujeto=sujeto, acto=acto, decision=True, documento=documento_vigente(tipo), usuario=usuario)


def reautenticado(cliente):
    """Marca la sesión del cliente como recién reautenticada (lo que deja allauth al confirmar la contraseña).
    Las acciones críticas del panel (M-2) lo exigen; las pruebas de esas funciones parten de una confirmación vigente."""
    sesion = cliente.session
    sesion['account_authentication_methods'] = [*sesion.get('account_authentication_methods', []),
                                                {'method': 'password', 'at': time.time(), 'reauthenticated': True}]
    sesion.save()
    return cliente
