import os
from django.core.asgi import get_asgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
if os.environ.get("ELCHILITO_DB_ROLE", "app") != "app":
    raise RuntimeError("El servidor no puede usar el rol migrador.")
application = get_asgi_application()
