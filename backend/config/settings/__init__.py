"""Elige la configuración por CHILITO_ENV. Es obligatoria: un olvido no debe arrancar en modo relajado."""
import os

from django.core.exceptions import ImproperlyConfigured

PERFIL = os.environ.get('CHILITO_ENV')
if PERFIL in {'local', 'testing'}:
    from .desarrollo import *  # noqa: F401,F403
elif PERFIL == 'deployment':
    from .produccion import *  # noqa: F401,F403
else:
    raise ImproperlyConfigured('Define CHILITO_ENV: local, testing o deployment')
