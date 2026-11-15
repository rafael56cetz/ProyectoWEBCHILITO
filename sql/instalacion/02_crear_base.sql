-- Solo administrador PostgreSQL, conectado a postgres.
-- Ejecutar esta sentencia sola, con autocommit; CREATE DATABASE no admite transacción.
-- Si ya existe, detenerse: no borrar ni reutilizar una base sin revisión.
CREATE DATABASE chilito_integracion_sinteticos OWNER chilito_pkg_owner;
