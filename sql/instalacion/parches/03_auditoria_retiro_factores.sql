-- Solo para una base creada antes de datos.0007. Query Tool, como chilito_pkg_owner.
-- Permite auditar el retiro de segundo factor que hace el equipo de soporte.
BEGIN;

DO $$ BEGIN
 IF current_database() <> 'chilito_integracion_sinteticos' OR current_user <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a chilito_integracion_sinteticos como chilito_pkg_owner'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0007_auditoria_retiro_factores')
 THEN RAISE EXCEPTION 'Este parche ya está aplicado'; END IF;
END $$;

ALTER TABLE "datos_auditoria" DROP CONSTRAINT "auditoria_accion_valida";
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "auditoria_accion_valida" CHECK ("accion" IN ('maintenance', 'support-granted', 'support-revoked', 'token-requested', 'technical-opened', 'technical-closed', 'diagnostic-requested', 'request-recorded', 'version-validated', 'knowledge-saved', 'maintenance-corrected', 'maintenance-voided', 'mfa-reset'));

INSERT INTO public.django_migrations(app,name,applied) VALUES('datos','0007_auditoria_retiro_factores',now());

COMMIT;
