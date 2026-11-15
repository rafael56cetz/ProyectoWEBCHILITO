-- Solo administrador PostgreSQL, conectado a postgres. No contiene contraseñas.
-- Ejecutar una vez. Si los roles ya existen, falla y revierte todo; no los modifica.
BEGIN;
CREATE ROLE chilito_pkg_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE chilito_pkg_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE chilito_pkg_runtime SET search_path=pg_catalog,public;
COMMIT;
-- Establecer contraseñas por canal protegido; nunca escribirlas en este archivo.
