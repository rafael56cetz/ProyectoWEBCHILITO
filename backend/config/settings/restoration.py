"""Only for an explicitly named isolated restoration. Never selects the main database."""
import re
from django.core.exceptions import ImproperlyConfigured
from .testing import *  # noqa: F403

restore_database = os.environ.get("ELCHILITO_RESTORE_DB","")
if not re.fullmatch(r"el_chilito_restore_[0-9]{8}_[a-f0-9]{8}",restore_database):
    raise ImproperlyConfigured("Falta seleccionar una base aislada de restauracion.")
DATABASES["default"]["NAME"] = restore_database
