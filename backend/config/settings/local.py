"""Loopback-only settings. Not a production deployment configuration."""
import os
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403

DB_SCOPE = os.environ.get("ELCHILITO_DB_SCOPE", "local")
DB_ROLE = os.environ.get("ELCHILITO_DB_ROLE", "app")
if DB_SCOPE not in {"local", "test"} or DB_ROLE not in {"app", "migrador"}:
    raise ImproperlyConfigured("Seleccion DB_SCOPE/DB_ROLE no valida.")
prefix = "el_chilito_test" if DB_SCOPE == "test" else "el_chilito"
db_user = prefix + ("_app" if DB_ROLE == "app" else "_migrador")
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": prefix,
    "USER": db_user,
    "PASSWORD": secret("DB_TEST_PASSWORD" if DB_SCOPE == "test" else "DB_PASSWORD", db_user + ".txt"),
    "HOST": "127.0.0.1", "PORT": "5433",
    "CONN_MAX_AGE": 0,
    "OPTIONS": {"connect_timeout": 5, "sslmode": "disable"},
}}
# These two exceptions apply ONLY to this loopback HTTP presentation.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False


HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": "http://127.0.0.1:8766/index.html#verificar",
    "account_reset_password": "http://127.0.0.1:8766/index.html#recuperar",
    "account_reset_password_from_key": "http://127.0.0.1:8766/index.html#restablecer?token={key}",
    "account_signup": "http://127.0.0.1:8766/index.html#registro",
}

# Owner-authorized Stage B review; never use this profile for publication.
ELCHILITO_LOCAL_PRESENTATION = True
ELCHILITO_LOCAL_REGISTRATION_ENABLED = os.environ.get("ELCHILITO_LOCAL_REGISTRATION", "1") == "1"
# Owner-authorized local registration with any valid email address.
ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT = os.environ.get("ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT", "1") == "1"
