-- =====================================================================================================
--  EL CHILITO · DESIGNAR (O RETIRAR) UNA CUENTA ADMINISTRADORA
--  Sustituye a preparar_administrador_principal.sql y a asignar_capacidad.sql.
--  Query Tool de pgAdmin, conectado a la base como chilito_pkg_owner. Cambia solo las líneas marcadas «<==».
-- =====================================================================================================
--
--  CÓMO FUNCIONA EL ADMINISTRADOR EN EL CHILITO
--  · No existe un «superusuario» en la página. Una cuenta es administradora cuando tiene al menos una
--    de las seis capacidades, guardadas en cuentas_usuario_user_permissions.
--  · La persona primero se REGISTRA en la página como cualquiera (correo, contraseña, código por correo).
--  · Después se ejecuta este script con su correo. La próxima vez que entre, la página la lleva al panel.
--  · Para usar el panel debe tener activada la app autenticadora o una llave de acceso. Si no, la página
--    la manda a «Mi cuenta › Seguridad» hasta que active una.
--
--  CAPACIDADES (pon en «capacidades» las que quieras; por defecto, todas):
--    ver_flota                 Telemetría de flota
--    atender_soporte           Consola remota: casos de soporte, token y resolución
--    gestionar_mantenimientos  Mantenimientos de los huertos asignados (ver «asignar_huerto_principal»)
--    atender_consultas         Solicitudes del producto (mensajes del formulario «Consíguelo»)
--    vincular_huertos          Vinculación de huertos y pestaña «Equipos y ventas»
--    gestionar_guias           Guías de cuidado
--
--  QUÉ HACE
--  · accion = 'conceder': añade las capacidades elegidas (repetirlo no duplica nada). Si eliges
--    gestionar_mantenimientos y asignar_huerto_principal = true, crea si falta el huerto «principal»
--    con su dispositivo «chilito-principal» y se lo asigna para mantenimientos.
--  · accion = 'retirar': quita las capacidades elegidas. Si le quitas todas, vuelve a ser cuenta normal.
--    También desactiva sus asignaciones de mantenimiento cuando retiras gestionar_mantenimientos.
--  · No crea cuentas ni contraseñas, no cambia privilegios de PostgreSQL y no toca is_staff/is_superuser.
--  · Todo o nada: si algo falla, no se aplica ningún cambio.
-- =====================================================================================================
DO $$
DECLARE
 correo      text    := 'CAMBIA_ESTE_CORREO@example.test';               -- <== correo de la cuenta
 accion      text    := 'conceder';                                      -- <== 'conceder' o 'retirar'
 capacidades text[]  := ARRAY['ver_flota','atender_soporte','gestionar_mantenimientos',
                              'atender_consultas','vincular_huertos','gestionar_guias']; -- <== capacidades
 asignar_huerto_principal boolean := true;                               -- <== solo para gestionar_mantenimientos

 validas constant text[] := ARRAY['ver_flota','atender_soporte','gestionar_mantenimientos',
                                  'atender_consultas','vincular_huertos','gestionar_guias'];
 u bigint; h bigint; n integer; cuenta_activa boolean; verificada boolean; factor boolean; quedan text;
BEGIN
 IF current_user <> 'chilito_pkg_owner' THEN RAISE EXCEPTION 'Ejecútalo como chilito_pkg_owner'; END IF;
 IF correo LIKE 'CAMBIA%' THEN RAISE EXCEPTION 'Escribe el correo de la cuenta en la línea marcada'; END IF;
 IF accion NOT IN ('conceder','retirar') THEN RAISE EXCEPTION 'accion debe ser conceder o retirar'; END IF;
 IF capacidades IS NULL OR cardinality(capacidades)=0 OR NOT capacidades <@ validas THEN
  RAISE EXCEPTION 'Capacidades válidas: %', array_to_string(validas,', ');
 END IF;

 -- La cuenta se busca igual que al iniciar sesión: sin distinguir mayúsculas ni espacios.
 SELECT id, is_active INTO u, cuenta_activa FROM public.cuentas_usuario WHERE lower(email)=lower(btrim(correo));
 IF NOT FOUND THEN RAISE EXCEPTION 'No existe esa cuenta: la persona debe registrarse primero en la página'; END IF;

 IF accion = 'conceder' THEN
  IF NOT cuenta_activa THEN RAISE EXCEPTION 'La cuenta está desactivada'; END IF;
  INSERT INTO public.cuentas_usuario_user_permissions(usuario_id,permission_id)
   SELECT u, p.id FROM public.auth_permission p
   JOIN public.django_content_type c ON c.id=p.content_type_id
   WHERE c.app_label='datos' AND p.codename = ANY(capacidades)
   ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS n = ROW_COUNT;
  RAISE NOTICE 'Capacidades nuevas concedidas: %', n;

  IF 'gestionar_mantenimientos' = ANY(capacidades) AND asignar_huerto_principal THEN
   INSERT INTO public.huerto_huerto(clave,nombre,zona_horaria,creado_en)
    VALUES('principal','Huerto principal','America/Mexico_City',now()) ON CONFLICT(clave) DO NOTHING;
   SELECT id INTO h FROM public.huerto_huerto WHERE clave='principal';
   INSERT INTO public.datos_dispositivo(huerto_id,identificador,creado_en)
    VALUES(h,'chilito-principal',now()) ON CONFLICT DO NOTHING;
   INSERT INTO public.datos_asignacionmantenimiento(usuario_id,huerto_id,activa,asignada_en)
    VALUES(u,h,true,now()) ON CONFLICT(usuario_id,huerto_id) DO UPDATE SET activa=true;
   RAISE NOTICE 'Huerto «principal» asignado para mantenimientos.';
  END IF;

  -- Avisos útiles: no impiden la designación, pero la página los exigirá.
  SELECT EXISTS(SELECT 1 FROM public.account_emailaddress e WHERE e.user_id=u AND e.verified
                AND lower(e.email)=lower((SELECT email FROM public.cuentas_usuario WHERE id=u))) INTO verificada;
  SELECT EXISTS(SELECT 1 FROM public.mfa_authenticator WHERE user_id=u AND type IN ('totp','webauthn')) INTO factor;
  IF NOT verificada THEN
   RAISE NOTICE 'OJO: el correo aún no está verificado. Debe terminar el registro con el código que le llegó.';
  END IF;
  IF NOT factor THEN
   RAISE NOTICE 'OJO: sin app autenticadora ni llave de acceso. Al entrar, la página la llevará a Seguridad para activarla.';
  END IF;

 ELSE
  DELETE FROM public.cuentas_usuario_user_permissions up
   USING public.auth_permission p, public.django_content_type c
   WHERE up.usuario_id=u AND up.permission_id=p.id AND c.id=p.content_type_id
     AND c.app_label='datos' AND p.codename = ANY(capacidades);
  GET DIAGNOSTICS n = ROW_COUNT;
  RAISE NOTICE 'Capacidades retiradas: %', n;
  IF 'gestionar_mantenimientos' = ANY(capacidades) THEN
   UPDATE public.datos_asignacionmantenimiento SET activa=false WHERE usuario_id=u AND activa;
  END IF;
 END IF;

 SELECT string_agg(p.codename, ', ' ORDER BY p.codename) INTO quedan
  FROM public.cuentas_usuario_user_permissions up
  JOIN public.auth_permission p ON p.id=up.permission_id
  JOIN public.django_content_type c ON c.id=p.content_type_id
  WHERE up.usuario_id=u AND c.app_label='datos' AND p.codename = ANY(validas);
 RAISE NOTICE 'Capacidades actuales de la cuenta: %', coalesce(quedan, 'ninguna (cuenta normal)');
END $$;

-- Para ver quién es administrador ahora mismo (solo lectura):
-- SELECT u.email, string_agg(p.codename, ', ' ORDER BY p.codename) AS capacidades
-- FROM cuentas_usuario u
-- JOIN cuentas_usuario_user_permissions up ON up.usuario_id=u.id
-- JOIN auth_permission p ON p.id=up.permission_id
-- JOIN django_content_type c ON c.id=p.content_type_id AND c.app_label='datos'
-- WHERE p.codename IN ('ver_flota','atender_soporte','gestionar_mantenimientos','atender_consultas','vincular_huertos','gestionar_guias')
-- GROUP BY u.email ORDER BY u.email;
