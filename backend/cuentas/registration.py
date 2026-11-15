"""Registro público de cuentas normales; solo se habilita por configuración del servidor.

La excepción histórica de uso solo local no se copió a esta aplicación a propósito."""
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
