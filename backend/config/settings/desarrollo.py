"""Equipo local y pruebas. Nada de este archivo se usa en despliegue."""
import base64
import hashlib
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import CHILITO_MFA_KEY, DATABASES, PROFILE, SECRET_KEY

DEBUG = os.environ.get('CHILITO_DEBUG', '0') == '1'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver'] if PROFILE == 'testing' else ['127.0.0.1', 'localhost']
if DATABASES['default']['NAME'] not in {'chilito_integracion_sinteticos', 'test_chilito_integracion_sinteticos'}:
    raise ImproperlyConfigured('Perfil local limitado a bases sintéticas de integración')
DATABASES['default']['OPTIONS']['sslmode'] = os.environ.get('CHILITO_DB_SSLMODE', 'disable')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
CSRF_TRUSTED_ORIGINS = []
ELCHILITO_REGISTRATION_ENABLED = os.environ.get('CHILITO_REGISTRATION_ENABLED', '1') == '1'
# WebAuthn exige HTTPS salvo aquí. produccion.py nunca lo activa.
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = PROFILE == 'local'
# Clave local derivada para no exigir un secreto más en desarrollo. Despliegue exige la suya.
CHILITO_MFA_KEY = CHILITO_MFA_KEY or base64.urlsafe_b64encode(hashlib.sha256((SECRET_KEY + ':mfa').encode()).digest()).decode()
