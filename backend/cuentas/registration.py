"""Explicit, loopback-only authorization for the owner's local registration review."""
import os
from django.conf import settings
from django.core.exceptions import DisallowedHost

def configuration_profile():
    # override_settings uses a holder with SETTINGS_MODULE=None in isolated tests.
    return settings.SETTINGS_MODULE or os.environ.get("DJANGO_SETTINGS_MODULE", "")

def configuration_problems():
    registration_enabled = getattr(settings, "ELCHILITO_LOCAL_REGISTRATION_ENABLED", False) is True
    any_recipient = getattr(settings, "ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT", False) is True
    if not registration_enabled and not any_recipient:
        return []
    problems = []
    module = configuration_profile()
    if any_recipient and module != "config.settings.local":
        problems.append("El envio a cualquier destinatario solo se permite en el perfil local.")
    if module not in {"config.settings.local", "config.settings.testing"}:
        problems.append("El registro local no se permite en otro perfil.")
    if getattr(settings, "ELCHILITO_LOCAL_PRESENTATION", False) is not True:
        problems.append("Falta habilitar explicitamente la presentacion local.")
    if settings.ALLOWED_HOSTS != ["127.0.0.1"]:
        problems.append("El registro local requiere hosts limitados al loopback.")
    if getattr(settings, "USE_X_FORWARDED_HOST", False) or getattr(settings, "SECURE_PROXY_SSL_HEADER", None):
        problems.append("La excepcion local no admite un proxy.")
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        problems.append("La excepcion local no admite CORS abierto.")
    urls = getattr(settings, "HEADLESS_FRONTEND_URLS", {})
    if not urls or any(not url.startswith("http://127.0.0.1:8766/index.html#") for url in urls.values()):
        problems.append("El origen del correo debe ser el local canonico.")
    database = settings.DATABASES["default"]["NAME"]
    if module == "config.settings.testing":
        if database != "el_chilito_test" or settings.EMAIL_BACKEND != "django.core.mail.backends.locmem.EmailBackend":
            problems.append("La revision automatizada requiere base y correo aislados.")
    elif database != "el_chilito" or settings.EMAIL_BACKEND != "cuentas.email.AuthorizedSMTPBackend":
        problems.append("La presentacion requiere la base local y el correo autorizado.")
    return problems

def local_email_recipients_allowed():
    return (
        getattr(settings, "ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT", False) is True
        and configuration_profile() == "config.settings.local"
        and not configuration_problems()
    )

def local_registration_allowed(request):
    if getattr(settings, "ELCHILITO_LOCAL_REGISTRATION_ENABLED", False) is not True or configuration_problems():
        return False
    if request is None or request.META.get("REMOTE_ADDR") != "127.0.0.1" or request.scheme != "http":
        return False
    ports = {"127.0.0.1:8766"}
    if configuration_profile() == "config.settings.testing":
        ports.add("127.0.0.1:8768")
    try:
        return request.get_host() in ports
    except DisallowedHost:
        return False
