-- Solo para una base creada antes de datos.0008. Query Tool, como chilito_pkg_owner.
-- Soporte resuelto (historial inmutable), avisos por correo sin token y buzón de consultas del producto.
-- Crea la capacidad atender_consultas, pero NO la asigna a nadie: usa asignar_capacidad.sql con atender_consultas.
-- Es una sola transacción: si algo falla, no se aplica nada.
BEGIN;

DO $$ BEGIN
 IF current_database() <> 'chilito_integracion_sinteticos' OR current_user <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a chilito_integracion_sinteticos como chilito_pkg_owner'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0007_auditoria_retiro_factores')
 THEN RAISE EXCEPTION 'Falta el parche 03_auditoria_retiro_factores.sql'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0008_soporte_resuelto_y_buzon')
 THEN RAISE EXCEPTION 'Este parche ya está aplicado'; END IF;
 IF EXISTS(SELECT 1 FROM public.datos_sesiontecnica WHERE motivo_cierre NOT IN ('explicit','revoked','replaced','logout','expiry','resolved','')
           OR (cerrada_en IS NULL AND motivo_cierre <> ''))
 THEN RAISE EXCEPTION 'Hay sesiones técnicas con un motivo de cierre inesperado: revísalas antes'; END IF;
END $$;

-- Esquema de datos.0008 (generado con sqlmigrate; igual que migrate).
--
-- Create model AvisoCorreo
--
CREATE TABLE "datos_avisocorreo" ("id" uuid NOT NULL PRIMARY KEY, "tipo" varchar(20) NOT NULL, "creado_en" timestamp with time zone NOT NULL, "estado" varchar(16) NOT NULL, "intentos" smallint NOT NULL CHECK ("intentos" >= 0), "ultimo_intento_en" timestamp with time zone NULL, "aceptado_en" timestamp with time zone NULL);
--
-- Create model ConsultaProducto
--
CREATE TABLE "datos_consultaproducto" ("id" uuid NOT NULL PRIMARY KEY, "recibida_en" timestamp with time zone NOT NULL, "nombre" varchar(100) NOT NULL, "correo" varchar(254) NOT NULL, "mensaje" text NOT NULL, "huella" varchar(64) NOT NULL, "estado" varchar(10) NOT NULL, "atendida_en" timestamp with time zone NULL);
--
-- Create model ResolucionSoporte
--
CREATE TABLE "datos_resolucionsoporte" ("id" uuid NOT NULL PRIMARY KEY, "resultado" varchar(20) NOT NULL, "nota" text NOT NULL, "resuelto_en" timestamp with time zone NOT NULL);
--
-- Change Meta options on dispositivo
--
-- (no-op)
--
-- Remove constraint auditoria_accion_valida from model auditoria
--
ALTER TABLE "datos_auditoria" DROP CONSTRAINT "auditoria_accion_valida";
--
-- Remove constraint sesion_tecnica_cierre_valido from model sesiontecnica
--
ALTER TABLE "datos_sesiontecnica" DROP CONSTRAINT "sesion_tecnica_cierre_valido";
--
-- Create constraint auditoria_accion_valida on model auditoria
--
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "auditoria_accion_valida" CHECK ("accion" IN ('maintenance', 'support-granted', 'support-revoked', 'token-requested', 'technical-opened', 'technical-closed', 'diagnostic-requested', 'request-recorded', 'version-validated', 'knowledge-saved', 'maintenance-corrected', 'maintenance-voided', 'case-resolved', 'mfa-reset'));
--
-- Create constraint sesion_tecnica_cierre_valido on model sesiontecnica
--
ALTER TABLE "datos_sesiontecnica" ADD CONSTRAINT "sesion_tecnica_cierre_valido" CHECK ((("cerrada_en" IS NULL AND "motivo_cierre" = '') OR ("cerrada_en" >= ("iniciada_en") AND "cerrada_en" IS NOT NULL AND "motivo_cierre" IN ('explicit', 'revoked', 'replaced', 'logout', 'expiry', 'resolved'))));
--
-- Add field caso to avisocorreo
--
ALTER TABLE "datos_avisocorreo" ADD COLUMN "caso_id" uuid NULL CONSTRAINT "datos_avisocorreo_caso_id_fe2e6603_fk_datos_casosoporte_id" REFERENCES "datos_casosoporte"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_avisocorreo_caso_id_fe2e6603_fk_datos_casosoporte_id" IMMEDIATE;
--
-- Add field atendida_por to consultaproducto
--
ALTER TABLE "datos_consultaproducto" ADD COLUMN "atendida_por_id" bigint NULL CONSTRAINT "datos_consultaproduc_atendida_por_id_b419d152_fk_cuentas_u" REFERENCES "cuentas_usuario"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_consultaproduc_atendida_por_id_b419d152_fk_cuentas_u" IMMEDIATE;
--
-- Add field consulta to avisocorreo
--
ALTER TABLE "datos_avisocorreo" ADD COLUMN "consulta_id" uuid NULL CONSTRAINT "datos_avisocorreo_consulta_id_56fccf8f_fk_datos_con" REFERENCES "datos_consultaproducto"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_avisocorreo_consulta_id_56fccf8f_fk_datos_con" IMMEDIATE;
--
-- Add field caso to resolucionsoporte
--
ALTER TABLE "datos_resolucionsoporte" ADD COLUMN "caso_id" uuid NOT NULL UNIQUE CONSTRAINT "datos_resolucionsopo_caso_id_6cdd272a_fk_datos_cas" REFERENCES "datos_casosoporte"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_resolucionsopo_caso_id_6cdd272a_fk_datos_cas" IMMEDIATE;
--
-- Add field responsable to resolucionsoporte
--
ALTER TABLE "datos_resolucionsoporte" ADD COLUMN "responsable_id" bigint NOT NULL CONSTRAINT "datos_resolucionsopo_responsable_id_8de17b6d_fk_cuentas_u" REFERENCES "cuentas_usuario"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_resolucionsopo_responsable_id_8de17b6d_fk_cuentas_u" IMMEDIATE;
--
-- Create index consulta_estado_fecha_idx on field(s) estado, -recibida_en of model consultaproducto
--
CREATE INDEX "consulta_estado_fecha_idx" ON "datos_consultaproducto" ("estado", "recibida_en" DESC);
--
-- Create index consulta_huella_idx on field(s) huella, -recibida_en of model consultaproducto
--
CREATE INDEX "consulta_huella_idx" ON "datos_consultaproducto" ("huella", "recibida_en" DESC);
--
-- Create constraint consulta_correo_significativo on model consultaproducto
--
ALTER TABLE "datos_consultaproducto" ADD CONSTRAINT "consulta_correo_significativo" CHECK ("correo"::text ~  E'\\S');
--
-- Create constraint consulta_mensaje_significativo on model consultaproducto
--
ALTER TABLE "datos_consultaproducto" ADD CONSTRAINT "consulta_mensaje_significativo" CHECK ("mensaje"::text ~  E'\\S');
--
-- Create constraint consulta_mensaje_limite on model consultaproducto
--
ALTER TABLE "datos_consultaproducto" ADD CONSTRAINT "consulta_mensaje_limite" CHECK (LENGTH("mensaje") <= 2000);
--
-- Create constraint consulta_huella_valida on model consultaproducto
--
ALTER TABLE "datos_consultaproducto" ADD CONSTRAINT "consulta_huella_valida" CHECK ("huella"::text ~ '^[0-9a-f]{64}$');
--
-- Create constraint consulta_estado_valido on model consultaproducto
--
ALTER TABLE "datos_consultaproducto" ADD CONSTRAINT "consulta_estado_valido" CHECK ("estado" IN ('nueva', 'atendida', 'archivada'));
--
-- Create constraint consulta_atencion_coherente on model consultaproducto
--
ALTER TABLE "datos_consultaproducto" ADD CONSTRAINT "consulta_atencion_coherente" CHECK ((("atendida_en" IS NULL AND "atendida_por_id" IS NULL AND "estado" = 'nueva') OR ("atendida_en" IS NOT NULL AND "atendida_por_id" IS NOT NULL AND "estado" IN ('atendida', 'archivada'))));
--
-- Create index aviso_correo_pendientes_idx on field(s) estado, creado_en of model avisocorreo
--
CREATE INDEX "aviso_correo_pendientes_idx" ON "datos_avisocorreo" ("estado", "creado_en");
--
-- Create constraint aviso_correo_tipo_valido on model avisocorreo
--
ALTER TABLE "datos_avisocorreo" ADD CONSTRAINT "aviso_correo_tipo_valido" CHECK ("tipo" IN ('caso_nuevo', 'token_solicitado', 'consulta_nueva'));
--
-- Create constraint aviso_correo_referencia_coherente on model avisocorreo
--
ALTER TABLE "datos_avisocorreo" ADD CONSTRAINT "aviso_correo_referencia_coherente" CHECK ((("caso_id" IS NOT NULL AND "consulta_id" IS NULL AND "tipo" IN ('caso_nuevo', 'token_solicitado')) OR ("caso_id" IS NULL AND "consulta_id" IS NOT NULL AND "tipo" = 'consulta_nueva')));
--
-- Create constraint aviso_correo_estado_valido on model avisocorreo
--
ALTER TABLE "datos_avisocorreo" ADD CONSTRAINT "aviso_correo_estado_valido" CHECK ("estado" IN ('pendiente', 'aceptado_smtp', 'fallido'));
--
-- Create constraint aviso_correo_intentos_limite on model avisocorreo
--
ALTER TABLE "datos_avisocorreo" ADD CONSTRAINT "aviso_correo_intentos_limite" CHECK ("intentos" <= 5);
--
-- Create constraint aviso_correo_aceptacion_coherente on model avisocorreo
--
ALTER TABLE "datos_avisocorreo" ADD CONSTRAINT "aviso_correo_aceptacion_coherente" CHECK ((("aceptado_en" IS NOT NULL AND "estado" = 'aceptado_smtp') OR (NOT ("estado" = 'aceptado_smtp') AND "aceptado_en" IS NULL)));
--
-- Create constraint aviso_correo_caso_unico on model avisocorreo
--
CREATE UNIQUE INDEX "aviso_correo_caso_unico" ON "datos_avisocorreo" ("caso_id") WHERE "tipo" = 'caso_nuevo';
--
-- Create constraint aviso_correo_consulta_unico on model avisocorreo
--
CREATE UNIQUE INDEX "aviso_correo_consulta_unico" ON "datos_avisocorreo" ("consulta_id") WHERE "tipo" = 'consulta_nueva';
--
-- Create constraint resolucion_resultado_valido on model resolucionsoporte
--
ALTER TABLE "datos_resolucionsoporte" ADD CONSTRAINT "resolucion_resultado_valido" CHECK ("resultado" IN ('solucionado', 'sin_falla', 'sin_respuesta', 'otro'));
--
-- Create constraint resolucion_otro_con_nota on model resolucionsoporte
--
ALTER TABLE "datos_resolucionsoporte" ADD CONSTRAINT "resolucion_otro_con_nota" CHECK ((NOT ("resultado" = 'otro') OR "nota"::text ~  E'\\S'));
--
-- Create constraint resolucion_nota_limite on model resolucionsoporte
--
ALTER TABLE "datos_resolucionsoporte" ADD CONSTRAINT "resolucion_nota_limite" CHECK (LENGTH("nota") <= 500);
--
-- Raw SQL operation
--

CREATE TRIGGER historial_resolucionsoporte BEFORE UPDATE OR DELETE ON public.datos_resolucionsoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE FUNCTION public.chilito_consulta_atencion() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'La consulta se conserva' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'estado'-'atendida_por_id'-'atendida_en') IS DISTINCT FROM (to_jsonb(OLD)-'estado'-'atendida_por_id'-'atendida_en')
 OR NOT ((OLD.estado='nueva' AND NEW.estado IN ('atendida','archivada')) OR (OLD.estado='atendida' AND NEW.estado='archivada')) THEN
  RAISE EXCEPTION 'Solo se admite avanzar la atención de la consulta' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER consulta_solo_avanzar BEFORE UPDATE OR DELETE ON public.datos_consultaproducto FOR EACH ROW EXECUTE FUNCTION public.chilito_consulta_atencion();
CREATE FUNCTION public.chilito_aviso_correo() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'El aviso se conserva' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'estado'-'intentos'-'ultimo_intento_en'-'aceptado_en') IS DISTINCT FROM (to_jsonb(OLD)-'estado'-'intentos'-'ultimo_intento_en'-'aceptado_en')
 OR OLD.estado='aceptado_smtp' OR NEW.intentos < OLD.intentos THEN
  RAISE EXCEPTION 'El aviso solo registra intentos hasta su aceptación' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER aviso_correo_estado BEFORE UPDATE OR DELETE ON public.datos_avisocorreo FOR EACH ROW EXECUTE FUNCTION public.chilito_aviso_correo();

CREATE INDEX "datos_avisocorreo_caso_id_fe2e6603" ON "datos_avisocorreo" ("caso_id");
CREATE INDEX "datos_consultaproducto_atendida_por_id_b419d152" ON "datos_consultaproducto" ("atendida_por_id");
CREATE INDEX "datos_avisocorreo_consulta_id_56fccf8f" ON "datos_avisocorreo" ("consulta_id");
CREATE INDEX "datos_resolucionsoporte_responsable_id_8de17b6d" ON "datos_resolucionsoporte" ("responsable_id");

-- Privilegios mínimos del rol de la aplicación (igual que sql/privilegios.sql).
GRANT SELECT,INSERT ON public.datos_resolucionsoporte,public.datos_consultaproducto,public.datos_avisocorreo TO chilito_pkg_runtime;
GRANT UPDATE(estado,atendida_por_id,atendida_en) ON public.datos_consultaproducto TO chilito_pkg_runtime;
GRANT UPDATE(estado,intentos,ultimo_intento_en,aceptado_en) ON public.datos_avisocorreo TO chilito_pkg_runtime;

-- Capacidad nueva (Django la crearía al migrar). Sin asignarla a ninguna cuenta.
INSERT INTO public.auth_permission(name,content_type_id,codename)
 SELECT 'Atender consultas del producto',c.id,'atender_consultas' FROM public.django_content_type c
 WHERE c.app_label='datos' AND c.model='dispositivo'
 ON CONFLICT (content_type_id,codename) DO NOTHING;

INSERT INTO public.django_migrations(app,name,applied) VALUES('datos','0008_soporte_resuelto_y_buzon',now());

COMMIT;
