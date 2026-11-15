-- Solo para una base que ya tiene datos.0008 (parche 04). Query Tool, como chilito_pkg_owner.
-- Permite pasar una consulta del producto de «Archivada» a «Atendida».
-- Solo cambia la función del disparador: el mensaje sigue inmutable, no se borra y nunca vuelve a «nueva».
-- Sin cambios de privilegios. Es una sola transacción: si algo falla, no se aplica nada (ejecuta ROLLBACK;).
BEGIN;

DO $$ BEGIN
 IF current_database() <> 'chilito_integracion_sinteticos' OR current_user <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a chilito_integracion_sinteticos como chilito_pkg_owner'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0008_soporte_resuelto_y_buzon')
 THEN RAISE EXCEPTION 'Falta el parche 04_soporte_resuelto_y_buzon.sql'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0009_consulta_archivada_a_atendida')
 THEN RAISE EXCEPTION 'Este parche ya está aplicado'; END IF;
END $$;

-- Igual que datos.0009 (y que 03_esquema_completo.sql).
CREATE OR REPLACE FUNCTION public.chilito_consulta_atencion() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'La consulta se conserva' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'estado'-'atendida_por_id'-'atendida_en') IS DISTINCT FROM (to_jsonb(OLD)-'estado'-'atendida_por_id'-'atendida_en')
 OR NOT ((OLD.estado='nueva' AND NEW.estado IN ('atendida','archivada'))
      OR (OLD.estado='atendida' AND NEW.estado='archivada')
      OR (OLD.estado='archivada' AND NEW.estado='atendida')) THEN
  RAISE EXCEPTION 'Transición de atención no permitida' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;

INSERT INTO public.django_migrations(app,name,applied) VALUES('datos','0009_consulta_archivada_a_atendida',now());

COMMIT;
