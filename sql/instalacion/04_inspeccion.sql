-- Solo lectura de estructura y restricciones. No consulta filas de usuarios o huertos.
SELECT current_database() AS base, current_user AS rol,
       current_setting('server_version') AS version_postgresql;

SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema='public'
ORDER BY table_name, ordinal_position;

SELECT c.relname AS tabla, con.conname AS restriccion, con.contype AS tipo,
       pg_get_constraintdef(con.oid) AS definicion, con.convalidated AS validada
FROM pg_constraint con
JOIN pg_class c ON c.oid=con.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public'
ORDER BY c.relname, con.conname;

SELECT c.relname AS tabla, t.tgname AS disparador,
       pg_get_triggerdef(t.oid) AS definicion
FROM pg_trigger t
JOIN pg_class c ON c.oid=t.tgrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND NOT t.tgisinternal
ORDER BY c.relname, t.tgname;
