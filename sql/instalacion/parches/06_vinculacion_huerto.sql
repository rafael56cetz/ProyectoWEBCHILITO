-- Solo para una base que ya tiene datos.0009 (parche 05). Query Tool, como chilito_pkg_owner.
-- Vinculación de huertos: tabla de códigos (solo su resumen, nunca el código), capacidad vincular_huertos
-- (creada SIN asignar), índice «una cuenta, un huerto activo», auditoría y triggers de protección.
-- Privilegios nuevos del rol de la aplicación: leer, crear y cerrar códigos; CREAR membresías (no cambiarlas
-- ni borrarlas). El trigger membresia_exige_codigo exige, al confirmar, un código consumido coherente.
-- Es una sola transacción: si algo falla, no se aplica nada (ejecuta ROLLBACK; para limpiar el error).
BEGIN;

DO $$ BEGIN
 IF current_database() <> 'chilito_integracion_sinteticos' OR current_user <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a chilito_integracion_sinteticos como chilito_pkg_owner'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0009_consulta_archivada_a_atendida')
 THEN RAISE EXCEPTION 'Falta el parche 05_consulta_archivada_a_atendida.sql'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE (app='datos' AND name='0010_vinculacion_huerto')
           OR (app='huerto' AND name='0007_una_membresia_activa_por_cuenta'))
 THEN RAISE EXCEPTION 'Este parche ya está aplicado'; END IF;
 IF EXISTS(SELECT 1 FROM public.huerto_membresia WHERE activa GROUP BY usuario_id HAVING count(*)>1)
 THEN RAISE EXCEPTION 'Hay cuentas con más de un huerto activo: revísalas antes (la regla nueva es uno por cuenta)'; END IF;
END $$;

-- Esquema de huerto.0007 (generado con sqlmigrate; igual que migrate).
--
-- Create constraint membresia_activa_por_cuenta on model membresia
--
CREATE UNIQUE INDEX "membresia_activa_por_cuenta" ON "huerto_membresia" ("usuario_id") WHERE "activa";

-- Esquema de datos.0010 (generado con sqlmigrate; incluye los triggers).
--
-- Create model CodigoVinculacion
--
CREATE TABLE "datos_codigovinculacion" ("id" uuid NOT NULL PRIMARY KEY, "entrega" varchar(10) NOT NULL, "verificador" varchar(128) NOT NULL, "emitido_en" timestamp with time zone NOT NULL, "vence_en" timestamp with time zone NOT NULL, "intentos" smallint NOT NULL CHECK ("intentos" >= 0), "estado" varchar(12) NOT NULL, "envio" varchar(14) NOT NULL, "cerrado_en" timestamp with time zone NULL);
--
-- Change Meta options on dispositivo
--
-- (no-op)
--
-- Remove constraint auditoria_accion_valida from model auditoria
--
ALTER TABLE "datos_auditoria" DROP CONSTRAINT "auditoria_accion_valida";
--
-- Add field destinatario to codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD COLUMN "destinatario_id" bigint NOT NULL CONSTRAINT "datos_codigovinculac_destinatario_id_5f528941_fk_cuentas_u" REFERENCES "cuentas_usuario"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_codigovinculac_destinatario_id_5f528941_fk_cuentas_u" IMMEDIATE;
--
-- Add field emitido_por to codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD COLUMN "emitido_por_id" bigint NOT NULL CONSTRAINT "datos_codigovinculac_emitido_por_id_7f90f681_fk_cuentas_u" REFERENCES "cuentas_usuario"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_codigovinculac_emitido_por_id_7f90f681_fk_cuentas_u" IMMEDIATE;
--
-- Add field huerto to codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD COLUMN "huerto_id" bigint NOT NULL CONSTRAINT "datos_codigovinculacion_huerto_id_605a0bdb_fk_huerto_huerto_id" REFERENCES "huerto_huerto"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_codigovinculacion_huerto_id_605a0bdb_fk_huerto_huerto_id" IMMEDIATE;
--
-- Add field membresia to codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD COLUMN "membresia_id" bigint NULL UNIQUE CONSTRAINT "datos_codigovinculac_membresia_id_7329f237_fk_huerto_me" REFERENCES "huerto_membresia"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_codigovinculac_membresia_id_7329f237_fk_huerto_me" IMMEDIATE;
--
-- Add field vinculacion to auditoria
--
ALTER TABLE "datos_auditoria" ADD COLUMN "vinculacion_id" uuid NULL CONSTRAINT "datos_auditoria_vinculacion_id_40037548_fk_datos_cod" REFERENCES "datos_codigovinculacion"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "datos_auditoria_vinculacion_id_40037548_fk_datos_cod" IMMEDIATE;
--
-- Create constraint auditoria_accion_valida on model auditoria
--
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "auditoria_accion_valida" CHECK ("accion" IN ('maintenance', 'support-granted', 'support-revoked', 'token-requested', 'technical-opened', 'technical-closed', 'diagnostic-requested', 'request-recorded', 'version-validated', 'knowledge-saved', 'maintenance-corrected', 'maintenance-voided', 'case-resolved', 'mfa-reset', 'binding-issued', 'binding-revoked', 'binding-replaced', 'binding-consumed', 'binding-rejected', 'binding-locked', 'binding-limited'));
--
-- Create index vinculacion_estado_fecha_idx on field(s) estado, -emitido_en of model codigovinculacion
--
CREATE INDEX "vinculacion_estado_fecha_idx" ON "datos_codigovinculacion" ("estado", "emitido_en" DESC);
--
-- Create index vinculacion_entrega_idx on field(s) huerto, destinatario, entrega of model codigovinculacion
--
CREATE INDEX "vinculacion_entrega_idx" ON "datos_codigovinculacion" ("huerto_id", "destinatario_id", "entrega");
--
-- Create constraint vinculacion_entrega_valida on model codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD CONSTRAINT "vinculacion_entrega_valida" CHECK ("entrega" IN ('presencial', 'correo'));
--
-- Create constraint vinculacion_estado_valido on model codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD CONSTRAINT "vinculacion_estado_valido" CHECK ("estado" IN ('pendiente', 'consumido', 'revocado', 'reemplazado', 'bloqueado'));
--
-- Create constraint vinculacion_envio_coherente on model codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD CONSTRAINT "vinculacion_envio_coherente" CHECK ((("entrega" = 'presencial' AND "envio" = 'no_aplica') OR ("entrega" = 'correo' AND "envio" IN ('pendiente', 'aceptado_smtp', 'rechazado', 'incierto'))));
--
-- Create constraint vinculacion_verificador_resumido on model codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD CONSTRAINT "vinculacion_verificador_resumido" CHECK ("verificador"::text ~  E'^[a-z0-9_]+\\$[^$]+\\$');
--
-- Create constraint vinculacion_vigencia_maxima on model codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD CONSTRAINT "vinculacion_vigencia_maxima" CHECK (("vence_en" > ("emitido_en") AND "vence_en" <= ("emitido_en" + '0:10:00'::interval)));
--
-- Create constraint vinculacion_intentos_limite on model codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD CONSTRAINT "vinculacion_intentos_limite" CHECK ("intentos" <= 5);
--
-- Create constraint vinculacion_cierre_coherente on model codigovinculacion
--
ALTER TABLE "datos_codigovinculacion" ADD CONSTRAINT "vinculacion_cierre_coherente" CHECK ((("cerrado_en" IS NULL AND "estado" = 'pendiente' AND "membresia_id" IS NULL) OR ("cerrado_en" IS NOT NULL AND "estado" = 'consumido' AND "membresia_id" IS NOT NULL) OR ("cerrado_en" IS NOT NULL AND "estado" IN ('revocado', 'reemplazado', 'bloqueado') AND "membresia_id" IS NULL)));
--
-- Create constraint vinculacion_pendiente_por_huerto on model codigovinculacion
--
CREATE UNIQUE INDEX "vinculacion_pendiente_por_huerto" ON "datos_codigovinculacion" ("huerto_id") WHERE "estado" = 'pendiente';
--
-- Create constraint vinculacion_pendiente_por_cuenta on model codigovinculacion
--
CREATE UNIQUE INDEX "vinculacion_pendiente_por_cuenta" ON "datos_codigovinculacion" ("destinatario_id") WHERE "estado" = 'pendiente';
--
-- Raw SQL operation
--

CREATE FUNCTION public.chilito_codigo_vinculacion() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'El código de vinculación se conserva' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'estado'-'intentos'-'cerrado_en'-'membresia_id'-'envio')
    IS DISTINCT FROM (to_jsonb(OLD)-'estado'-'intentos'-'cerrado_en'-'membresia_id'-'envio')
 OR NEW.intentos < OLD.intentos
 OR (OLD.estado<>'pendiente' AND (NEW.estado,NEW.intentos,NEW.cerrado_en,NEW.membresia_id)
                                IS DISTINCT FROM (OLD.estado,OLD.intentos,OLD.cerrado_en,OLD.membresia_id))
 OR (NEW.envio IS DISTINCT FROM OLD.envio AND OLD.envio<>'pendiente') THEN
  RAISE EXCEPTION 'El código de vinculación solo admite cerrarse una vez' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER codigo_vinculacion_historial BEFORE UPDATE OR DELETE ON public.datos_codigovinculacion
 FOR EACH ROW EXECUTE FUNCTION public.chilito_codigo_vinculacion();

CREATE FUNCTION public.chilito_membresia_por_codigo() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF current_user = (SELECT tableowner FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename='huerto_membresia') THEN
  RETURN NULL;
 END IF;
 IF NOT NEW.activa OR NOT EXISTS(SELECT 1 FROM public.datos_codigovinculacion c
   WHERE c.membresia_id=NEW.id AND c.estado='consumido' AND c.destinatario_id=NEW.usuario_id
     AND c.huerto_id=NEW.huerto_id AND c.cerrado_en<=c.vence_en) THEN
  RAISE EXCEPTION 'La membresía requiere un código de vinculación consumido' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER membresia_exige_codigo AFTER INSERT ON public.huerto_membresia
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.chilito_membresia_por_codigo();

CREATE INDEX "datos_codigovinculacion_destinatario_id_5f528941" ON "datos_codigovinculacion" ("destinatario_id");
CREATE INDEX "datos_codigovinculacion_emitido_por_id_7f90f681" ON "datos_codigovinculacion" ("emitido_por_id");
CREATE INDEX "datos_codigovinculacion_huerto_id_605a0bdb" ON "datos_codigovinculacion" ("huerto_id");
CREATE INDEX "datos_auditoria_vinculacion_id_40037548" ON "datos_auditoria" ("vinculacion_id");

-- Privilegios mínimos del rol de la aplicación (igual que sql/privilegios.sql).
GRANT SELECT,INSERT ON public.datos_codigovinculacion TO chilito_pkg_runtime;
GRANT UPDATE(estado,intentos,cerrado_en,membresia_id,envio) ON public.datos_codigovinculacion TO chilito_pkg_runtime;
GRANT INSERT ON public.huerto_membresia TO chilito_pkg_runtime;
DO $$ DECLARE seq text; BEGIN
 seq:=pg_get_serial_sequence('public.huerto_membresia','id');
 IF seq IS NOT NULL THEN EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %s TO chilito_pkg_runtime',seq); END IF;
END $$;

-- Capacidad nueva (Django la crearía al migrar). Sin asignarla a ninguna cuenta: usa asignar_capacidad.sql con vincular_huertos.
INSERT INTO public.auth_permission(name,content_type_id,codename)
 SELECT 'Emitir y revocar códigos de vinculación de huertos',c.id,'vincular_huertos' FROM public.django_content_type c
 WHERE c.app_label='datos' AND c.model='dispositivo'
 ON CONFLICT (content_type_id,codename) DO NOTHING;

INSERT INTO public.django_migrations(app,name,applied) VALUES
 ('huerto','0007_una_membresia_activa_por_cuenta',now()),
 ('datos','0010_vinculacion_huerto',now());

COMMIT;
