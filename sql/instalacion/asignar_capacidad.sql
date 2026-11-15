-- Concede UNA capacidad a UNA cuenta activa. Query Tool, como chilito_pkg_owner.
-- Cambia solo el correo y la capacidad de las líneas marcadas.
-- Capacidades permitidas: atender_consultas, vincular_huertos, gestionar_guias.
-- Requiere el esquema de la capacidad elegida y TOTP o una llave de acceso activos.
-- No concede otras capacidades ni privilegios de PostgreSQL. Repetir no duplica la asignación.
-- Vincular huertos pedirá además un segundo factor usado en los últimos 5 minutos.
DO $$
DECLARE
 correo text := 'CAMBIA_ESTE_CORREO@example.test'; -- <== correo de la cuenta
 capacidad text := 'CAMBIA_ESTA_CAPACIDAD';       -- <== una de las tres capacidades permitidas
 parche text;
 u bigint; p integer; n integer;
BEGIN
 IF capacidad IS NULL OR capacidad NOT IN ('atender_consultas','vincular_huertos','gestionar_guias')
 THEN RAISE EXCEPTION 'Elige atender_consultas, vincular_huertos o gestionar_guias'; END IF;
 parche := CASE capacidad
  WHEN 'atender_consultas' THEN '04_soporte_resuelto_y_buzon.sql'
  WHEN 'vincular_huertos' THEN '06_vinculacion_huerto.sql'
  WHEN 'gestionar_guias' THEN '07_guias_cuidado.sql'
 END;
 SELECT id INTO u FROM public.cuentas_usuario WHERE lower(email)=lower(btrim(correo)) AND is_active;
 IF NOT FOUND THEN RAISE EXCEPTION 'No existe una cuenta activa con ese correo'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.mfa_authenticator WHERE user_id=u AND type IN ('totp','webauthn'))
 THEN RAISE EXCEPTION 'La cuenta debe activar antes la app autenticadora o una llave de acceso'; END IF;
 SELECT p2.id INTO p FROM public.auth_permission p2 JOIN public.django_content_type c ON c.id=p2.content_type_id
  WHERE c.app_label='datos' AND p2.codename=capacidad;
 IF NOT FOUND THEN RAISE EXCEPTION 'Falta la capacidad: aplica antes el parche %', parche; END IF;
 INSERT INTO public.cuentas_usuario_user_permissions(usuario_id,permission_id) VALUES(u,p) ON CONFLICT DO NOTHING;
 GET DIAGNOSTICS n = ROW_COUNT;
 IF n=1 THEN
  RAISE NOTICE 'Capacidad % concedida.', capacidad;
 ELSE
  RAISE NOTICE 'La cuenta ya tenía la capacidad.';
 END IF;
END $$;
