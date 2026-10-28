-- GENERATED from migrations. Do not edit DDL here; regenerate.
-- UPGRADE, not a standalone baseline installer. README describes both routes.
-- Requires Django/allauth baseline applied by tools/preparar_base.py and public schema.
-- Owner only. Run once with psql -v ON_ERROR_STOP=1 -f el_chilito.sql.
-- Transaction includes both DDL and the corresponding migration records; never --fake.
BEGIN;
SET LOCAL search_path=public,pg_catalog;
LOCK TABLE public.django_migrations IN EXCLUSIVE MODE;
DO $$ BEGIN
 IF current_user NOT IN (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) THEN
  RAISE EXCEPTION 'Use the database owner/migrator';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='contenttypes' AND name='0001_initial') THEN RAISE EXCEPTION 'Missing baseline migration contenttypes.0001_initial'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='contenttypes' AND name='0002_remove_content_type_name') THEN RAISE EXCEPTION 'Missing baseline migration contenttypes.0002_remove_content_type_name'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0001_initial') THEN RAISE EXCEPTION 'Missing baseline migration auth.0001_initial'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0002_alter_permission_name_max_length') THEN RAISE EXCEPTION 'Missing baseline migration auth.0002_alter_permission_name_max_length'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0003_alter_user_email_max_length') THEN RAISE EXCEPTION 'Missing baseline migration auth.0003_alter_user_email_max_length'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0004_alter_user_username_opts') THEN RAISE EXCEPTION 'Missing baseline migration auth.0004_alter_user_username_opts'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0005_alter_user_last_login_null') THEN RAISE EXCEPTION 'Missing baseline migration auth.0005_alter_user_last_login_null'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0006_require_contenttypes_0002') THEN RAISE EXCEPTION 'Missing baseline migration auth.0006_require_contenttypes_0002'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0007_alter_validators_add_error_messages') THEN RAISE EXCEPTION 'Missing baseline migration auth.0007_alter_validators_add_error_messages'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0008_alter_user_username_max_length') THEN RAISE EXCEPTION 'Missing baseline migration auth.0008_alter_user_username_max_length'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0009_alter_user_last_name_max_length') THEN RAISE EXCEPTION 'Missing baseline migration auth.0009_alter_user_last_name_max_length'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0010_alter_group_name_max_length') THEN RAISE EXCEPTION 'Missing baseline migration auth.0010_alter_group_name_max_length'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0011_update_proxy_permissions') THEN RAISE EXCEPTION 'Missing baseline migration auth.0011_update_proxy_permissions'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='auth' AND name='0012_alter_user_first_name_max_length') THEN RAISE EXCEPTION 'Missing baseline migration auth.0012_alter_user_first_name_max_length'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='cuentas' AND name='0001_initial') THEN RAISE EXCEPTION 'Missing baseline migration cuentas.0001_initial'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0001_initial') THEN RAISE EXCEPTION 'Missing baseline migration account.0001_initial'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0002_email_max_length') THEN RAISE EXCEPTION 'Missing baseline migration account.0002_email_max_length'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0003_alter_emailaddress_create_unique_verified_email') THEN RAISE EXCEPTION 'Missing baseline migration account.0003_alter_emailaddress_create_unique_verified_email'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0004_alter_emailaddress_drop_unique_email') THEN RAISE EXCEPTION 'Missing baseline migration account.0004_alter_emailaddress_drop_unique_email'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0005_emailaddress_idx_upper_email') THEN RAISE EXCEPTION 'Missing baseline migration account.0005_emailaddress_idx_upper_email'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0006_emailaddress_lower') THEN RAISE EXCEPTION 'Missing baseline migration account.0006_emailaddress_lower'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0007_emailaddress_idx_email') THEN RAISE EXCEPTION 'Missing baseline migration account.0007_emailaddress_idx_email'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0008_emailaddress_unique_primary_email_fixup') THEN RAISE EXCEPTION 'Missing baseline migration account.0008_emailaddress_unique_primary_email_fixup'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='account' AND name='0009_emailaddress_unique_primary_email') THEN RAISE EXCEPTION 'Missing baseline migration account.0009_emailaddress_unique_primary_email'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='cuentas' AND name='0002_cuotas_acceso') THEN RAISE EXCEPTION 'Missing baseline migration cuentas.0002_cuotas_acceso'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='cuentas' AND name='0003_confirmacion_registro_local') THEN RAISE EXCEPTION 'Missing baseline migration cuentas.0003_confirmacion_registro_local'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='huerto' AND name='0001_initial') THEN RAISE EXCEPTION 'Missing baseline migration huerto.0001_initial'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='huerto' AND name='0002_identidades_estables') THEN RAISE EXCEPTION 'Missing baseline migration huerto.0002_identidades_estables'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='huerto' AND name='0003_avisos') THEN RAISE EXCEPTION 'Missing baseline migration huerto.0003_avisos'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='huerto' AND name='0004_relaciones_avisos') THEN RAISE EXCEPTION 'Missing baseline migration huerto.0004_relaciones_avisos'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.django_migrations WHERE app='sessions' AND name='0001_initial') THEN RAISE EXCEPTION 'Missing baseline migration sessions.0001_initial'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='huerto' AND name='0005_aviso_aviso_titulo_significativo_and_more') THEN RAISE EXCEPTION 'Migration already applied huerto.0005_aviso_aviso_titulo_significativo_and_more; use Django migrate --check'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='huerto' AND name='0006_tres_zonas_y_lecturas') THEN RAISE EXCEPTION 'Migration already applied huerto.0006_tres_zonas_y_lecturas; use Django migrate --check'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0001_initial') THEN RAISE EXCEPTION 'Migration already applied datos.0001_initial; use Django migrate --check'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0002_integridad_historial') THEN RAISE EXCEPTION 'Migration already applied datos.0002_integridad_historial; use Django migrate --check'; END IF;
 IF EXISTS(SELECT 1 FROM public.django_migrations WHERE app='datos' AND name='0003_sesiontecnica_tecnica_admin_una_abierta') THEN RAISE EXCEPTION 'Migration already applied datos.0003_sesiontecnica_tecnica_admin_una_abierta; use Django migrate --check'; END IF;
END $$;
-- Migration huerto.0005_aviso_aviso_titulo_significativo_and_more
ALTER TABLE "huerto_aviso" ADD CONSTRAINT "aviso_titulo_significativo" CHECK ("titulo"::text ~  E'\\S');
ALTER TABLE "huerto_aviso" ADD CONSTRAINT "aviso_texto_significativo" CHECK ("descripcion"::text ~  E'\\S');
ALTER TABLE "huerto_huerto" ADD CONSTRAINT "huerto_nombre_significativo" CHECK ("nombre"::text ~  E'\\S');
ALTER TABLE "huerto_huerto" ADD CONSTRAINT "huerto_clave_significativa" CHECK ("clave"::text ~  E'\\S');
ALTER TABLE "huerto_zona" ADD CONSTRAINT "zona_nombre_significativo" CHECK ("nombre"::text ~  E'\\S');
ALTER TABLE "huerto_zona" ADD CONSTRAINT "zona_cultivo_significativo" CHECK ("cultivo"::text ~  E'\\S');

INSERT INTO django_migrations(app,name,applied) VALUES ('huerto','0005_aviso_aviso_titulo_significativo_and_more',statement_timestamp());

-- Migration huerto.0006_tres_zonas_y_lecturas

-- Serialize provisioning and reject invalid legacy rows before adding cardinality rules.
LOCK TABLE public.huerto_huerto, public.huerto_zona IN SHARE ROW EXCLUSIVE MODE;
INSERT INTO public.huerto_zona(huerto_id,numero,nombre,cultivo)
 SELECT h.id,n,'Planta '||n,'Chile habanero' FROM public.huerto_huerto h
 CROSS JOIN generate_series(1,3) n
 ON CONFLICT(huerto_id,numero) DO NOTHING;
CREATE FUNCTION public.chilito_crear_tres_zonas() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 INSERT INTO public.huerto_zona(huerto_id,numero,nombre,cultivo)
 SELECT NEW.id,n,'Planta '||n,'Chile habanero' FROM generate_series(1,3) n;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_crear_tres_zonas AFTER INSERT ON public.huerto_huerto
 FOR EACH ROW EXECUTE FUNCTION public.chilito_crear_tres_zonas();
CREATE FUNCTION public.chilito_conservar_zona() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'Las tres zonas se conservan; no se permite borrarlas' USING ERRCODE='23514';
END $$;
CREATE TRIGGER chilito_conservar_zona BEFORE DELETE ON public.huerto_zona
 FOR EACH ROW EXECUTE FUNCTION public.chilito_conservar_zona();
CREATE FUNCTION public.chilito_lectura_exige_membresia() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE garden bigint;
BEGIN
 SELECT huerto_id INTO garden FROM public.huerto_aviso WHERE id=NEW.aviso_id;
 PERFORM 1 FROM public.huerto_membresia
 WHERE usuario_id=NEW.usuario_id AND huerto_id=garden AND activa FOR UPDATE;
 IF NOT FOUND THEN
  RAISE EXCEPTION 'Membresia activa requerida' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_lectura_exige_membresia BEFORE INSERT OR UPDATE ON public.huerto_avisoleido
 FOR EACH ROW EXECUTE FUNCTION public.chilito_lectura_exige_membresia();
REVOKE ALL ON FUNCTION public.chilito_crear_tres_zonas(), public.chilito_conservar_zona(),
 public.chilito_lectura_exige_membresia() FROM PUBLIC;


INSERT INTO django_migrations(app,name,applied) VALUES ('huerto','0006_tres_zonas_y_lecturas',statement_timestamp());

-- Migration datos.0001_initial
CREATE TABLE "datos_dispositivo" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "identificador" varchar(128) NOT NULL UNIQUE, "creado_en" timestamp with time zone NOT NULL, "huerto_id" bigint NOT NULL UNIQUE);
CREATE TABLE "datos_casosoporte" ("id" uuid NOT NULL PRIMARY KEY, "incidente" varchar(16) NOT NULL, "creado_en" timestamp with time zone NOT NULL, "huerto_id" bigint NOT NULL, "solicitante_id" bigint NOT NULL, "dispositivo_id" bigint NOT NULL);
CREATE TABLE "datos_mantenimiento" ("id" uuid NOT NULL PRIMARY KEY, "tipo" varchar(16) NOT NULL, "registrado_en" timestamp with time zone NOT NULL, "actor_id" bigint NOT NULL, "huerto_id" bigint NOT NULL);
CREATE TABLE "datos_permisosoporte" ("id" uuid NOT NULL PRIMARY KEY, "consentimiento" boolean NOT NULL, "verificador" varchar(64) NOT NULL UNIQUE, "alcance" varchar(24) NOT NULL, "emitido_en" timestamp with time zone NOT NULL, "vence_en" timestamp with time zone NOT NULL, "revocado_en" timestamp with time zone NULL, "caso_id" uuid NOT NULL, "otorgante_id" bigint NOT NULL);
CREATE TABLE "datos_revisionconocimiento" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "contenido" text NOT NULL, "creada_en" timestamp with time zone NOT NULL, "autor_id" bigint NOT NULL);
CREATE TABLE "datos_sesiontecnica" ("id" uuid NOT NULL PRIMARY KEY, "iniciada_en" timestamp with time zone NOT NULL, "cerrada_en" timestamp with time zone NULL, "motivo_cierre" varchar(24) NOT NULL, "administrador_id" bigint NOT NULL, "permiso_id" uuid NOT NULL);
CREATE TABLE "datos_validacionversion" ("id" uuid NOT NULL PRIMARY KEY, "tipo" varchar(12) NOT NULL, "version" varchar(64) NOT NULL, "notas" text NOT NULL, "validada_en" timestamp with time zone NOT NULL, "actor_id" bigint NOT NULL);
CREATE TABLE "datos_solicitud" ("id" uuid NOT NULL PRIMARY KEY, "tipo" varchar(20) NOT NULL, "creada_en" timestamp with time zone NOT NULL, "estado" varchar(16) NOT NULL, "actor_id" bigint NOT NULL, "dispositivo_id" bigint NULL, "huerto_id" bigint NULL, "sesion_tecnica_id" uuid NULL, "validacion_id" uuid NULL UNIQUE);
CREATE TABLE "datos_auditoria" ("id" uuid NOT NULL PRIMARY KEY, "accion" varchar(32) NOT NULL, "resultado" varchar(16) NOT NULL, "creada_en" timestamp with time zone NOT NULL, "actor_id" bigint NOT NULL, "huerto_id" bigint NULL, "caso_id" uuid NULL, "mantenimiento_id" uuid NULL, "permiso_id" uuid NULL, "conocimiento_id" bigint NULL, "sesion_tecnica_id" uuid NULL, "solicitud_id" uuid NULL, "validacion_id" uuid NULL);
ALTER TABLE "datos_dispositivo" ADD CONSTRAINT "dispositivo_id_significativo" CHECK ("identificador"::text ~  E'\\S');
CREATE INDEX "caso_solicitante_fecha_idx" ON "datos_casosoporte" ("solicitante_id", "creado_en" DESC);
ALTER TABLE "datos_casosoporte" ADD CONSTRAINT "soporte_incidente_valido" CHECK ("incidente" IN ('pump', 'humidity', 'lamp', 'connection', 'other'));
CREATE INDEX "mant_huerto_fecha_idx" ON "datos_mantenimiento" ("huerto_id", "registrado_en" DESC);
ALTER TABLE "datos_mantenimiento" ADD CONSTRAINT "mantenimiento_tipo_valido" CHECK ("tipo" IN ('refill', 'substrate', 'germination', 'harvest', 'inspection'));
CREATE INDEX "permiso_caso_vence_idx" ON "datos_permisosoporte" ("caso_id", "vence_en");
ALTER TABLE "datos_permisosoporte" ADD CONSTRAINT "permiso_verificador_sha256" CHECK ("verificador"::text ~ '^[0-9a-f]{64}$');
ALTER TABLE "datos_permisosoporte" ADD CONSTRAINT "permiso_alcance_limitado" CHECK ("alcance" = 'diagnostico_incidente');
ALTER TABLE "datos_permisosoporte" ADD CONSTRAINT "permiso_ventana_24h" CHECK (("vence_en" > ("emitido_en") AND "vence_en" <= ("emitido_en" + '1 day 0:00:00'::interval)));
ALTER TABLE "datos_permisosoporte" ADD CONSTRAINT "permiso_revocacion_coherente" CHECK (("revocado_en" IS NULL OR "revocado_en" >= ("emitido_en")));
ALTER TABLE "datos_revisionconocimiento" ADD CONSTRAINT "conocimiento_significativo" CHECK ("contenido"::text ~  E'\\S');
ALTER TABLE "datos_revisionconocimiento" ADD CONSTRAINT "conocimiento_longitud" CHECK ((LENGTH("contenido") >= 20 AND LENGTH("contenido") <= 10000));
CREATE INDEX "tecnica_admin_cierre_idx" ON "datos_sesiontecnica" ("administrador_id", "cerrada_en");
ALTER TABLE "datos_sesiontecnica" ADD CONSTRAINT "sesion_tecnica_cierre_valido" CHECK ((("cerrada_en" IS NULL AND "motivo_cierre" = '') OR ("cerrada_en" >= ("iniciada_en") AND "cerrada_en" IS NOT NULL AND "motivo_cierre" IN ('explicit', 'revoked', 'replaced', 'logout', 'expiry'))));
ALTER TABLE "datos_validacionversion" ADD CONSTRAINT "version_tipo_valido" CHECK ("tipo" IN ('weights', 'math', 'rollback'));
ALTER TABLE "datos_validacionversion" ADD CONSTRAINT "version_formato_valido" CHECK ("version"::text ~ '^[a-zA-Z0-9][a-zA-Z0-9._-]{2,63}$');
ALTER TABLE "datos_validacionversion" ADD CONSTRAINT "version_notas_limite" CHECK (LENGTH("notas") <= 2000);
CREATE INDEX "solicitud_huerto_fecha_idx" ON "datos_solicitud" ("huerto_id", "creada_en" DESC);
ALTER TABLE "datos_solicitud" ADD CONSTRAINT "solicitud_sin_actuacion" CHECK ("estado" = 'pending');
ALTER TABLE "datos_solicitud" ADD CONSTRAINT "solicitud_tipo_valido" CHECK ("tipo" IN ('water', 'lamp-off', 'lamp-auto', 'weights', 'math', 'rollback', 'restart-node', 'restart-platform'));
ALTER TABLE "datos_solicitud" ADD CONSTRAINT "solicitud_referencias_por_tipo" CHECK ((("dispositivo_id" IS NOT NULL AND "huerto_id" IS NOT NULL AND "sesion_tecnica_id" IS NULL AND "tipo" IN ('water', 'lamp-off', 'lamp-auto') AND "validacion_id" IS NULL) OR ("dispositivo_id" IS NOT NULL AND "huerto_id" IS NOT NULL AND "sesion_tecnica_id" IS NOT NULL AND "tipo" = 'restart-node' AND "validacion_id" IS NULL) OR ("dispositivo_id" IS NULL AND "huerto_id" IS NULL AND "sesion_tecnica_id" IS NULL AND "tipo" IN ('weights', 'math', 'rollback') AND "validacion_id" IS NOT NULL) OR ("dispositivo_id" IS NULL AND "huerto_id" IS NULL AND "sesion_tecnica_id" IS NULL AND "tipo" = 'restart-platform' AND "validacion_id" IS NULL)));
CREATE INDEX "auditoria_actor_fecha_idx" ON "datos_auditoria" ("actor_id", "creada_en" DESC);
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "auditoria_accion_valida" CHECK ("accion" IN ('maintenance', 'support-granted', 'support-revoked', 'token-requested', 'technical-opened', 'technical-closed', 'diagnostic-requested', 'request-recorded', 'version-validated', 'knowledge-saved'));
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "auditoria_resultado_valido" CHECK ("resultado" IN ('recorded', 'pending'));
ALTER TABLE "datos_permisosoporte" ADD CONSTRAINT "permiso_consentimiento_explicito" CHECK ("consentimiento");
ALTER TABLE "datos_dispositivo" ADD CONSTRAINT "datos_dispositivo_huerto_id_16a3e7d3_fk_huerto_huerto_id" FOREIGN KEY ("huerto_id") REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_dispositivo_identificador_a63a5a39_like" ON "datos_dispositivo" ("identificador" varchar_pattern_ops);
ALTER TABLE "datos_casosoporte" ADD CONSTRAINT "datos_casosoporte_huerto_id_a4225f5a_fk_huerto_huerto_id" FOREIGN KEY ("huerto_id") REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_casosoporte" ADD CONSTRAINT "datos_casosoporte_solicitante_id_a98a04ec_fk_cuentas_usuario_id" FOREIGN KEY ("solicitante_id") REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_casosoporte" ADD CONSTRAINT "datos_casosoporte_dispositivo_id_70c6c5a4_fk_datos_dis" FOREIGN KEY ("dispositivo_id") REFERENCES "datos_dispositivo" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_casosoporte_huerto_id_a4225f5a" ON "datos_casosoporte" ("huerto_id");
CREATE INDEX "datos_casosoporte_solicitante_id_a98a04ec" ON "datos_casosoporte" ("solicitante_id");
CREATE INDEX "datos_casosoporte_dispositivo_id_70c6c5a4" ON "datos_casosoporte" ("dispositivo_id");
ALTER TABLE "datos_mantenimiento" ADD CONSTRAINT "datos_mantenimiento_actor_id_ca229383_fk_cuentas_usuario_id" FOREIGN KEY ("actor_id") REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_mantenimiento" ADD CONSTRAINT "datos_mantenimiento_huerto_id_6787022f_fk_huerto_huerto_id" FOREIGN KEY ("huerto_id") REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_mantenimiento_actor_id_ca229383" ON "datos_mantenimiento" ("actor_id");
CREATE INDEX "datos_mantenimiento_huerto_id_6787022f" ON "datos_mantenimiento" ("huerto_id");
ALTER TABLE "datos_permisosoporte" ADD CONSTRAINT "datos_permisosoporte_caso_id_75c4d803_fk_datos_casosoporte_id" FOREIGN KEY ("caso_id") REFERENCES "datos_casosoporte" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_permisosoporte" ADD CONSTRAINT "datos_permisosoporte_otorgante_id_b72af916_fk_cuentas_u" FOREIGN KEY ("otorgante_id") REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_permisosoporte_verificador_486a16ab_like" ON "datos_permisosoporte" ("verificador" varchar_pattern_ops);
CREATE INDEX "datos_permisosoporte_caso_id_75c4d803" ON "datos_permisosoporte" ("caso_id");
CREATE INDEX "datos_permisosoporte_otorgante_id_b72af916" ON "datos_permisosoporte" ("otorgante_id");
ALTER TABLE "datos_revisionconocimiento" ADD CONSTRAINT "datos_revisionconoci_autor_id_3eeed166_fk_cuentas_u" FOREIGN KEY ("autor_id") REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_revisionconocimiento_autor_id_3eeed166" ON "datos_revisionconocimiento" ("autor_id");
ALTER TABLE "datos_sesiontecnica" ADD CONSTRAINT "datos_sesiontecnica_administrador_id_d4d5ce0f_fk_cuentas_u" FOREIGN KEY ("administrador_id") REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_sesiontecnica" ADD CONSTRAINT "datos_sesiontecnica_permiso_id_fa478ed3_fk_datos_per" FOREIGN KEY ("permiso_id") REFERENCES "datos_permisosoporte" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_sesiontecnica_administrador_id_d4d5ce0f" ON "datos_sesiontecnica" ("administrador_id");
CREATE INDEX "datos_sesiontecnica_permiso_id_fa478ed3" ON "datos_sesiontecnica" ("permiso_id");
ALTER TABLE "datos_validacionversion" ADD CONSTRAINT "datos_validacionversion_actor_id_a4d4367c_fk_cuentas_usuario_id" FOREIGN KEY ("actor_id") REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_validacionversion_actor_id_a4d4367c" ON "datos_validacionversion" ("actor_id");
ALTER TABLE "datos_solicitud" ADD CONSTRAINT "datos_solicitud_actor_id_d55a761a_fk_cuentas_usuario_id" FOREIGN KEY ("actor_id") REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_solicitud" ADD CONSTRAINT "datos_solicitud_dispositivo_id_1607985b_fk_datos_dispositivo_id" FOREIGN KEY ("dispositivo_id") REFERENCES "datos_dispositivo" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_solicitud" ADD CONSTRAINT "datos_solicitud_huerto_id_2c03652c_fk_huerto_huerto_id" FOREIGN KEY ("huerto_id") REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_solicitud" ADD CONSTRAINT "datos_solicitud_sesion_tecnica_id_b4ab2ccc_fk_datos_ses" FOREIGN KEY ("sesion_tecnica_id") REFERENCES "datos_sesiontecnica" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_solicitud" ADD CONSTRAINT "datos_solicitud_validacion_id_0be37b51_fk_datos_val" FOREIGN KEY ("validacion_id") REFERENCES "datos_validacionversion" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_solicitud_actor_id_d55a761a" ON "datos_solicitud" ("actor_id");
CREATE INDEX "datos_solicitud_dispositivo_id_1607985b" ON "datos_solicitud" ("dispositivo_id");
CREATE INDEX "datos_solicitud_huerto_id_2c03652c" ON "datos_solicitud" ("huerto_id");
CREATE INDEX "datos_solicitud_sesion_tecnica_id_b4ab2ccc" ON "datos_solicitud" ("sesion_tecnica_id");
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_actor_id_c36e3472_fk_cuentas_usuario_id" FOREIGN KEY ("actor_id") REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_huerto_id_f65d310e_fk_huerto_huerto_id" FOREIGN KEY ("huerto_id") REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_caso_id_1230ac45_fk_datos_casosoporte_id" FOREIGN KEY ("caso_id") REFERENCES "datos_casosoporte" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_mantenimiento_id_1a8db11e_fk_datos_man" FOREIGN KEY ("mantenimiento_id") REFERENCES "datos_mantenimiento" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_permiso_id_971e8bf2_fk_datos_permisosoporte_id" FOREIGN KEY ("permiso_id") REFERENCES "datos_permisosoporte" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_conocimiento_id_eac685d6_fk_datos_rev" FOREIGN KEY ("conocimiento_id") REFERENCES "datos_revisionconocimiento" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_sesion_tecnica_id_37f600f0_fk_datos_ses" FOREIGN KEY ("sesion_tecnica_id") REFERENCES "datos_sesiontecnica" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_solicitud_id_fb9082bc_fk_datos_solicitud_id" FOREIGN KEY ("solicitud_id") REFERENCES "datos_solicitud" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "datos_auditoria" ADD CONSTRAINT "datos_auditoria_validacion_id_e1a8c181_fk_datos_val" FOREIGN KEY ("validacion_id") REFERENCES "datos_validacionversion" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "datos_auditoria_actor_id_c36e3472" ON "datos_auditoria" ("actor_id");
CREATE INDEX "datos_auditoria_huerto_id_f65d310e" ON "datos_auditoria" ("huerto_id");
CREATE INDEX "datos_auditoria_caso_id_1230ac45" ON "datos_auditoria" ("caso_id");
CREATE INDEX "datos_auditoria_mantenimiento_id_1a8db11e" ON "datos_auditoria" ("mantenimiento_id");
CREATE INDEX "datos_auditoria_permiso_id_971e8bf2" ON "datos_auditoria" ("permiso_id");
CREATE INDEX "datos_auditoria_conocimiento_id_eac685d6" ON "datos_auditoria" ("conocimiento_id");
CREATE INDEX "datos_auditoria_sesion_tecnica_id_37f600f0" ON "datos_auditoria" ("sesion_tecnica_id");
CREATE INDEX "datos_auditoria_solicitud_id_fb9082bc" ON "datos_auditoria" ("solicitud_id");
CREATE INDEX "datos_auditoria_validacion_id_e1a8c181" ON "datos_auditoria" ("validacion_id");

INSERT INTO django_migrations(app,name,applied) VALUES ('datos','0001_initial',statement_timestamp());

-- Migration datos.0002_integridad_historial

CREATE FUNCTION public.chilito_historial_inmutable() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'Historial inmutable; no se permite alterar ni borrar' USING ERRCODE='23514';
END $$;
CREATE FUNCTION public.chilito_permiso_revocar() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'El permiso se conserva' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'revocado_en') IS DISTINCT FROM (to_jsonb(OLD)-'revocado_en')
 OR OLD.revocado_en IS NOT NULL AND NEW.revocado_en IS DISTINCT FROM OLD.revocado_en
 OR NEW.revocado_en IS NULL THEN
  RAISE EXCEPTION 'Solo se admite revocacion irreversible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION public.chilito_tecnica_cerrar() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'La sesion tecnica se conserva' USING ERRCODE='23514';
 END IF;
 IF (to_jsonb(NEW)-'cerrada_en'-'motivo_cierre') IS DISTINCT FROM (to_jsonb(OLD)-'cerrada_en'-'motivo_cierre')
 OR OLD.cerrada_en IS NOT NULL AND (NEW.cerrada_en IS DISTINCT FROM OLD.cerrada_en OR NEW.motivo_cierre IS DISTINCT FROM OLD.motivo_cierre)
 OR NEW.cerrada_en IS NULL THEN
  RAISE EXCEPTION 'Solo se admite cierre irreversible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION public.chilito_datos_relaciones() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE c public.datos_casosoporte%ROWTYPE; p public.datos_permisosoporte%ROWTYPE;
        t public.datos_sesiontecnica%ROWTYPE; v public.datos_validacionversion%ROWTYPE;
        s public.datos_solicitud%ROWTYPE; g bigint; a bigint;
BEGIN
 IF TG_TABLE_NAME='datos_casosoporte' THEN
  IF NOT EXISTS(SELECT 1 FROM public.datos_dispositivo WHERE id=NEW.dispositivo_id AND huerto_id=NEW.huerto_id) THEN
   RAISE EXCEPTION 'Dispositivo de otro huerto' USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='datos_permisosoporte' THEN
  SELECT * INTO c FROM public.datos_casosoporte WHERE id=NEW.caso_id;
  IF NEW.otorgante_id IS DISTINCT FROM c.solicitante_id THEN
   RAISE EXCEPTION 'Permiso de otro solicitante' USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='datos_sesiontecnica' THEN
  SELECT * INTO p FROM public.datos_permisosoporte WHERE id=NEW.permiso_id FOR UPDATE;
  IF p.revocado_en IS NOT NULL OR p.vence_en<=statement_timestamp()
   OR NEW.iniciada_en<p.emitido_en OR NEW.iniciada_en>=p.vence_en THEN
   RAISE EXCEPTION 'Permiso no vigente' USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='datos_solicitud' THEN
  IF NEW.dispositivo_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_dispositivo WHERE id=NEW.dispositivo_id AND huerto_id=NEW.huerto_id) THEN
   RAISE EXCEPTION 'Dispositivo de otro huerto' USING ERRCODE='23514';
  END IF;
  IF NEW.validacion_id IS NOT NULL THEN
   SELECT * INTO v FROM public.datos_validacionversion WHERE id=NEW.validacion_id;
   IF v.actor_id IS DISTINCT FROM NEW.actor_id OR v.tipo IS DISTINCT FROM NEW.tipo THEN
    RAISE EXCEPTION 'Validacion de otro actor o tipo' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.sesion_tecnica_id IS NOT NULL THEN
   SELECT * INTO t FROM public.datos_sesiontecnica WHERE id=NEW.sesion_tecnica_id;
   SELECT * INTO p FROM public.datos_permisosoporte WHERE id=t.permiso_id FOR UPDATE;
   SELECT * INTO t FROM public.datos_sesiontecnica WHERE id=NEW.sesion_tecnica_id FOR UPDATE;
   SELECT * INTO c FROM public.datos_casosoporte WHERE id=p.caso_id;
   IF t.administrador_id IS DISTINCT FROM NEW.actor_id OR t.cerrada_en IS NOT NULL
    OR p.revocado_en IS NOT NULL OR p.vence_en<=statement_timestamp()
    OR NEW.huerto_id IS DISTINCT FROM c.huerto_id OR NEW.dispositivo_id IS DISTINCT FROM c.dispositivo_id THEN
    RAISE EXCEPTION 'Solicitud fuera de la autorizacion tecnica' USING ERRCODE='23514';
   END IF;
  END IF;
 ELSIF TG_TABLE_NAME='datos_auditoria' THEN
  IF NEW.caso_id IS NOT NULL THEN
   SELECT * INTO c FROM public.datos_casosoporte WHERE id=NEW.caso_id;
   IF NEW.huerto_id IS DISTINCT FROM c.huerto_id THEN
    RAISE EXCEPTION 'Auditoria de otro huerto' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.permiso_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_permisosoporte WHERE id=NEW.permiso_id AND caso_id=NEW.caso_id) THEN
   RAISE EXCEPTION 'Auditoria de otro permiso' USING ERRCODE='23514';
  END IF;
  IF NEW.solicitud_id IS NOT NULL THEN
   SELECT * INTO s FROM public.datos_solicitud WHERE id=NEW.solicitud_id;
   IF s.actor_id IS DISTINCT FROM NEW.actor_id OR s.huerto_id IS DISTINCT FROM NEW.huerto_id THEN
    RAISE EXCEPTION 'Auditoria de otra solicitud' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.mantenimiento_id IS NOT NULL THEN
   SELECT huerto_id,actor_id INTO g,a FROM public.datos_mantenimiento WHERE id=NEW.mantenimiento_id;
   IF g IS DISTINCT FROM NEW.huerto_id OR a IS DISTINCT FROM NEW.actor_id THEN
    RAISE EXCEPTION 'Auditoria de otro mantenimiento' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.validacion_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_validacionversion WHERE id=NEW.validacion_id AND actor_id=NEW.actor_id) THEN
   RAISE EXCEPTION 'Auditoria de otra validacion' USING ERRCODE='23514';
  END IF;
  IF NEW.conocimiento_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_revisionconocimiento WHERE id=NEW.conocimiento_id AND autor_id=NEW.actor_id) THEN
   RAISE EXCEPTION 'Auditoria de otra revision' USING ERRCODE='23514';
  END IF;
  IF NEW.sesion_tecnica_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.datos_sesiontecnica WHERE id=NEW.sesion_tecnica_id AND administrador_id=NEW.actor_id AND permiso_id=NEW.permiso_id) THEN
   RAISE EXCEPTION 'Auditoria de otra sesion' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER historial_dispositivo BEFORE UPDATE OR DELETE ON public.datos_dispositivo FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_mantenimiento BEFORE UPDATE OR DELETE ON public.datos_mantenimiento FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_casosoporte BEFORE UPDATE OR DELETE ON public.datos_casosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_validacionversion BEFORE UPDATE OR DELETE ON public.datos_validacionversion FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_revisionconocimiento BEFORE UPDATE OR DELETE ON public.datos_revisionconocimiento FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_solicitud BEFORE UPDATE OR DELETE ON public.datos_solicitud FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_auditoria BEFORE UPDATE OR DELETE ON public.datos_auditoria FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();

CREATE TRIGGER permiso_solo_revocar BEFORE UPDATE OR DELETE ON public.datos_permisosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_permiso_revocar();
CREATE TRIGGER tecnica_solo_cerrar BEFORE UPDATE OR DELETE ON public.datos_sesiontecnica FOR EACH ROW EXECUTE FUNCTION public.chilito_tecnica_cerrar();
CREATE TRIGGER relacion_casosoporte BEFORE INSERT ON public.datos_casosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();
CREATE TRIGGER relacion_permisosoporte BEFORE INSERT ON public.datos_permisosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();
CREATE TRIGGER relacion_sesiontecnica BEFORE INSERT ON public.datos_sesiontecnica FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();
CREATE TRIGGER relacion_solicitud BEFORE INSERT ON public.datos_solicitud FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();
CREATE TRIGGER relacion_auditoria BEFORE INSERT ON public.datos_auditoria FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();

REVOKE ALL ON FUNCTION public.chilito_historial_inmutable(),public.chilito_permiso_revocar(),
 public.chilito_tecnica_cerrar(),public.chilito_datos_relaciones() FROM PUBLIC;

CREATE FUNCTION public.chilito_usuario_sin_privilegios() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF current_user='chilito_pkg_runtime' AND (NEW.is_staff OR NEW.is_superuser OR NOT NEW.is_active) THEN
  RAISE EXCEPTION 'El runtime no provisiona privilegios' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_usuario_sin_privilegios BEFORE INSERT ON public.cuentas_usuario
 FOR EACH ROW EXECUTE FUNCTION public.chilito_usuario_sin_privilegios();
REVOKE ALL ON FUNCTION public.chilito_usuario_sin_privilegios() FROM PUBLIC;


INSERT INTO django_migrations(app,name,applied) VALUES ('datos','0002_integridad_historial',statement_timestamp());

-- Migration datos.0003_sesiontecnica_tecnica_admin_una_abierta
CREATE UNIQUE INDEX "tecnica_admin_una_abierta" ON "datos_sesiontecnica" ("administrador_id") WHERE "cerrada_en" IS NULL;

INSERT INTO django_migrations(app,name,applied) VALUES ('datos','0003_sesiontecnica_tecnica_admin_una_abierta',statement_timestamp());
COMMIT;
