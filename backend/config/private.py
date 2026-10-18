"""Load application secrets at runtime; never include their values in errors."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ElChilito" / "secrets"

def secret(name, filename):
    value = os.environ.get(name)
    if value:
        return value
    path = Path(os.environ.get(name + "_FILE", PRIVATE_ROOT / filename)).resolve()
    if path.is_relative_to(PROJECT_ROOT):
        raise ImproperlyConfigured(f"{name}: el archivo privado debe estar fuera del proyecto.")
    try:
        value = path.read_text(encoding="utf-8-sig").rstrip("\r\n")
    except (OSError, UnicodeError):
        raise ImproperlyConfigured(f"{name}: falta configurar el secreto privado.") from None
    if not value:
        raise ImproperlyConfigured(f"{name}: el archivo privado esta vacio.")
    return value
