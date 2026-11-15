-- Registra UN equipo entregable: huerto (sus tres zonas las crea un trigger) y su dispositivo.
-- Query Tool, como chilito_pkg_owner. Requiere el parche 06. No crea membresías: la cuenta se asocia
-- después con un código de vinculación desde el panel. Cambia solo las tres líneas marcadas.
DO $$
DECLARE
 v_clave text := 'CAMBIA-CLAVE-DEL-HUERTO';      -- <== identificador corto, sin espacios (ej.: huerto-0002)
 v_nombre text := 'CAMBIA EL NOMBRE DEL HUERTO';  -- <== nombre visible (ej.: Huerto de la entrega 2)
 v_equipo text := 'CAMBIA-ID-DEL-DISPOSITIVO';    -- <== identificador del ESP32 (no es un secreto)
 h bigint;
BEGIN
 IF current_user <> 'chilito_pkg_owner' THEN RAISE EXCEPTION 'Ejecútalo como chilito_pkg_owner'; END IF;
 IF v_clave LIKE 'CAMBIA%' OR v_nombre LIKE 'CAMBIA%' OR v_equipo LIKE 'CAMBIA%' THEN RAISE EXCEPTION 'Cambia las tres líneas marcadas'; END IF;
 IF v_clave !~ '^[-a-zA-Z0-9_]{1,64}$' THEN RAISE EXCEPTION 'La clave solo admite letras, números, guion y guion bajo'; END IF;
 IF btrim(v_nombre)='' OR length(v_nombre)>100 OR btrim(v_equipo)='' OR length(v_equipo)>128 THEN RAISE EXCEPTION 'Nombre o identificador no válidos'; END IF;
 IF EXISTS(SELECT 1 FROM public.huerto_huerto WHERE clave=v_clave) THEN RAISE EXCEPTION 'Ya existe un huerto con esa clave'; END IF;
 IF EXISTS(SELECT 1 FROM public.datos_dispositivo WHERE identificador=v_equipo) THEN RAISE EXCEPTION 'Ese dispositivo ya está registrado'; END IF;
 INSERT INTO public.huerto_huerto(clave,nombre,zona_horaria,creado_en) VALUES(v_clave,btrim(v_nombre),'America/Mexico_City',now()) RETURNING id INTO h;
 INSERT INTO public.datos_dispositivo(huerto_id,identificador,creado_en) VALUES(h,btrim(v_equipo),now());
 IF (SELECT count(*) FROM public.huerto_zona WHERE huerto_id=h) <> 3 THEN RAISE EXCEPTION 'No se crearon las tres zonas'; END IF;
 RAISE NOTICE 'Equipo registrado: huerto % con 3 zonas y dispositivo %. Ya aparece en «Vinculación de huertos».', v_clave, v_equipo;
END $$;
