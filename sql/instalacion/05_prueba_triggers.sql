-- Prueba las reglas que necesitan un huerto. Query Tool, como chilito_pkg_owner.
-- No deja datos: crea filas de prueba y termina en ROLLBACK.
-- Resultado en la pestaña Messages: una línea FALLO por caso distinto y un RESUMEN final.
BEGIN;

CREATE FUNCTION pg_temp.espera(sentencia text, estado text, nombre text, INOUT fallos integer)
LANGUAGE plpgsql AS $$
DECLARE obtenido text := 'ok';
BEGIN
 BEGIN
  EXECUTE sentencia;
  -- Se revierte cada caso: uno que se acepta por error no afecta a los siguientes.
  RAISE EXCEPTION USING ERRCODE='ZZ001';
 EXCEPTION
  WHEN SQLSTATE 'ZZ001' THEN obtenido := 'ok';
  WHEN OTHERS THEN obtenido := SQLSTATE;
 END;
 IF obtenido <> estado THEN
  fallos := fallos + 1;
  RAISE NOTICE 'FALLO: % (esperado %, obtenido %)', nombre, estado, obtenido;
 END IF;
END $$;

DO $$
DECLARE
 autor bigint; editor bigint; ajeno bigint; h bigint; otro_h bigint;
 m uuid := gen_random_uuid(); r1 uuid := gen_random_uuid(); r2 uuid := gen_random_uuid();
 zonas integer; f integer := 0; total integer := 19;
 usuario text := 'INSERT INTO public.cuentas_usuario(password,is_superuser,first_name,last_name,is_staff,is_active,date_joined,email,alias) VALUES(''x'',false,'''','''',false,true,now(),%L,'''') RETURNING id';
 revision text := 'INSERT INTO public.datos_revisionmantenimiento(id,numero,tipo,tipo_corregido,motivo,registrada_en,editor_id,mantenimiento_id) VALUES(%L,%s,%L,%L,''motivo'',now(),%s,%L)';
 auditoria text := 'INSERT INTO public.datos_auditoria(id,accion,resultado,creada_en,actor_id,huerto_id,mantenimiento_id,revision_mantenimiento_id) VALUES(gen_random_uuid(),%L,''recorded'',now(),%s,%s,%L,%L)';
BEGIN
 EXECUTE format(usuario,'prueba-autor@example.test') INTO autor;
 EXECUTE format(usuario,'prueba-editor@example.test') INTO editor;
 EXECUTE format(usuario,'prueba-ajeno@example.test') INTO ajeno;
 INSERT INTO public.huerto_huerto(clave,nombre,zona_horaria,creado_en) VALUES('prueba-1','Prueba 1','UTC',now()) RETURNING id INTO h;
 INSERT INTO public.huerto_huerto(clave,nombre,zona_horaria,creado_en) VALUES('prueba-2','Prueba 2','UTC',now()) RETURNING id INTO otro_h;
 SELECT count(*) INTO zonas FROM public.huerto_zona WHERE huerto_id=h;
 IF zonas <> 3 THEN f := f + 1; RAISE NOTICE 'FALLO: el huerto creó % zonas', zonas; END IF;
 INSERT INTO public.huerto_membresia(activa,asignada_en,huerto_id,usuario_id) VALUES(true,now(),h,autor);
 INSERT INTO public.datos_asignacionmantenimiento(activa,asignada_en,huerto_id,usuario_id) VALUES(true,now(),h,editor);
 INSERT INTO public.datos_mantenimiento(id,tipo,registrado_en,actor_id,huerto_id) VALUES(m,'harvest',now(),autor,h);

 -- Reglas existentes
 f := pg_temp.espera(format('UPDATE public.datos_mantenimiento SET tipo=''refill'' WHERE id=%L',m),'23514','mantenimiento inmutable',f);
 f := pg_temp.espera(format('DELETE FROM public.datos_mantenimiento WHERE id=%L',m),'23514','mantenimiento sin borrado',f);
 f := pg_temp.espera(format('UPDATE public.huerto_membresia SET usuario_id=%s WHERE usuario_id=%s',ajeno,autor),'23514','membresía sin reasignar',f);
 f := pg_temp.espera(format('UPDATE public.huerto_zona SET numero=1 WHERE huerto_id=%s AND numero=2',h),'23514','zona sin reasignar',f);
 f := pg_temp.espera(format(auditoria,'maintenance',autor,h,m,NULL),'ok','auditoría del autor',f);
 f := pg_temp.espera(format(auditoria,'maintenance',editor,h,m,NULL),'23514','auditoría actor distinto del autor',f);

 -- Revisiones
 f := pg_temp.espera(format(revision,gen_random_uuid(),1,'correccion','refill',ajeno,m),'23514','editor sin asignación',f);
 f := pg_temp.espera(format(revision,gen_random_uuid(),3,'correccion','refill',editor,m),'23514','número fuera de orden',f);
 f := pg_temp.espera(format(revision,gen_random_uuid(),1,'correccion',NULL,editor,m),'23514','corrección sin tipo',f);
 f := pg_temp.espera(format(revision,gen_random_uuid(),1,'anulacion','refill',editor,m),'23514','anulación con tipo',f);
 EXECUTE format(revision,r1,1,'correccion','refill',editor,m);
 f := pg_temp.espera(format(auditoria,'maintenance-corrected',editor,h,NULL,r1),'ok','auditoría del editor',f);
 f := pg_temp.espera(format(auditoria,'maintenance-corrected',autor,h,NULL,r1),'23514','auditoría de otro actor',f);
 f := pg_temp.espera(format(auditoria,'maintenance-corrected',editor,otro_h,NULL,r1),'23514','auditoría de otro huerto',f);
 f := pg_temp.espera(format(auditoria,'maintenance-corrected',editor,h,NULL,NULL),'23514','acción sin revisión',f);
 f := pg_temp.espera(format('UPDATE public.datos_revisionmantenimiento SET motivo=''x'' WHERE id=%L',r1),'23514','revisión inmutable',f);
 f := pg_temp.espera(format(revision,gen_random_uuid(),1,'anulacion',NULL,editor,m),'23514','número repetido',f);
 EXECUTE format(revision,r2,2,'anulacion',NULL,editor,m);
 f := pg_temp.espera(format(revision,gen_random_uuid(),3,'correccion','refill',editor,m),'23514','revisión tras anular',f);
 f := pg_temp.espera(format('UPDATE public.datos_asignacionmantenimiento SET usuario_id=%s WHERE usuario_id=%s',ajeno,editor),'23514','asignación sin reasignar',f);

 RAISE NOTICE 'RESUMEN: % casos, % fallos', total, f;
END $$;

ROLLBACK;
