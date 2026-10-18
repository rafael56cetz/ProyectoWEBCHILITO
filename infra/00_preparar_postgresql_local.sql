-- Ejecutar una sola vez en una instancia nueva.
-- No contiene las tablas de la aplicación: las crearán las migraciones.

\set ON_ERROR_STOP on

CREATE ROLE el_chilito_migrador
  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;

\password el_chilito_migrador

CREATE ROLE el_chilito_app
  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;

\password el_chilito_app

CREATE DATABASE el_chilito
  OWNER el_chilito_migrador
  ENCODING 'UTF8';

REVOKE ALL ON DATABASE el_chilito FROM PUBLIC;
GRANT CONNECT ON DATABASE el_chilito TO el_chilito_app;

\connect el_chilito

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO el_chilito_app;

ALTER DEFAULT PRIVILEGES
  FOR ROLE el_chilito_migrador IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLES TO el_chilito_app;

ALTER DEFAULT PRIVILEGES
  FOR ROLE el_chilito_migrador IN SCHEMA public
  GRANT USAGE, SELECT
  ON SEQUENCES TO el_chilito_app;
