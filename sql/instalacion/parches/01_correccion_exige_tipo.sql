-- Solo para una base creada antes de datos.0006. Query Tool, como chilito_pkg_owner.
-- Una corrección sin tipo pasaba el CHECK: IN con NULL da desconocido, y el CHECK lo acepta.
-- Una base creada con el 03 actual ya lo incluye y este parche se detiene.
BEGIN;

DO $$ BEGIN
 IF current_database() <> 'chilito_integracion_sinteticos' OR current_user <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a chilito_integracion_sinteticos como chilito_pkg_owner'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0006_correccion_exige_tipo')
 THEN RAISE EXCEPTION 'Este parche ya está aplicado'; END IF;
END $$;

ALTER TABLE "datos_revisionmantenimiento" DROP CONSTRAINT "revision_mant_tipo_coherente";
ALTER TABLE "datos_revisionmantenimiento" ADD CONSTRAINT "revision_mant_tipo_coherente" CHECK ((("tipo" = 'correccion' AND "tipo_corregido" IN ('refill', 'substrate', 'germination', 'harvest', 'inspection') AND "tipo_corregido" IS NOT NULL) OR ("tipo" = 'anulacion' AND "tipo_corregido" IS NULL)));

INSERT INTO public.django_migrations(app,name,applied) VALUES('datos','0006_correccion_exige_tipo',now());

COMMIT;
