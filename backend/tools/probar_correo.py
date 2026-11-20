"""Envía un correo de prueba con la configuración local. Uso: probar_correo.py destino@correo"""
import sys

from entorno_local import cargar

cargar()
import django

django.setup()
from django.conf import settings
from django.core.mail import send_mail

from cuentas.email import MailUnavailable, delivery_problem

if len(sys.argv) != 2:
    sys.exit('Uso: probar_correo.py destino@correo')
if settings.EMAIL_BACKEND != 'cuentas.email.AuthorizedSMTPBackend':
    sys.exit('SMTP no está activo: revisa CHILITO_SMTP_CONFIG en tu .env')
problema = delivery_problem(sys.argv[1])
if problema:
    sys.exit(f'Configuración incompleta: {problema}')
try:
    send_mail('Prueba de correo de YouGarden', 'Si lees esto, el correo funciona.', None, [sys.argv[1]])
except MailUnavailable:
    sys.exit('Gmail rechazó el envío. Revisa la contraseña de aplicación y la verificación en dos pasos.')
print('SMTP aceptó el mensaje. Revisa la bandeja de entrada y el spam.')
