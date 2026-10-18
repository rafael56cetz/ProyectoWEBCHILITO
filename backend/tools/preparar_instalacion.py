"""First installation only: preserve existing roles/data and generate private secrets."""
import argparse
import subprocess
import sys
from psycopg import sql
from tools.private_files import create_private_secret, PRIVATE_DIR


def psql(query, database="postgres", container="el-chilito-db-1"):
    result = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-X", "-w", "-U", "postgres",
         "-d", database, "-v", "ON_ERROR_STOP=1", "-At"],
        input=query, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("PostgreSQL no pudo completar la preparacion; revisar sin sobrescribir.")
    return result.stdout.strip()


def prepare(container="el-chilito-db-1"):
    for role in ("el_chilito_migrador", "el_chilito_app"):
        exists = psql(sql.SQL("SELECT 1 FROM pg_roles WHERE rolname={}").format(
            sql.Literal(role)).as_string(), container=container)
        if exists:
            if not (PRIVATE_DIR / (role + ".txt")).is_file():
                raise RuntimeError("Rol existente sin archivo privado: recuperar credenciales, no restablecer.")
            continue
        password = create_private_secret(role + ".txt")
        if password is None:
            raise RuntimeError("Archivo privado existente sin rol: revisar antes de continuar.")
        psql(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}").format(
            sql.Identifier(role), sql.Literal(password)).as_string(), container=container)
    exists = psql("SELECT 1 FROM pg_database WHERE datname='el_chilito'", container=container)
    if not exists:
        psql("CREATE DATABASE el_chilito OWNER el_chilito_migrador ENCODING 'UTF8'", container=container)
    if psql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='el_chilito'", container=container) != "el_chilito_migrador":
        raise RuntimeError("La base tiene otro propietario; no se modifica.")
    psql("""REVOKE ALL ON DATABASE el_chilito FROM PUBLIC;
GRANT CONNECT ON DATABASE el_chilito TO el_chilito_app;""", container=container)
    psql("""REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO el_chilito_app;
ALTER DEFAULT PRIVILEGES FOR ROLE el_chilito_migrador IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO el_chilito_app;
ALTER DEFAULT PRIVILEGES FOR ROLE el_chilito_migrador IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO el_chilito_app;""", "el_chilito", container)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo-secretos", action="store_true")
    parser.add_argument("--contenedor", default="el-chilito-db-1")
    args = parser.parse_args()
    if args.contenedor != "el-chilito-db-1" and not args.contenedor.startswith("el-chilito-instalacion-prueba-"):
        raise RuntimeError("Contenedor fuera del alcance de instalacion.")
    create_private_secret("postgres_admin.txt")
    create_private_secret("django_secret_key.txt")
    if not args.solo_secretos:
        prepare(args.contenedor)
    print("Preparacion completada sin mostrar ni reemplazar secretos.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Instalacion detenida. Revisar Docker y correspondencia de base/roles/archivos privados. No se restablecen contrasenas.", file=sys.stderr)
        sys.exit(1)
