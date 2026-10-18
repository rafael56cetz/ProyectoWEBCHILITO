"""Provision ONLY isolated test roles/database. Does not reset existing passwords."""
import subprocess
import sys
from psycopg import sql
from tools.private_files import create_private_secret, PRIVATE_DIR

def psql(query, database="postgres"):
    result = subprocess.run(
        ["docker", "exec", "-i", "el-chilito-db-1", "psql", "-X", "-w",
         "-U", "postgres", "-d", database, "-v", "ON_ERROR_STOP=1", "-At"],
        input=query, capture_output=True, text=True)
    if result.returncode:
        # SQL may contain generated test passwords: do not print stderr or query.
        raise RuntimeError("No se pudo preparar la base aislada; no se modifican credenciales existentes.")
    return result.stdout.strip()

def main():
    create_private_secret("django_secret_key.txt")
    for role in ("el_chilito_test_migrador", "el_chilito_test_app"):
        present = psql(sql.SQL("SELECT 1 FROM pg_roles WHERE rolname={}").format(sql.Literal(role)).as_string())
        if present:
            if not (PRIVATE_DIR / (role + ".txt")).is_file():
                raise RuntimeError("Un rol aislado ya existe sin su archivo privado; revisar, no restablecer.")
            continue
        password = create_private_secret(role + ".txt")
        if password is None:
            raise RuntimeError("Hay archivo privado previo sin rol correspondiente; revisar sin sobrescribir.")
        statement = sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}").format(sql.Identifier(role), sql.Literal(password))
        psql(statement.as_string())
        password = None
    present = psql("SELECT 1 FROM pg_database WHERE datname='el_chilito_test'")
    if not present:
        psql("CREATE DATABASE el_chilito_test OWNER el_chilito_test_migrador ENCODING 'UTF8'")
    owner = psql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='el_chilito_test'")
    if owner != "el_chilito_test_migrador":
        raise RuntimeError("La base aislada tiene otro propietario; no se modifica.")
    psql("""REVOKE ALL ON DATABASE el_chilito_test FROM PUBLIC;
GRANT CONNECT ON DATABASE el_chilito_test TO el_chilito_test_app;""")
    psql("""REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO el_chilito_test_app;
ALTER DEFAULT PRIVILEGES FOR ROLE el_chilito_test_migrador IN SCHEMA public
GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO el_chilito_test_app;
ALTER DEFAULT PRIVILEGES FOR ROLE el_chilito_test_migrador IN SCHEMA public
GRANT USAGE,SELECT ON SEQUENCES TO el_chilito_test_app;""", "el_chilito_test")
    print("Base aislada y roles de prueba preparados; sin CREATEDB ni SUPERUSER para roles de aplicacion.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Preparacion detenida: revisar estado y archivos privados; no se exponen valores.", file=sys.stderr)
        sys.exit(1)
