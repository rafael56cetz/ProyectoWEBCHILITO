"""Despliegue: cualquier valor inseguro detiene el arranque."""
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from cryptography.fernet import Fernet

from .base import CHILITO_MFA_KEY, DATABASES, ELCHILITO_SMTP_ENABLED, ORIGIN

if os.environ.get('CHILITO_DEBUG', '0') != '0':
    raise ImproperlyConfigured('DEBUG no se permite en despliegue')
DEBUG = False
ALLOWED_HOSTS = [v.strip() for v in os.environ.get('CHILITO_ALLOWED_HOSTS', '').split(',') if v.strip()]
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('Hosts explícitos requeridos')
if not ORIGIN.startswith('https://'):
    raise ImproperlyConfigured('Origen HTTPS requerido')
if DATABASES['default']['USER'] != 'chilito_pkg_runtime':
    raise ImproperlyConfigured('La aplicación requiere rol limitado')
if DATABASES['default']['OPTIONS']['sslmode'] != 'verify-full':
    raise ImproperlyConfigured('PostgreSQL remoto requiere verify-full en despliegue')
try:
    Fernet(CHILITO_MFA_KEY)
except (ValueError, TypeError):
    raise ImproperlyConfigured('CHILITO_MFA_KEY debe ser una clave Fernet') from None
# Sin SMTP, los códigos de acceso irían a un archivo local del servidor.
if not ELCHILITO_SMTP_ENABLED:
    raise ImproperlyConfigured('Despliegue requiere correo SMTP autorizado')
CSRF_TRUSTED_ORIGINS = [ORIGIN]
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# Solo tras un proxy propio que sustituya este encabezado; así no se puede falsificar desde fuera.
if os.environ.get('CHILITO_BEHIND_PROXY') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    ALLAUTH_TRUSTED_PROXY_COUNT = int(os.environ.get('CHILITO_TRUSTED_PROXY_COUNT', '1'))
ELCHILITO_REGISTRATION_ENABLED = os.environ.get('CHILITO_REGISTRATION_ENABLED', '0') == '1'
