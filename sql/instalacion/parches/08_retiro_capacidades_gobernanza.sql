-- Solo para una base que ya tiene datos.0012 (parche 07). Query Tool, como chilito_pkg_owner.
-- Retira las capacidades ver_gobernanza y gestionar_cambios (los apartados «Gobernanza de datos» y
-- «Despliegues y parámetros» ya no existen). No cambia tablas: borra esos dos permisos y sus asignaciones.
-- ANTES: ejecuta el SELECT del plan (PLAN-RETIRO-GOBERNANZA-Y-DESPLIEGUES.md, fase 0) y confirma que ninguna
-- cuenta administradora dependa solo de esas dos capacidades; esa cuenta dejaría de ser administradora.
-- Una sola transacción: si algo falla, no se aplica nada (ejecuta ROLLBACK; para limpiar el error).
-- Después de aplicarlo, reinicia el servidor.
BEGIN;

DO $$ BEGIN
 IF current_database() <> 'chilito_integracion_sinteticos' OR current_user <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a chilito_integracion_sinteticos como chilito_pkg_owner'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0012_guias_iniciales')
 THEN RAISE EXCEPTION 'Falta el parche 07_guias_cuidado.sql'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0013_retiro_capacidades_gobernanza')
 THEN RAISE EXCEPTION 'Este parche ya está aplicado'; END IF;
END $$;

-- Esquema de datos.0013: solo cambia las opciones del modelo (sin SQL).

DELETE FROM public.cuentas_usuario_user_permissions WHERE permission_id IN (
 SELECT p.id FROM public.auth_permission p JOIN public.django_content_type c ON c.id=p.content_type_id
 WHERE c.app_label='datos' AND p.codename IN ('ver_gobernanza','gestionar_cambios'));
DELETE FROM public.auth_group_permissions WHERE permission_id IN (
 SELECT p.id FROM public.auth_permission p JOIN public.django_content_type c ON c.id=p.content_type_id
 WHERE c.app_label='datos' AND p.codename IN ('ver_gobernanza','gestionar_cambios'));
DELETE FROM public.auth_permission WHERE id IN (
 SELECT p.id FROM public.auth_permission p JOIN public.django_content_type c ON c.id=p.content_type_id
 WHERE c.app_label='datos' AND p.codename IN ('ver_gobernanza','gestionar_cambios'));

INSERT INTO public.django_migrations(app,name,applied) VALUES
 ('datos','0013_retiro_capacidades_gobernanza',now());

COMMIT;
