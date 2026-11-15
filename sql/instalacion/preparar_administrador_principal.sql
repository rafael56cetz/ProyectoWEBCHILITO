-- Convierte una cuenta YA REGISTRADA en administradora. Query Tool, como chilito_pkg_owner.
-- Cambia solo el correo de la línea marcada. No crea contraseñas ni cuentas.
-- Crea, si no existen, el huerto principal, su dispositivo y la asignación de mantenimientos.
DO $$
DECLARE
 correo text := 'CAMBIA_ESTE_CORREO@example.test'; -- <== escribe aquí el correo de la cuenta
 u bigint; h bigint; n integer;
BEGIN
 SELECT id INTO u FROM public.cuentas_usuario WHERE lower(email)=lower(btrim(correo));
 IF NOT FOUND THEN RAISE EXCEPTION 'No existe esa cuenta: regístrala primero en la aplicación'; END IF;
 INSERT INTO public.huerto_huerto(clave,nombre,zona_horaria,creado_en)
  VALUES('principal','Huerto principal','America/Mexico_City',now()) ON CONFLICT(clave) DO NOTHING;
 SELECT id INTO h FROM public.huerto_huerto WHERE clave='principal';
 INSERT INTO public.datos_dispositivo(huerto_id,identificador,creado_en)
  VALUES(h,'chilito-principal',now()) ON CONFLICT DO NOTHING;
 INSERT INTO public.cuentas_usuario_user_permissions(usuario_id,permission_id)
  SELECT u,p.id FROM public.auth_permission p
  JOIN public.django_content_type c ON c.id=p.content_type_id
  WHERE c.app_label='datos' AND p.codename IN ('ver_flota','atender_soporte','gestionar_mantenimientos')
  ON CONFLICT DO NOTHING;
 GET DIAGNOSTICS n = ROW_COUNT;
 INSERT INTO public.datos_asignacionmantenimiento(usuario_id,huerto_id,activa,asignada_en)
  VALUES(u,h,true,now()) ON CONFLICT(usuario_id,huerto_id) DO UPDATE SET activa=true;
 RAISE NOTICE 'Listo: % capacidades nuevas. Falta activar TOTP o una llave en Seguridad.', n;
END $$;
