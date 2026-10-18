import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "test":
        requested = [arg for arg in sys.argv[2:] if arg.startswith("--settings")]
        if requested and requested != ["--settings=config.settings.testing"]:
            sys.exit("Las pruebas solo admiten --settings=config.settings.testing.")
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.testing"
    role = os.environ.get("ELCHILITO_DB_ROLE", "app")
    if command == "migrate" and role != "migrador":
        sys.exit("migrate requiere ELCHILITO_DB_ROLE=migrador; nunca usar el rol de aplicacion para DDL.")
    if command in {"runserver", "runserver_plus"} and role != "app":
        sys.exit("El servidor requiere ELCHILITO_DB_ROLE=app.")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
