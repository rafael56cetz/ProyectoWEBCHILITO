-- Administrative context, dedicated database only. No passwords embedded.
-- psql --dbname=postgres -v ON_ERROR_STOP=1 -f roles.sql
-- Fails if names already exist; do not alter unrelated roles/databases automatically.
CREATE ROLE chilito_pkg_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE chilito_pkg_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE chilito_pkg_runtime SET search_path=pg_catalog,public;
CREATE DATABASE chilito_datos_sinteticos OWNER chilito_pkg_owner;
CREATE DATABASE test_chilito_datos_sinteticos OWNER chilito_pkg_owner;
-- Set passwords interactively with \password, or by an external secret manager.
-- Do not put secrets into these files or shell history. No role membership is granted.
