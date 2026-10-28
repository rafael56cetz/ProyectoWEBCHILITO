"""Public normal-account registration, enabled only through server configuration.
The historical local-only exception is deliberately not copied into the new app.
"""
from django.conf import settings


def configuration_problems():
    problems = []
    if getattr(settings, 'ELCHILITO_REGISTRATION_ENABLED', False) not in (True, False):
        problems.append('El registro debe configurarse mediante un booleano del servidor.')
    return problems


def local_registration_allowed(request):
    # Name retained because the reused adapter/input import it; this is now the
    # server registration policy, not the previous port/host-specific exception.
    return request is not None and getattr(settings, 'ELCHILITO_REGISTRATION_ENABLED', False) is True
