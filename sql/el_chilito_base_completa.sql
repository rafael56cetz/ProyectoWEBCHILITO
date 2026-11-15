-- =====================================================================================================
--  EL CHILITO · BASE DE DATOS COMPLETA (PostgreSQL 17)
--  Script único de instalación. Sustituye a 03_esquema_completo.sql y a los parches 01 a 08.
--  Deja la base exactamente igual que la aplicación actual (61 migraciones de Django ya aplicadas).
--  Explicación completa: sql/FUNCIONAMIENTO-BASE-DE-DATOS.md
--  No contiene contraseñas ni cuentas de personas.
-- =====================================================================================================
--
--  CÓMO SE INSTALA (tres pasos, una sola vez)
--  ------------------------------------------
--  PASO 1 · Como administrador del servidor (usuario postgres), conectado a la base «postgres».
--           Ejecuta estas líneas (quítales los dos guiones del principio):
--
--    CREATE ROLE chilito_pkg_owner   LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
--    CREATE ROLE chilito_pkg_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
--    ALTER ROLE chilito_pkg_runtime SET search_path = pg_catalog, public;
--
--           Después ponles contraseña en pgAdmin (Login/Group Roles › Definition). Nunca en este archivo.
--           Si los roles ya existen, salta este paso.
--
--  PASO 2 · Igual que el paso 1, pero ejecuta ESTA LÍNEA SOLA (CREATE DATABASE no admite ir acompañada):
--
--    CREATE DATABASE chilito_integracion_sinteticos OWNER chilito_pkg_owner;
--
--  PASO 3 · Conéctate a la base nueva como chilito_pkg_owner y ejecuta ESTE ARCHIVO COMPLETO.
--           Corre en una sola transacción: si algo falla, no queda nada a medias (pulsa Rollback).
--           Se detiene solo si la base no está vacía, si el usuario no es chilito_pkg_owner
--           o si el servidor no es PostgreSQL 17.
--
--  DESPUÉS · La persona administradora se registra en la página y luego se ejecuta
--            sql/designar_administrador.sql con su correo.
--
--  ÍNDICE DEL ARCHIVO
--    0. Comprobaciones de seguridad
--    1. Función de identidad de correo (la necesita un índice de cuentas)
--    2. Tablas internas de Django: migraciones, tipos, permisos, grupos y sesiones
--    3. Cuentas: usuarios, correos, segundo factor, cuotas y confirmación de registro
--    4. Huertos: huerto, zonas, membresías y avisos
--    5. Operación: dispositivos, mantenimiento, soporte, solicitudes, vinculación, guías, buzón, auditoría
--    6. Privacidad: textos legales, decisiones, cookies y estadísticas
--    7. Recibos de idempotencia
--    8. Reglas en la base: funciones y triggers
--    9. Datos iniciales: tipos, permisos y capacidades, textos legales, guías y registro de migraciones
--   10. Privilegios del rol de la aplicación (chilito_pkg_runtime)
--
--  Los nombres de restricciones e índices con sufijos como «_fk_…» o «_like» los eligió Django.
--  Se conservan tal cual: si se cambian, las migraciones futuras no los encontrarían.
-- =====================================================================================================

BEGIN;

-- =====================================================================================================
-- 0. COMPROBACIONES DE SEGURIDAD
-- =====================================================================================================
DO $$ BEGIN
 IF current_user <> 'chilito_pkg_owner' OR session_user <> 'chilito_pkg_owner'
 OR (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conéctate como chilito_pkg_owner a una base cuyo propietario sea chilito_pkg_owner'; END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 17
 THEN RAISE EXCEPTION 'Este script está preparado para PostgreSQL 17'; END IF;
 IF EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public')
 THEN RAISE EXCEPTION 'La base no está vacía: este script solo instala una base nueva'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='chilito_pkg_runtime')
 THEN RAISE EXCEPTION 'Falta el rol chilito_pkg_runtime: ejecuta antes el paso 1'; END IF;
END $$;


-- =====================================================================================================
-- 1. FUNCIÓN DE IDENTIDAD DE CORREO
--    Convierte un correo en su «buzón real» para impedir cuentas duplicadas:
--    en Gmail ignora mayúsculas, puntos y lo que va tras «+», y trata googlemail.com como gmail.com.
--    Ej.: Juan.Perez+huerto@googlemail.com  →  juanperez@gmail.com
-- =====================================================================================================
CREATE FUNCTION public.chilito_identidad_correo(correo text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
 SELECT CASE WHEN lower(split_part(btrim(correo),'@',2)) IN ('gmail.com','googlemail.com')
   THEN replace(split_part(lower(split_part(btrim(correo),'@',1)),'+',1),'.','') || '@gmail.com'
   ELSE lower(btrim(correo)) END
$$;


-- =====================================================================================================
-- 2. TABLAS INTERNAS DE DJANGO
-- =====================================================================================================

-- Qué migraciones están aplicadas. Django la consulta al arrancar.
CREATE TABLE "django_migrations" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "app" varchar(255) NOT NULL,
 "name" varchar(255) NOT NULL,
 "applied" timestamp with time zone NOT NULL);

-- Catálogo de modelos (una fila por tabla de la aplicación). Los permisos cuelgan de aquí.
CREATE TABLE "django_content_type" (
 "id" integer NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "app_label" varchar(100) NOT NULL,
 "model" varchar(100) NOT NULL,
 CONSTRAINT "django_content_type_app_label_model_76bd3d3b_uniq" UNIQUE ("app_label", "model"));

-- Permisos. Las seis «capacidades» de administración son filas de esta tabla.
CREATE TABLE "auth_permission" (
 "id" integer NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "name" varchar(255) NOT NULL,
 "content_type_id" integer NOT NULL
  CONSTRAINT "auth_permission_content_type_id_2f476e4b_fk_django_co" REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
 "codename" varchar(100) NOT NULL,
 CONSTRAINT "auth_permission_content_type_id_codename_01ab375a_uniq" UNIQUE ("content_type_id", "codename"));
CREATE INDEX "auth_permission_content_type_id_2f476e4b" ON "auth_permission" ("content_type_id");

-- Grupos de permisos (hoy no se usan, pero Django los consulta).
CREATE TABLE "auth_group" (
 "id" integer NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "name" varchar(150) NOT NULL UNIQUE);
CREATE INDEX "auth_group_name_a6ea08ec_like" ON "auth_group" ("name" varchar_pattern_ops);

CREATE TABLE "auth_group_permissions" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "group_id" integer NOT NULL
  CONSTRAINT "auth_group_permissions_group_id_b120cbf9_fk_auth_group_id" REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED,
 "permission_id" integer NOT NULL
  CONSTRAINT "auth_group_permissio_permission_id_84c5c92e_fk_auth_perm" REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" UNIQUE ("group_id", "permission_id"));
CREATE INDEX "auth_group_permissions_group_id_b120cbf9" ON "auth_group_permissions" ("group_id");
CREATE INDEX "auth_group_permissions_permission_id_84c5c92e" ON "auth_group_permissions" ("permission_id");

-- Sesiones web. La cookie «sessionid» del navegador es la clave de esta tabla; los datos van firmados.
CREATE TABLE "django_session" (
 "session_key" varchar(40) NOT NULL PRIMARY KEY,
 "session_data" text NOT NULL,
 "expire_date" timestamp with time zone NOT NULL);
CREATE INDEX "django_session_session_key_c0390e0f_like" ON "django_session" ("session_key" varchar_pattern_ops);
CREATE INDEX "django_session_expire_date_a5c62663" ON "django_session" ("expire_date");


-- =====================================================================================================
-- 3. CUENTAS
-- =====================================================================================================

-- Cuentas. El correo es el usuario. La contraseña se guarda solo como resumen (hash), nunca en claro.
-- is_staff / is_superuser no se usan: el rol de la aplicación no puede crear cuentas con ellos.
CREATE TABLE "cuentas_usuario" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "password" varchar(128) NOT NULL,
 "last_login" timestamp with time zone NULL,
 "is_superuser" boolean NOT NULL,
 "first_name" varchar(150) NOT NULL,
 "last_name" varchar(150) NOT NULL,
 "is_staff" boolean NOT NULL,
 "is_active" boolean NOT NULL,
 "date_joined" timestamp with time zone NOT NULL,
 "email" varchar(254) NOT NULL UNIQUE,
 "alias" varchar(64) NOT NULL,
 "bienvenida_atendida_en" timestamp with time zone NULL,
 CONSTRAINT "usuario_alias_vacio_o_con_texto" CHECK (("alias" = '' OR "alias"::text ~  E'\\S')));
CREATE UNIQUE INDEX "usuario_email_ci_unico" ON "cuentas_usuario" ((LOWER("email")));
CREATE UNIQUE INDEX "usuario_identidad_correo_unica" ON "cuentas_usuario" ((public.chilito_identidad_correo("email")));
CREATE INDEX "cuentas_usuario_email_86dc1160_like" ON "cuentas_usuario" ("email" varchar_pattern_ops);

-- Grupos de cada cuenta (sin uso hoy).
CREATE TABLE "cuentas_usuario_groups" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "usuario_id" bigint NOT NULL
  CONSTRAINT "cuentas_usuario_grou_usuario_id_251ff583_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "group_id" integer NOT NULL
  CONSTRAINT "cuentas_usuario_groups_group_id_e6725cc8_fk_auth_group_id" REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "cuentas_usuario_groups_usuario_id_group_id_f5ef6c73_uniq" UNIQUE ("usuario_id", "group_id"));
CREATE INDEX "cuentas_usuario_groups_usuario_id_251ff583" ON "cuentas_usuario_groups" ("usuario_id");
CREATE INDEX "cuentas_usuario_groups_group_id_e6725cc8" ON "cuentas_usuario_groups" ("group_id");

-- Permisos de cada cuenta. AQUÍ SE HACE ADMINISTRADORA A UNA CUENTA: una fila por capacidad.
CREATE TABLE "cuentas_usuario_user_permissions" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "usuario_id" bigint NOT NULL
  CONSTRAINT "cuentas_usuario_user_usuario_id_5a9718f1_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "permission_id" integer NOT NULL
  CONSTRAINT "cuentas_usuario_user_permission_id_1753ad79_fk_auth_perm" REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "cuentas_usuario_user_per_usuario_id_permission_id_26c0acea_uniq" UNIQUE ("usuario_id", "permission_id"));
CREATE INDEX "cuentas_usuario_user_permissions_usuario_id_5a9718f1" ON "cuentas_usuario_user_permissions" ("usuario_id");
CREATE INDEX "cuentas_usuario_user_permissions_permission_id_1753ad79" ON "cuentas_usuario_user_permissions" ("permission_id");

-- Correos de cada cuenta y si están verificados (django-allauth). Sin correo verificado no se entra.
CREATE TABLE "account_emailaddress" (
 "id" integer NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "email" varchar(254) NOT NULL,
 "verified" boolean NOT NULL,
 "primary" boolean NOT NULL,
 "user_id" bigint NOT NULL
  CONSTRAINT "account_emailaddress_user_id_2c513194_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "account_emailaddress_user_id_email_987c8728_uniq" UNIQUE ("user_id", "email"));
CREATE UNIQUE INDEX "unique_verified_email" ON "account_emailaddress" ("email") WHERE "verified";
CREATE UNIQUE INDEX "unique_primary_email" ON "account_emailaddress" ("user_id", "primary") WHERE "primary";
CREATE INDEX "account_emailaddress_user_id_2c513194" ON "account_emailaddress" ("user_id");
CREATE INDEX "account_emailaddress_email_03be32b2" ON "account_emailaddress" ("email");
CREATE INDEX "account_emailaddress_email_03be32b2_like" ON "account_emailaddress" ("email" varchar_pattern_ops);

-- Confirmaciones por enlace (allauth). La app verifica por CÓDIGO guardado en la sesión, así que queda vacía.
CREATE TABLE "account_emailconfirmation" (
 "id" integer NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "created" timestamp with time zone NOT NULL,
 "sent" timestamp with time zone NULL,
 "key" varchar(64) NOT NULL UNIQUE,
 "email_address_id" integer NOT NULL
  CONSTRAINT "account_emailconfirm_email_address_id_5b7f8c58_fk_account_e" REFERENCES "account_emailaddress" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX "account_emailconfirmation_key_f43612bd_like" ON "account_emailconfirmation" ("key" varchar_pattern_ops);
CREATE INDEX "account_emailconfirmation_email_address_id_5b7f8c58" ON "account_emailconfirmation" ("email_address_id");

-- Segundo factor: type = 'totp' (app autenticadora), 'recovery_codes' (códigos de recuperación)
-- o 'webauthn' (llaves de acceso). Los secretos de TOTP y de recuperación van cifrados (Fernet).
CREATE TABLE "mfa_authenticator" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "type" varchar(20) NOT NULL,
 "data" jsonb NOT NULL,
 "user_id" bigint NOT NULL
  CONSTRAINT "mfa_authenticator_user_id_0c3a50c0_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "created_at" timestamp with time zone NOT NULL,
 "last_used_at" timestamp with time zone NULL);
CREATE UNIQUE INDEX "unique_authenticator_type" ON "mfa_authenticator" ("user_id", "type") WHERE "type" IN ('totp', 'recovery_codes');
CREATE INDEX "mfa_authenticator_user_id_0c3a50c0" ON "mfa_authenticator" ("user_id");

-- Caché de Django en la base: contadores de límites de uso (intentos de acceso, formulario, cookies…).
CREATE TABLE "cuentas_cuotas_acceso" (
 "cache_key" varchar(255) NOT NULL PRIMARY KEY,
 "value" text NOT NULL,
 "expires" timestamp with time zone NOT NULL);
CREATE INDEX "cuentas_cuotas_acceso_cache_key_9ba7b803_like" ON "cuentas_cuotas_acceso" ("cache_key" varchar_pattern_ops);
CREATE INDEX "cuentas_cuotas_acceso_expires_c8e0ee83" ON "cuentas_cuotas_acceso" ("expires");

-- Constancia técnica de que, al registrarse, la persona marcó las dos casillas. Una fila por cuenta.
CREATE TABLE "cuentas_confirmacionregistrolocal" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "confirmado_en" timestamp with time zone NOT NULL,
 "casilla_marcada" boolean NOT NULL,
 "documentos_pendientes" boolean NOT NULL,
 "usuario_id" bigint NOT NULL UNIQUE
  CONSTRAINT "cuentas_confirmacion_usuario_id_e55a407a_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "registro_local_solo_confirmacion_tecnica" CHECK (("casilla_marcada" AND "documentos_pendientes")));


-- =====================================================================================================
-- 4. HUERTOS
-- =====================================================================================================

-- Cada huerto físico. Al insertar uno, un trigger crea sus 3 zonas (plantas).
CREATE TABLE "huerto_huerto" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "clave" varchar(64) NOT NULL UNIQUE,
 "nombre" varchar(100) NOT NULL,
 "zona_horaria" varchar(64) NOT NULL,
 "creado_en" timestamp with time zone NOT NULL,
 CONSTRAINT "huerto_nombre_no_vacio" CHECK (NOT ("nombre" = '')),
 CONSTRAINT "huerto_clave_no_vacia" CHECK (NOT ("clave" = '')),
 CONSTRAINT "huerto_nombre_significativo" CHECK ("nombre"::text ~  E'\\S'),
 CONSTRAINT "huerto_clave_significativa" CHECK ("clave"::text ~  E'\\S'));
CREATE INDEX "huerto_huerto_clave_5cb8f636_like" ON "huerto_huerto" ("clave" varchar_pattern_ops);

-- Qué cuenta tiene qué huerto. Una sola membresía activa por cuenta. Solo nace al consumir un código.
CREATE TABLE "huerto_membresia" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "activa" boolean NOT NULL,
 "asignada_en" timestamp with time zone NOT NULL,
 "huerto_id" bigint NOT NULL
  CONSTRAINT "huerto_membresia_huerto_id_334fadaa_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 "usuario_id" bigint NOT NULL
  CONSTRAINT "huerto_membresia_usuario_id_100403be_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "membresia_unica" UNIQUE ("usuario_id", "huerto_id"));
CREATE UNIQUE INDEX "membresia_activa_por_cuenta" ON "huerto_membresia" ("usuario_id") WHERE "activa";
CREATE INDEX "huerto_membresia_huerto_id_334fadaa" ON "huerto_membresia" ("huerto_id");
CREATE INDEX "huerto_membresia_usuario_id_100403be" ON "huerto_membresia" ("usuario_id");

-- Las tres plantas de cada huerto (numero 1, 2 y 3). No se borran.
CREATE TABLE "huerto_zona" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "numero" smallint NOT NULL CHECK ("numero" >= 0),
 "nombre" varchar(80) NOT NULL,
 "cultivo" varchar(80) NOT NULL,
 "huerto_id" bigint NOT NULL
  CONSTRAINT "huerto_zona_huerto_id_a9fba9c9_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "zona_numero_unico" UNIQUE ("huerto_id", "numero"),
 CONSTRAINT "zona_rango_1_3" CHECK (("numero" >= 1 AND "numero" <= 3)),
 CONSTRAINT "zona_nombre_no_vacio" CHECK (NOT ("nombre" = '')),
 CONSTRAINT "zona_nombre_significativo" CHECK ("nombre"::text ~  E'\\S'),
 CONSTRAINT "zona_cultivo_significativo" CHECK ("cultivo"::text ~  E'\\S'));
CREATE INDEX "huerto_zona_huerto_id_a9fba9c9" ON "huerto_zona" ("huerto_id");

-- Avisos del huerto (pantalla «Avisos»). Hoy ningún proceso los genera: la tabla está lista.
CREATE TABLE "huerto_aviso" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "severidad" varchar(16) NOT NULL,
 "titulo" varchar(160) NOT NULL,
 "descripcion" text NOT NULL,
 "recomendacion" text NOT NULL,
 "creado_en" timestamp with time zone NOT NULL,
 "resuelto_en" timestamp with time zone NULL,
 "huerto_id" bigint NOT NULL
  CONSTRAINT "huerto_aviso_huerto_id_aea765d7_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 "zona_id" bigint NULL
  CONSTRAINT "huerto_aviso_zona_id_35307045_fk_huerto_zona_id" REFERENCES "huerto_zona" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "aviso_severidad_valida" CHECK ("severidad" IN ('informacion', 'advertencia', 'critico')),
 CONSTRAINT "aviso_titulo_no_vacio" CHECK (NOT ("titulo" = '')),
 CONSTRAINT "aviso_descripcion_no_vacia" CHECK (NOT ("descripcion" = '')),
 CONSTRAINT "aviso_fechas_coherentes" CHECK (("resuelto_en" IS NULL OR "resuelto_en" >= ("creado_en"))),
 CONSTRAINT "aviso_titulo_significativo" CHECK ("titulo"::text ~  E'\\S'),
 CONSTRAINT "aviso_texto_significativo" CHECK ("descripcion"::text ~  E'\\S'));
CREATE INDEX "aviso_huerto_orden_idx" ON "huerto_aviso" ("huerto_id", "creado_en" DESC, "id" DESC);
CREATE INDEX "huerto_aviso_huerto_id_aea765d7" ON "huerto_aviso" ("huerto_id");
CREATE INDEX "huerto_aviso_zona_id_35307045" ON "huerto_aviso" ("zona_id");

-- Qué avisos leyó cada cuenta.
CREATE TABLE "huerto_avisoleido" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "leido_en" timestamp with time zone NOT NULL,
 "aviso_id" bigint NOT NULL
  CONSTRAINT "huerto_avisoleido_aviso_id_7267cafb_fk_huerto_aviso_id" REFERENCES "huerto_aviso" ("id") DEFERRABLE INITIALLY DEFERRED,
 "usuario_id" bigint NOT NULL
  CONSTRAINT "huerto_avisoleido_usuario_id_85feffc6_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "aviso_usuario_unico" UNIQUE ("aviso_id", "usuario_id"));
CREATE INDEX "huerto_avisoleido_aviso_id_7267cafb" ON "huerto_avisoleido" ("aviso_id");
CREATE INDEX "huerto_avisoleido_usuario_id_85feffc6" ON "huerto_avisoleido" ("usuario_id");


-- =====================================================================================================
-- 5. OPERACIÓN
-- =====================================================================================================

-- El equipo (ESP32) de cada huerto. Un dispositivo por huerto. No se modifica ni se borra.
CREATE TABLE "datos_dispositivo" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "identificador" varchar(128) NOT NULL UNIQUE,
 "creado_en" timestamp with time zone NOT NULL,
 "huerto_id" bigint NOT NULL UNIQUE
  CONSTRAINT "datos_dispositivo_huerto_id_16a3e7d3_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "dispositivo_id_significativo" CHECK ("identificador"::text ~  E'\\S'));
CREATE INDEX "datos_dispositivo_identificador_a63a5a39_like" ON "datos_dispositivo" ("identificador" varchar_pattern_ops);

-- Cuidados que registra la persona («Ya rellené el depósito», «Registrar cosecha»…). Nunca cambian.
-- tipo: refill = depósito, substrate = sustrato, germination = germinación, harvest = cosecha, inspection = inspección.
CREATE TABLE "datos_mantenimiento" (
 "id" uuid NOT NULL PRIMARY KEY,
 "tipo" varchar(16) NOT NULL,
 "registrado_en" timestamp with time zone NOT NULL,
 "actor_id" bigint NOT NULL
  CONSTRAINT "datos_mantenimiento_actor_id_ca229383_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "huerto_id" bigint NOT NULL
  CONSTRAINT "datos_mantenimiento_huerto_id_6787022f_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "mantenimiento_tipo_valido" CHECK ("tipo" IN ('refill', 'substrate', 'germination', 'harvest', 'inspection')));
CREATE INDEX "mant_huerto_fecha_idx" ON "datos_mantenimiento" ("huerto_id", "registrado_en" DESC);
CREATE INDEX "datos_mantenimiento_actor_id_ca229383" ON "datos_mantenimiento" ("actor_id");
CREATE INDEX "datos_mantenimiento_huerto_id_6787022f" ON "datos_mantenimiento" ("huerto_id");

-- Qué huertos puede corregir cada administradora con la capacidad gestionar_mantenimientos.
CREATE TABLE "datos_asignacionmantenimiento" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "activa" boolean NOT NULL,
 "asignada_en" timestamp with time zone NOT NULL,
 "huerto_id" bigint NOT NULL
  CONSTRAINT "datos_asignacionmant_huerto_id_bac530fd_fk_huerto_hu" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 "usuario_id" bigint NOT NULL
  CONSTRAINT "datos_asignacionmant_usuario_id_db5be448_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "asignacion_mant_unica" UNIQUE ("usuario_id", "huerto_id"));
CREATE INDEX "datos_asignacionmantenimiento_huerto_id_bac530fd" ON "datos_asignacionmantenimiento" ("huerto_id");
CREATE INDEX "datos_asignacionmantenimiento_usuario_id_db5be448" ON "datos_asignacionmantenimiento" ("usuario_id");

-- Correcciones y anulaciones de un mantenimiento: filas nuevas numeradas 1, 2, 3…; el original no se toca.
CREATE TABLE "datos_revisionmantenimiento" (
 "id" uuid NOT NULL PRIMARY KEY,
 "numero" integer NOT NULL CHECK ("numero" >= 0),
 "tipo" varchar(12) NOT NULL,
 "tipo_corregido" varchar(16) NULL,
 "motivo" text NOT NULL,
 "registrada_en" timestamp with time zone NOT NULL,
 "editor_id" bigint NOT NULL
  CONSTRAINT "datos_revisionmanten_editor_id_c7a82466_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "mantenimiento_id" uuid NOT NULL
  CONSTRAINT "datos_revisionmanten_mantenimiento_id_4b44acb9_fk_datos_man" REFERENCES "datos_mantenimiento" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "revision_mant_orden_unico" UNIQUE ("mantenimiento_id", "numero"),
 CONSTRAINT "revision_mant_numero_valido" CHECK ("numero" >= 1),
 CONSTRAINT "revision_mant_motivo_significativo" CHECK ("motivo"::text ~  E'\\S'),
 CONSTRAINT "revision_mant_motivo_limite" CHECK (LENGTH("motivo") <= 500),
 CONSTRAINT "revision_mant_tipo_coherente" CHECK ((("tipo" = 'correccion' AND "tipo_corregido" IN ('refill', 'substrate', 'germination', 'harvest', 'inspection') AND "tipo_corregido" IS NOT NULL) OR ("tipo" = 'anulacion' AND "tipo_corregido" IS NULL))));
CREATE UNIQUE INDEX "revision_mant_una_anulacion" ON "datos_revisionmantenimiento" ("mantenimiento_id") WHERE "tipo" = 'anulacion';
CREATE INDEX "datos_revisionmantenimiento_editor_id_c7a82466" ON "datos_revisionmantenimiento" ("editor_id");
CREATE INDEX "datos_revisionmantenimiento_mantenimiento_id_4b44acb9" ON "datos_revisionmantenimiento" ("mantenimiento_id");

-- Casos de soporte que abre la persona usuaria desde «Soporte técnico».
CREATE TABLE "datos_casosoporte" (
 "id" uuid NOT NULL PRIMARY KEY,
 "incidente" varchar(16) NOT NULL,
 "creado_en" timestamp with time zone NOT NULL,
 "huerto_id" bigint NOT NULL
  CONSTRAINT "datos_casosoporte_huerto_id_a4225f5a_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 "solicitante_id" bigint NOT NULL
  CONSTRAINT "datos_casosoporte_solicitante_id_a98a04ec_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "dispositivo_id" bigint NOT NULL
  CONSTRAINT "datos_casosoporte_dispositivo_id_70c6c5a4_fk_datos_dis" REFERENCES "datos_dispositivo" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "soporte_incidente_valido" CHECK ("incidente" IN ('pump', 'humidity', 'lamp', 'connection', 'other')));
CREATE INDEX "caso_solicitante_fecha_idx" ON "datos_casosoporte" ("solicitante_id", "creado_en" DESC);
CREATE INDEX "datos_casosoporte_huerto_id_a4225f5a" ON "datos_casosoporte" ("huerto_id");
CREATE INDEX "datos_casosoporte_solicitante_id_a98a04ec" ON "datos_casosoporte" ("solicitante_id");
CREATE INDEX "datos_casosoporte_dispositivo_id_70c6c5a4" ON "datos_casosoporte" ("dispositivo_id");

-- Autorización de soporte (máximo 24 h). Del token solo se guarda su verificador HMAC-SHA256.
CREATE TABLE "datos_permisosoporte" (
 "id" uuid NOT NULL PRIMARY KEY,
 "consentimiento" boolean NOT NULL,
 "verificador" varchar(64) NOT NULL UNIQUE,
 "alcance" varchar(24) NOT NULL,
 "emitido_en" timestamp with time zone NOT NULL,
 "vence_en" timestamp with time zone NOT NULL,
 "revocado_en" timestamp with time zone NULL,
 "caso_id" uuid NOT NULL
  CONSTRAINT "datos_permisosoporte_caso_id_75c4d803_fk_datos_casosoporte_id" REFERENCES "datos_casosoporte" ("id") DEFERRABLE INITIALLY DEFERRED,
 "otorgante_id" bigint NOT NULL
  CONSTRAINT "datos_permisosoporte_otorgante_id_b72af916_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "permiso_verificador_sha256" CHECK ("verificador"::text ~ '^[0-9a-f]{64}$'),
 CONSTRAINT "permiso_alcance_limitado" CHECK ("alcance" = 'diagnostico_incidente'),
 CONSTRAINT "permiso_ventana_24h" CHECK (("vence_en" > ("emitido_en") AND "vence_en" <= ("emitido_en" + '1 day 0:00:00'::interval))),
 CONSTRAINT "permiso_revocacion_coherente" CHECK (("revocado_en" IS NULL OR "revocado_en" >= ("emitido_en"))),
 CONSTRAINT "permiso_consentimiento_explicito" CHECK ("consentimiento"));
CREATE INDEX "permiso_caso_vence_idx" ON "datos_permisosoporte" ("caso_id", "vence_en");
CREATE INDEX "datos_permisosoporte_verificador_486a16ab_like" ON "datos_permisosoporte" ("verificador" varchar_pattern_ops);
CREATE INDEX "datos_permisosoporte_caso_id_75c4d803" ON "datos_permisosoporte" ("caso_id");
CREATE INDEX "datos_permisosoporte_otorgante_id_b72af916" ON "datos_permisosoporte" ("otorgante_id");

-- Sesión técnica que abre la administradora con el token. Una abierta por administradora; solo se cierra.
CREATE TABLE "datos_sesiontecnica" (
 "id" uuid NOT NULL PRIMARY KEY,
 "iniciada_en" timestamp with time zone NOT NULL,
 "cerrada_en" timestamp with time zone NULL,
 "motivo_cierre" varchar(24) NOT NULL,
 "administrador_id" bigint NOT NULL
  CONSTRAINT "datos_sesiontecnica_administrador_id_d4d5ce0f_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "permiso_id" uuid NOT NULL
  CONSTRAINT "datos_sesiontecnica_permiso_id_fa478ed3_fk_datos_per" REFERENCES "datos_permisosoporte" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "sesion_tecnica_cierre_valido" CHECK ((("cerrada_en" IS NULL AND "motivo_cierre" = '') OR ("cerrada_en" >= ("iniciada_en") AND "cerrada_en" IS NOT NULL AND "motivo_cierre" IN ('explicit', 'revoked', 'replaced', 'logout', 'expiry', 'resolved')))));
CREATE UNIQUE INDEX "tecnica_admin_una_abierta" ON "datos_sesiontecnica" ("administrador_id") WHERE "cerrada_en" IS NULL;
CREATE INDEX "tecnica_admin_cierre_idx" ON "datos_sesiontecnica" ("administrador_id", "cerrada_en");
CREATE INDEX "datos_sesiontecnica_administrador_id_d4d5ce0f" ON "datos_sesiontecnica" ("administrador_id");
CREATE INDEX "datos_sesiontecnica_permiso_id_fa478ed3" ON "datos_sesiontecnica" ("permiso_id");

-- Cierre de un caso de soporte por la administradora. Una por caso; no cambia.
CREATE TABLE "datos_resolucionsoporte" (
 "id" uuid NOT NULL PRIMARY KEY,
 "resultado" varchar(20) NOT NULL,
 "nota" text NOT NULL,
 "resuelto_en" timestamp with time zone NOT NULL,
 "caso_id" uuid NOT NULL UNIQUE
  CONSTRAINT "datos_resolucionsopo_caso_id_6cdd272a_fk_datos_cas" REFERENCES "datos_casosoporte" ("id") DEFERRABLE INITIALLY DEFERRED,
 "responsable_id" bigint NOT NULL
  CONSTRAINT "datos_resolucionsopo_responsable_id_8de17b6d_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "resolucion_resultado_valido" CHECK ("resultado" IN ('solucionado', 'sin_falla', 'sin_respuesta', 'otro')),
 CONSTRAINT "resolucion_otro_con_nota" CHECK ((NOT ("resultado" = 'otro') OR "nota"::text ~  E'\\S')),
 CONSTRAINT "resolucion_nota_limite" CHECK (LENGTH("nota") <= 500));
CREATE INDEX "datos_resolucionsoporte_responsable_id_8de17b6d" ON "datos_resolucionsoporte" ("responsable_id");

-- Registro administrativo de versiones (pesos, matemáticas, reversión). Sin pantalla hoy; se conserva.
CREATE TABLE "datos_validacionversion" (
 "id" uuid NOT NULL PRIMARY KEY,
 "tipo" varchar(12) NOT NULL,
 "version" varchar(64) NOT NULL,
 "notas" text NOT NULL,
 "validada_en" timestamp with time zone NOT NULL,
 "actor_id" bigint NOT NULL
  CONSTRAINT "datos_validacionversion_actor_id_a4d4367c_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "version_tipo_valido" CHECK ("tipo" IN ('weights', 'math', 'rollback')),
 CONSTRAINT "version_formato_valido" CHECK ("version"::text ~ '^[a-zA-Z0-9][a-zA-Z0-9._-]{2,63}$'),
 CONSTRAINT "version_notas_limite" CHECK (LENGTH("notas") <= 2000));
CREATE INDEX "datos_validacionversion_actor_id_a4d4367c" ON "datos_validacionversion" ("actor_id");

-- Notas de conocimiento administrativo. Sin pantalla hoy; se conserva.
CREATE TABLE "datos_revisionconocimiento" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "contenido" text NOT NULL,
 "creada_en" timestamp with time zone NOT NULL,
 "autor_id" bigint NOT NULL
  CONSTRAINT "datos_revisionconoci_autor_id_3eeed166_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "conocimiento_significativo" CHECK ("contenido"::text ~  E'\\S'),
 CONSTRAINT "conocimiento_longitud" CHECK ((LENGTH("contenido") >= 20 AND LENGTH("contenido") <= 10000)));
CREATE INDEX "datos_revisionconocimiento_autor_id_3eeed166" ON "datos_revisionconocimiento" ("autor_id");

-- Solicitudes (riego puntual, apagar lámpara, modo automático…). Se GUARDAN, no se ejecutan: estado siempre 'pending'.
CREATE TABLE "datos_solicitud" (
 "id" uuid NOT NULL PRIMARY KEY,
 "tipo" varchar(20) NOT NULL,
 "creada_en" timestamp with time zone NOT NULL,
 "estado" varchar(16) NOT NULL,
 "actor_id" bigint NOT NULL
  CONSTRAINT "datos_solicitud_actor_id_d55a761a_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "dispositivo_id" bigint NULL
  CONSTRAINT "datos_solicitud_dispositivo_id_1607985b_fk_datos_dispositivo_id" REFERENCES "datos_dispositivo" ("id") DEFERRABLE INITIALLY DEFERRED,
 "huerto_id" bigint NULL
  CONSTRAINT "datos_solicitud_huerto_id_2c03652c_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 "sesion_tecnica_id" uuid NULL
  CONSTRAINT "datos_solicitud_sesion_tecnica_id_b4ab2ccc_fk_datos_ses" REFERENCES "datos_sesiontecnica" ("id") DEFERRABLE INITIALLY DEFERRED,
 "validacion_id" uuid NULL UNIQUE
  CONSTRAINT "datos_solicitud_validacion_id_0be37b51_fk_datos_val" REFERENCES "datos_validacionversion" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "solicitud_sin_actuacion" CHECK ("estado" = 'pending'),
 CONSTRAINT "solicitud_tipo_valido" CHECK ("tipo" IN ('water', 'lamp-off', 'lamp-auto', 'weights', 'math', 'rollback', 'restart-node', 'restart-platform')),
 CONSTRAINT "solicitud_referencias_por_tipo" CHECK ((("dispositivo_id" IS NOT NULL AND "huerto_id" IS NOT NULL AND "sesion_tecnica_id" IS NULL AND "tipo" IN ('water', 'lamp-off', 'lamp-auto') AND "validacion_id" IS NULL) OR ("dispositivo_id" IS NOT NULL AND "huerto_id" IS NOT NULL AND "sesion_tecnica_id" IS NOT NULL AND "tipo" = 'restart-node' AND "validacion_id" IS NULL) OR ("dispositivo_id" IS NULL AND "huerto_id" IS NULL AND "sesion_tecnica_id" IS NULL AND "tipo" IN ('weights', 'math', 'rollback') AND "validacion_id" IS NOT NULL) OR ("dispositivo_id" IS NULL AND "huerto_id" IS NULL AND "sesion_tecnica_id" IS NULL AND "tipo" = 'restart-platform' AND "validacion_id" IS NULL))));
CREATE INDEX "solicitud_huerto_fecha_idx" ON "datos_solicitud" ("huerto_id", "creada_en" DESC);
CREATE INDEX "datos_solicitud_actor_id_d55a761a" ON "datos_solicitud" ("actor_id");
CREATE INDEX "datos_solicitud_dispositivo_id_1607985b" ON "datos_solicitud" ("dispositivo_id");
CREATE INDEX "datos_solicitud_huerto_id_2c03652c" ON "datos_solicitud" ("huerto_id");
CREATE INDEX "datos_solicitud_sesion_tecnica_id_b4ab2ccc" ON "datos_solicitud" ("sesion_tecnica_id");

-- Códigos de vinculación (26 caracteres, 10 minutos, 5 intentos). Del código solo se guarda su resumen.
CREATE TABLE "datos_codigovinculacion" (
 "id" uuid NOT NULL PRIMARY KEY,
 "entrega" varchar(10) NOT NULL,
 "verificador" varchar(128) NOT NULL,
 "emitido_en" timestamp with time zone NOT NULL,
 "vence_en" timestamp with time zone NOT NULL,
 "intentos" smallint NOT NULL CHECK ("intentos" >= 0),
 "estado" varchar(12) NOT NULL,
 "envio" varchar(14) NOT NULL,
 "cerrado_en" timestamp with time zone NULL,
 "destinatario_id" bigint NOT NULL
  CONSTRAINT "datos_codigovinculac_destinatario_id_5f528941_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "emitido_por_id" bigint NOT NULL
  CONSTRAINT "datos_codigovinculac_emitido_por_id_7f90f681_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "huerto_id" bigint NOT NULL
  CONSTRAINT "datos_codigovinculacion_huerto_id_605a0bdb_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 "membresia_id" bigint NULL UNIQUE
  CONSTRAINT "datos_codigovinculac_membresia_id_7329f237_fk_huerto_me" REFERENCES "huerto_membresia" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "vinculacion_entrega_valida" CHECK ("entrega" IN ('presencial', 'correo')),
 CONSTRAINT "vinculacion_estado_valido" CHECK ("estado" IN ('pendiente', 'consumido', 'revocado', 'reemplazado', 'bloqueado')),
 CONSTRAINT "vinculacion_envio_coherente" CHECK ((("entrega" = 'presencial' AND "envio" = 'no_aplica') OR ("entrega" = 'correo' AND "envio" IN ('pendiente', 'aceptado_smtp', 'rechazado', 'incierto')))),
 CONSTRAINT "vinculacion_verificador_resumido" CHECK ("verificador"::text ~  E'^[a-z0-9_]+\\$[^$]+\\$'),
 CONSTRAINT "vinculacion_vigencia_maxima" CHECK (("vence_en" > ("emitido_en") AND "vence_en" <= ("emitido_en" + '0:10:00'::interval))),
 CONSTRAINT "vinculacion_intentos_limite" CHECK ("intentos" <= 5),
 CONSTRAINT "vinculacion_cierre_coherente" CHECK ((("cerrado_en" IS NULL AND "estado" = 'pendiente' AND "membresia_id" IS NULL) OR ("cerrado_en" IS NOT NULL AND "estado" = 'consumido' AND "membresia_id" IS NOT NULL) OR ("cerrado_en" IS NOT NULL AND "estado" IN ('revocado', 'reemplazado', 'bloqueado') AND "membresia_id" IS NULL))));
CREATE UNIQUE INDEX "vinculacion_pendiente_por_huerto" ON "datos_codigovinculacion" ("huerto_id") WHERE "estado" = 'pendiente';
CREATE UNIQUE INDEX "vinculacion_pendiente_por_cuenta" ON "datos_codigovinculacion" ("destinatario_id") WHERE "estado" = 'pendiente';
CREATE INDEX "vinculacion_estado_fecha_idx" ON "datos_codigovinculacion" ("estado", "emitido_en" DESC);
CREATE INDEX "vinculacion_entrega_idx" ON "datos_codigovinculacion" ("huerto_id", "destinatario_id", "entrega");
CREATE INDEX "datos_codigovinculacion_destinatario_id_5f528941" ON "datos_codigovinculacion" ("destinatario_id");
CREATE INDEX "datos_codigovinculacion_emitido_por_id_7f90f681" ON "datos_codigovinculacion" ("emitido_por_id");
CREATE INDEX "datos_codigovinculacion_huerto_id_605a0bdb" ON "datos_codigovinculacion" ("huerto_id");

-- Guías de cuidado (preguntas frecuentes). Se retiran, no se borran. Cada cambio sube «version».
CREATE TABLE "datos_guiacuidado" (
 "id" uuid NOT NULL PRIMARY KEY,
 "clave" varchar(64) NOT NULL UNIQUE,
 "pregunta" varchar(200) NOT NULL,
 "respuesta" text NOT NULL,
 "orden" integer NOT NULL CHECK ("orden" >= 0),
 "estado" varchar(10) NOT NULL,
 "fuente_nombre" varchar(120) NOT NULL,
 "fuente_url" varchar(500) NOT NULL,
 "version" integer NOT NULL CHECK ("version" >= 0),
 "creado_en" timestamp with time zone NOT NULL,
 "actualizado_en" timestamp with time zone NOT NULL,
 "actualizado_por_id" bigint NULL
  CONSTRAINT "datos_guiacuidado_actualizado_por_id_2e6317a5_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "creado_por_id" bigint NULL
  CONSTRAINT "datos_guiacuidado_creado_por_id_2337ac27_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "guia_pregunta_significativa" CHECK ("pregunta"::text ~  E'\\S'),
 CONSTRAINT "guia_respuesta_significativa" CHECK ("respuesta"::text ~  E'\\S'),
 CONSTRAINT "guia_respuesta_limite" CHECK (LENGTH("respuesta") <= 4000),
 CONSTRAINT "guia_clave_valida" CHECK ("clave"::text ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
 CONSTRAINT "guia_orden_valido" CHECK (("orden" >= 1 AND "orden" <= 9999)),
 CONSTRAINT "guia_estado_valido" CHECK ("estado" IN ('borrador', 'publicada', 'retirada')),
 CONSTRAINT "guia_version_valida" CHECK ("version" >= 1),
 CONSTRAINT "guia_fuente_valida" CHECK (("fuente_url" = '' OR ("fuente_url"::text ~ '^https?://[^[:space:]]+$' AND NOT ("fuente_nombre" = '')))));
CREATE INDEX "guia_estado_orden_idx" ON "datos_guiacuidado" ("estado", "orden");
CREATE INDEX "datos_guiacuidado_clave_d54710c6_like" ON "datos_guiacuidado" ("clave" varchar_pattern_ops);
CREATE INDEX "datos_guiacuidado_actualizado_por_id_2e6317a5" ON "datos_guiacuidado" ("actualizado_por_id");
CREATE INDEX "datos_guiacuidado_creado_por_id_2337ac27" ON "datos_guiacuidado" ("creado_por_id");

-- Mensajes del formulario público «Consíguelo» (buzón «Solicitudes del producto»).
-- estado: nueva → atendida | archivada; atendida ↔ archivada. Nunca vuelve a «nueva» ni se borra.
CREATE TABLE "datos_consultaproducto" (
 "id" uuid NOT NULL PRIMARY KEY,
 "recibida_en" timestamp with time zone NOT NULL,
 "nombre" varchar(100) NOT NULL,
 "correo" varchar(254) NOT NULL,
 "mensaje" text NOT NULL,
 "huella" varchar(64) NOT NULL,
 "estado" varchar(10) NOT NULL,
 "atendida_en" timestamp with time zone NULL,
 "atendida_por_id" bigint NULL
  CONSTRAINT "datos_consultaproduc_atendida_por_id_b419d152_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "consulta_correo_significativo" CHECK ("correo"::text ~  E'\\S'),
 CONSTRAINT "consulta_mensaje_significativo" CHECK ("mensaje"::text ~  E'\\S'),
 CONSTRAINT "consulta_mensaje_limite" CHECK (LENGTH("mensaje") <= 2000),
 CONSTRAINT "consulta_huella_valida" CHECK ("huella"::text ~ '^[0-9a-f]{64}$'),
 CONSTRAINT "consulta_estado_valido" CHECK ("estado" IN ('nueva', 'atendida', 'archivada')),
 CONSTRAINT "consulta_atencion_coherente" CHECK ((("atendida_en" IS NULL AND "atendida_por_id" IS NULL AND "estado" = 'nueva') OR ("atendida_en" IS NOT NULL AND "atendida_por_id" IS NOT NULL AND "estado" IN ('atendida', 'archivada')))));
CREATE INDEX "consulta_estado_fecha_idx" ON "datos_consultaproducto" ("estado", "recibida_en" DESC);
CREATE INDEX "consulta_huella_idx" ON "datos_consultaproducto" ("huella", "recibida_en" DESC);
CREATE INDEX "datos_consultaproducto_atendida_por_id_b419d152" ON "datos_consultaproducto" ("atendida_por_id");

-- Cola de avisos automáticos por correo (caso nuevo, token solicitado, consulta nueva). Hasta 5 intentos.
CREATE TABLE "datos_avisocorreo" (
 "id" uuid NOT NULL PRIMARY KEY,
 "tipo" varchar(20) NOT NULL,
 "creado_en" timestamp with time zone NOT NULL,
 "estado" varchar(16) NOT NULL,
 "intentos" smallint NOT NULL CHECK ("intentos" >= 0),
 "ultimo_intento_en" timestamp with time zone NULL,
 "aceptado_en" timestamp with time zone NULL,
 "caso_id" uuid NULL
  CONSTRAINT "datos_avisocorreo_caso_id_fe2e6603_fk_datos_casosoporte_id" REFERENCES "datos_casosoporte" ("id") DEFERRABLE INITIALLY DEFERRED,
 "consulta_id" uuid NULL
  CONSTRAINT "datos_avisocorreo_consulta_id_56fccf8f_fk_datos_con" REFERENCES "datos_consultaproducto" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "aviso_correo_tipo_valido" CHECK ("tipo" IN ('caso_nuevo', 'token_solicitado', 'consulta_nueva')),
 CONSTRAINT "aviso_correo_referencia_coherente" CHECK ((("caso_id" IS NOT NULL AND "consulta_id" IS NULL AND "tipo" IN ('caso_nuevo', 'token_solicitado')) OR ("caso_id" IS NULL AND "consulta_id" IS NOT NULL AND "tipo" = 'consulta_nueva'))),
 CONSTRAINT "aviso_correo_estado_valido" CHECK ("estado" IN ('pendiente', 'aceptado_smtp', 'fallido')),
 CONSTRAINT "aviso_correo_intentos_limite" CHECK ("intentos" <= 5),
 CONSTRAINT "aviso_correo_aceptacion_coherente" CHECK ((("aceptado_en" IS NOT NULL AND "estado" = 'aceptado_smtp') OR (NOT ("estado" = 'aceptado_smtp') AND "aceptado_en" IS NULL))));
CREATE UNIQUE INDEX "aviso_correo_caso_unico" ON "datos_avisocorreo" ("caso_id") WHERE "tipo" = 'caso_nuevo';
CREATE UNIQUE INDEX "aviso_correo_consulta_unico" ON "datos_avisocorreo" ("consulta_id") WHERE "tipo" = 'consulta_nueva';
CREATE INDEX "aviso_correo_pendientes_idx" ON "datos_avisocorreo" ("estado", "creado_en");
CREATE INDEX "datos_avisocorreo_caso_id_fe2e6603" ON "datos_avisocorreo" ("caso_id");
CREATE INDEX "datos_avisocorreo_consulta_id_56fccf8f" ON "datos_avisocorreo" ("consulta_id");

-- Auditoría: quién hizo qué y sobre qué registro. Sin texto libre, correos, tokens ni secretos. No cambia.
CREATE TABLE "datos_auditoria" (
 "id" uuid NOT NULL PRIMARY KEY,
 "accion" varchar(32) NOT NULL,
 "resultado" varchar(16) NOT NULL,
 "creada_en" timestamp with time zone NOT NULL,
 "actor_id" bigint NOT NULL
  CONSTRAINT "datos_auditoria_actor_id_c36e3472_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "huerto_id" bigint NULL
  CONSTRAINT "datos_auditoria_huerto_id_f65d310e_fk_huerto_huerto_id" REFERENCES "huerto_huerto" ("id") DEFERRABLE INITIALLY DEFERRED,
 "caso_id" uuid NULL
  CONSTRAINT "datos_auditoria_caso_id_1230ac45_fk_datos_casosoporte_id" REFERENCES "datos_casosoporte" ("id") DEFERRABLE INITIALLY DEFERRED,
 "mantenimiento_id" uuid NULL
  CONSTRAINT "datos_auditoria_mantenimiento_id_1a8db11e_fk_datos_man" REFERENCES "datos_mantenimiento" ("id") DEFERRABLE INITIALLY DEFERRED,
 "permiso_id" uuid NULL
  CONSTRAINT "datos_auditoria_permiso_id_971e8bf2_fk_datos_permisosoporte_id" REFERENCES "datos_permisosoporte" ("id") DEFERRABLE INITIALLY DEFERRED,
 "conocimiento_id" bigint NULL
  CONSTRAINT "datos_auditoria_conocimiento_id_eac685d6_fk_datos_rev" REFERENCES "datos_revisionconocimiento" ("id") DEFERRABLE INITIALLY DEFERRED,
 "sesion_tecnica_id" uuid NULL
  CONSTRAINT "datos_auditoria_sesion_tecnica_id_37f600f0_fk_datos_ses" REFERENCES "datos_sesiontecnica" ("id") DEFERRABLE INITIALLY DEFERRED,
 "solicitud_id" uuid NULL
  CONSTRAINT "datos_auditoria_solicitud_id_fb9082bc_fk_datos_solicitud_id" REFERENCES "datos_solicitud" ("id") DEFERRABLE INITIALLY DEFERRED,
 "validacion_id" uuid NULL
  CONSTRAINT "datos_auditoria_validacion_id_e1a8c181_fk_datos_val" REFERENCES "datos_validacionversion" ("id") DEFERRABLE INITIALLY DEFERRED,
 "revision_mantenimiento_id" uuid NULL
  CONSTRAINT "datos_auditoria_revision_mantenimien_c03015ee_fk_datos_rev" REFERENCES "datos_revisionmantenimiento" ("id") DEFERRABLE INITIALLY DEFERRED,
 "vinculacion_id" uuid NULL
  CONSTRAINT "datos_auditoria_vinculacion_id_40037548_fk_datos_cod" REFERENCES "datos_codigovinculacion" ("id") DEFERRABLE INITIALLY DEFERRED,
 "guia_id" uuid NULL
  CONSTRAINT "datos_auditoria_guia_id_06c2da4a_fk_datos_guiacuidado_id" REFERENCES "datos_guiacuidado" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "auditoria_resultado_valido" CHECK ("resultado" IN ('recorded', 'pending')),
 CONSTRAINT "auditoria_accion_valida" CHECK ("accion" IN ('maintenance', 'support-granted', 'support-revoked', 'token-requested', 'technical-opened', 'technical-closed', 'diagnostic-requested', 'request-recorded', 'version-validated', 'knowledge-saved', 'maintenance-corrected', 'maintenance-voided', 'case-resolved', 'mfa-reset', 'binding-issued', 'binding-revoked', 'binding-replaced', 'binding-consumed', 'binding-rejected', 'binding-locked', 'binding-limited', 'guide-created', 'guide-updated', 'guide-published', 'guide-withdrawn')),
 CONSTRAINT "auditoria_revision_coherente" CHECK ((("accion" IN ('maintenance-corrected', 'maintenance-voided') AND "mantenimiento_id" IS NULL AND "revision_mantenimiento_id" IS NOT NULL) OR (NOT ("accion" IN ('maintenance-corrected', 'maintenance-voided')) AND "revision_mantenimiento_id" IS NULL))),
 CONSTRAINT "auditoria_guia_coherente" CHECK ((("accion"::text LIKE 'guide-%' AND "guia_id" IS NOT NULL) OR (NOT ("accion"::text LIKE 'guide-%') AND "guia_id" IS NULL))));
CREATE INDEX "auditoria_actor_fecha_idx" ON "datos_auditoria" ("actor_id", "creada_en" DESC);
CREATE INDEX "datos_auditoria_actor_id_c36e3472" ON "datos_auditoria" ("actor_id");
CREATE INDEX "datos_auditoria_huerto_id_f65d310e" ON "datos_auditoria" ("huerto_id");
CREATE INDEX "datos_auditoria_caso_id_1230ac45" ON "datos_auditoria" ("caso_id");
CREATE INDEX "datos_auditoria_mantenimiento_id_1a8db11e" ON "datos_auditoria" ("mantenimiento_id");
CREATE INDEX "datos_auditoria_permiso_id_971e8bf2" ON "datos_auditoria" ("permiso_id");
CREATE INDEX "datos_auditoria_conocimiento_id_eac685d6" ON "datos_auditoria" ("conocimiento_id");
CREATE INDEX "datos_auditoria_sesion_tecnica_id_37f600f0" ON "datos_auditoria" ("sesion_tecnica_id");
CREATE INDEX "datos_auditoria_solicitud_id_fb9082bc" ON "datos_auditoria" ("solicitud_id");
CREATE INDEX "datos_auditoria_validacion_id_e1a8c181" ON "datos_auditoria" ("validacion_id");
CREATE INDEX "datos_auditoria_revision_mantenimiento_id_c03015ee" ON "datos_auditoria" ("revision_mantenimiento_id");
CREATE INDEX "datos_auditoria_vinculacion_id_40037548" ON "datos_auditoria" ("vinculacion_id");
CREATE INDEX "datos_auditoria_guia_id_06c2da4a" ON "datos_auditoria" ("guia_id");


-- =====================================================================================================
-- 6. PRIVACIDAD
-- =====================================================================================================

-- Versiones registradas de los textos legales, con la huella SHA-256 del archivo publicado.
CREATE TABLE "privacidad_documentoversion" (
 "id" uuid NOT NULL PRIMARY KEY,
 "tipo" varchar(16) NOT NULL,
 "version" varchar(64) NOT NULL,
 "contenido_ref" varchar(255) NOT NULL,
 "contenido_sha256" varchar(64) NOT NULL,
 "registrado_en" timestamp with time zone DEFAULT (STATEMENT_TIMESTAMP()) NOT NULL,
 CONSTRAINT "priv_documento_version_unica" UNIQUE ("tipo", "version"),
 CONSTRAINT "priv_documento_version_texto" CHECK ("version"::text ~  E'\\S'),
 CONSTRAINT "priv_documento_ref_texto" CHECK ("contenido_ref"::text ~  E'\\S'),
 CONSTRAINT "priv_documento_hash_valido" CHECK ("contenido_sha256"::text ~ '^[0-9a-f]{64}$'),
 CONSTRAINT "priv_documento_tipo_valido" CHECK ("tipo" IN ('aviso_privacidad', 'terminos', 'politica_cookies')));

-- Finalidades opcionales. Hoy solo una: estadísticas internas de navegación.
CREATE TABLE "privacidad_finalidadopcional" (
 "id" uuid NOT NULL PRIMARY KEY,
 "codigo" varchar(64) NOT NULL UNIQUE,
 "descripcion" varchar(255) NOT NULL,
 "creada_en" timestamp with time zone DEFAULT (STATEMENT_TIMESTAMP()) NOT NULL,
 CONSTRAINT "priv_finalidad_codigo_valido" CHECK ("codigo"::text ~ '^[a-z][a-z0-9_]{0,63}$'),
 CONSTRAINT "priv_finalidad_descripcion_texto" CHECK ("descripcion"::text ~  E'\\S'));
CREATE INDEX "privacidad_finalidadopcional_codigo_6639581a_like" ON "privacidad_finalidadopcional" ("codigo" varchar_pattern_ops);

-- «Sujeto» de privacidad: identificador seudónimo. ambito = 'cuenta' (una por cuenta) o 'navegador'
-- (uno por navegador que decidió sobre cookies; puede quedar ligado a una cuenta si decidió con sesión).
CREATE TABLE "privacidad_sujetoprivacidad" (
 "id" uuid NOT NULL PRIMARY KEY,
 "creado_en" timestamp with time zone DEFAULT (STATEMENT_TIMESTAMP()) NOT NULL,
 "usuario_id" bigint NULL
  CONSTRAINT "privacidad_sujetopri_usuario_id_19c8f107_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "ambito" varchar(9) NOT NULL,
 CONSTRAINT "priv_sujeto_ambito_valido" CHECK ("ambito" IN ('cuenta', 'navegador')));
CREATE UNIQUE INDEX "priv_sujeto_cuenta_unica" ON "privacidad_sujetoprivacidad" ("usuario_id") WHERE "ambito" = 'cuenta';
CREATE INDEX "privacidad_sujetoprivacidad_usuario_id_19c8f107" ON "privacidad_sujetoprivacidad" ("usuario_id");

-- Historial de decisiones: aceptar términos, leer el aviso, consentimiento y decisión de cookies. No cambia.
CREATE TABLE "privacidad_decisionprivacidad" (
 "id" uuid NOT NULL PRIMARY KEY,
 "acto" varchar(20) NOT NULL,
 "decision" boolean NOT NULL,
 "registrada_en" timestamp with time zone DEFAULT (STATEMENT_TIMESTAMP()) NOT NULL,
 "documento_id" uuid NOT NULL
  CONSTRAINT "privacidad_decisionp_documento_id_6e91616c_fk_privacida" REFERENCES "privacidad_documentoversion" ("id") DEFERRABLE INITIALLY DEFERRED,
 "finalidad_id" uuid NULL
  CONSTRAINT "privacidad_decisionp_finalidad_id_d508a7cc_fk_privacida" REFERENCES "privacidad_finalidadopcional" ("id") DEFERRABLE INITIALLY DEFERRED,
 "sujeto_id" uuid NOT NULL
  CONSTRAINT "privacidad_decisionp_sujeto_id_c3393b43_fk_privacida" REFERENCES "privacidad_sujetoprivacidad" ("id") DEFERRABLE INITIALLY DEFERRED,
 "politica_cookies_id" uuid NULL
  CONSTRAINT "privacidad_decisionp_politica_cookies_id_2c4fda84_fk_privacida" REFERENCES "privacidad_documentoversion" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "priv_decision_acto_finalidad" CHECK ((("acto" = 'consentimiento' AND "finalidad_id" IS NOT NULL AND "politica_cookies_id" IS NULL) OR ("acto" = 'cookies' AND "finalidad_id" IS NOT NULL AND "politica_cookies_id" IS NOT NULL) OR ("acto" IN ('lectura_aviso', 'aceptacion_terminos') AND "finalidad_id" IS NULL AND "politica_cookies_id" IS NULL))));
CREATE INDEX "priv_decision_historial_idx" ON "privacidad_decisionprivacidad" ("sujeto_id", "finalidad_id", "registrada_en" DESC);
CREATE INDEX "privacidad_decisionprivacidad_documento_id_6e91616c" ON "privacidad_decisionprivacidad" ("documento_id");
CREATE INDEX "privacidad_decisionprivacidad_finalidad_id_d508a7cc" ON "privacidad_decisionprivacidad" ("finalidad_id");
CREATE INDEX "privacidad_decisionprivacidad_sujeto_id_c3393b43" ON "privacidad_decisionprivacidad" ("sujeto_id");
CREATE INDEX "privacidad_decisionprivacidad_politica_cookies_id_2c4fda84" ON "privacidad_decisionprivacidad" ("politica_cookies_id");

-- Decisión VIGENTE de cada sujeto para cada finalidad (apunta a la última fila del historial).
CREATE TABLE "privacidad_preferenciafinalidad" (
 "id" uuid NOT NULL PRIMARY KEY,
 "actualizada_en" timestamp with time zone DEFAULT (STATEMENT_TIMESTAMP()) NOT NULL,
 "decision_id" uuid NOT NULL
  CONSTRAINT "privacidad_preferenc_decision_id_c1b08a89_fk_privacida" REFERENCES "privacidad_decisionprivacidad" ("id") DEFERRABLE INITIALLY DEFERRED,
 "finalidad_id" uuid NOT NULL
  CONSTRAINT "privacidad_preferenc_finalidad_id_038298fb_fk_privacida" REFERENCES "privacidad_finalidadopcional" ("id") DEFERRABLE INITIALLY DEFERRED,
 "sujeto_id" uuid NOT NULL
  CONSTRAINT "privacidad_preferenc_sujeto_id_511ff4ff_fk_privacida" REFERENCES "privacidad_sujetoprivacidad" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "priv_preferencia_unica" UNIQUE ("sujeto_id", "finalidad_id"));
CREATE INDEX "privacidad_preferenciafinalidad_decision_id_c1b08a89" ON "privacidad_preferenciafinalidad" ("decision_id");
CREATE INDEX "privacidad_preferenciafinalidad_finalidad_id_038298fb" ON "privacidad_preferenciafinalidad" ("finalidad_id");
CREATE INDEX "privacidad_preferenciafinalidad_sujeto_id_511ff4ff" ON "privacidad_preferenciafinalidad" ("sujeto_id");

-- Eventos: decisión, oposición, acceso a «Mis datos» y rectificación (solo el nombre del campo, nunca el valor).
CREATE TABLE "privacidad_eventoprivacidad" (
 "id" uuid NOT NULL PRIMARY KEY,
 "accion" varchar(16) NOT NULL,
 "resultado" varchar(12) NOT NULL,
 "campo" varchar(10) NOT NULL,
 "creado_en" timestamp with time zone DEFAULT (STATEMENT_TIMESTAMP()) NOT NULL,
 "actor_id" bigint NULL
  CONSTRAINT "privacidad_eventopri_actor_id_1e3d9c7e_fk_cuentas_u" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 "decision_id" uuid NULL
  CONSTRAINT "privacidad_eventopri_decision_id_2205b32c_fk_privacida" REFERENCES "privacidad_decisionprivacidad" ("id") DEFERRABLE INITIALLY DEFERRED,
 "finalidad_id" uuid NULL
  CONSTRAINT "privacidad_eventopri_finalidad_id_50b18f57_fk_privacida" REFERENCES "privacidad_finalidadopcional" ("id") DEFERRABLE INITIALLY DEFERRED,
 "sujeto_id" uuid NOT NULL
  CONSTRAINT "privacidad_eventopri_sujeto_id_506aeddb_fk_privacida" REFERENCES "privacidad_sujetoprivacidad" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "priv_evento_resultado_valido" CHECK ("resultado" IN ('completado', 'rechazado')),
 CONSTRAINT "priv_evento_referencias_validas" CHECK ((("accion" = 'rectificacion' AND "actor_id" IS NOT NULL AND "campo" IN ('first_name', 'last_name', 'alias') AND "decision_id" IS NULL AND "finalidad_id" IS NULL) OR ("accion" = 'acceso' AND "actor_id" IS NOT NULL AND "campo" = '' AND "decision_id" IS NULL AND "finalidad_id" IS NULL) OR ("accion" = 'decision' AND "campo" = '' AND "decision_id" IS NOT NULL) OR ("accion" = 'oposicion' AND "actor_id" IS NOT NULL AND "campo" = '' AND "decision_id" IS NOT NULL AND "finalidad_id" IS NOT NULL))));
CREATE INDEX "priv_evento_historial_idx" ON "privacidad_eventoprivacidad" ("sujeto_id", "creado_en" DESC);
CREATE INDEX "privacidad_eventoprivacidad_actor_id_1e3d9c7e" ON "privacidad_eventoprivacidad" ("actor_id");
CREATE INDEX "privacidad_eventoprivacidad_decision_id_2205b32c" ON "privacidad_eventoprivacidad" ("decision_id");
CREATE INDEX "privacidad_eventoprivacidad_finalidad_id_50b18f57" ON "privacidad_eventoprivacidad" ("finalidad_id");
CREATE INDEX "privacidad_eventoprivacidad_sujeto_id_506aeddb" ON "privacidad_eventoprivacidad" ("sujeto_id");

-- Visitas por día y sección. Solo totales, sin identidad. Solo cuenta si el navegador aceptó estadísticas.
CREATE TABLE "privacidad_conteonavegacion" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "dia" date NOT NULL,
 "seccion" varchar(16) NOT NULL,
 "visitas" bigint NOT NULL CHECK ("visitas" >= 0),
 CONSTRAINT "priv_conteo_dia_seccion_unico" UNIQUE ("dia", "seccion"),
 CONSTRAINT "priv_conteo_seccion_valida" CHECK ("seccion" IN ('inicio', 'proyecto', 'prototipo', 'funcionamiento', 'huerto', 'panel_tecnico', 'mantenimiento', 'soporte', 'avisos', 'cuenta', 'privacidad')));


-- =====================================================================================================
-- 7. RECIBOS DE IDEMPOTENCIA
--    Cada escritura del panel lleva una clave única (Idempotency-Key). Si el navegador reintenta,
--    se devuelve el mismo resultado en vez de repetir la operación. No guarda tokens ni contraseñas.
-- =====================================================================================================
CREATE TABLE "web_idempotencia" (
 "id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
 "clave" uuid NOT NULL,
 "ruta" varchar(240) NOT NULL,
 "huella" varchar(64) NOT NULL,
 "respuesta" jsonb NOT NULL,
 "creada_en" timestamp with time zone NOT NULL,
 "actor_id" bigint NOT NULL
  CONSTRAINT "web_idempotencia_actor_id_26d80f32_fk_cuentas_usuario_id" REFERENCES "cuentas_usuario" ("id") DEFERRABLE INITIALLY DEFERRED,
 CONSTRAINT "web_idempotencia_actor_clave" UNIQUE ("actor_id", "clave"));
CREATE INDEX "web_idempotencia_actor_id_26d80f32" ON "web_idempotencia" ("actor_id");


-- =====================================================================================================
-- 8. REGLAS EN LA BASE: FUNCIONES Y TRIGGERS
--    Segunda barrera: aunque la aplicación tuviera un error, la base rechaza el cambio (código 23514).
-- =====================================================================================================

-- 8.1 Historiales que nunca se modifican ni se borran -------------------------------------------------
CREATE FUNCTION public.chilito_historial_inmutable() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'Historial inmutable; no se permite alterar ni borrar' USING ERRCODE='23514';
END $$;
CREATE TRIGGER historial_dispositivo BEFORE UPDATE OR DELETE ON public.datos_dispositivo FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_mantenimiento BEFORE UPDATE OR DELETE ON public.datos_mantenimiento FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_revisionmantenimiento BEFORE UPDATE OR DELETE ON public.datos_revisionmantenimiento FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_casosoporte BEFORE UPDATE OR DELETE ON public.datos_casosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_resolucionsoporte BEFORE UPDATE OR DELETE ON public.datos_resolucionsoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_validacionversion BEFORE UPDATE OR DELETE ON public.datos_validacionversion FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_revisionconocimiento BEFORE UPDATE OR DELETE ON public.datos_revisionconocimiento FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_solicitud BEFORE UPDATE OR DELETE ON public.datos_solicitud FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();
CREATE TRIGGER historial_auditoria BEFORE UPDATE OR DELETE ON public.datos_auditoria FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();

-- 8.2 Cuentas -----------------------------------------------------------------------------------------
-- El rol de la aplicación no puede crear cuentas staff, superusuario ni inactivas.
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

-- Un método de segundo factor no cambia de dueño, de tipo ni de fecha de alta.
CREATE FUNCTION public.chilito_proteger_mfa() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.user_id IS DISTINCT FROM OLD.user_id
    OR NEW.type IS DISTINCT FROM OLD.type OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
  RAISE EXCEPTION 'La identidad de un autenticador no puede reasignarse' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_mfa_estable BEFORE UPDATE ON public.mfa_authenticator
 FOR EACH ROW EXECUTE FUNCTION public.chilito_proteger_mfa();

-- 8.3 Huertos -----------------------------------------------------------------------------------------
-- Zonas y membresías no cambian de huerto ni de dueño.
CREATE FUNCTION chilito_proteger_relacion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME='huerto_zona' THEN
    IF NEW.huerto_id IS DISTINCT FROM OLD.huerto_id OR NEW.numero IS DISTINCT FROM OLD.numero THEN
      RAISE EXCEPTION 'La identidad de zona no puede reasignarse' USING ERRCODE='23514';
    END IF;
  ELSIF TG_TABLE_NAME='huerto_membresia' THEN
    IF NEW.huerto_id IS DISTINCT FROM OLD.huerto_id OR NEW.usuario_id IS DISTINCT FROM OLD.usuario_id THEN
      RAISE EXCEPTION 'La identidad de membresia no puede reasignarse' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER chilito_zona_estable BEFORE UPDATE ON huerto_zona
FOR EACH ROW EXECUTE FUNCTION chilito_proteger_relacion();
CREATE TRIGGER chilito_membresia_estable BEFORE UPDATE ON huerto_membresia
FOR EACH ROW EXECUTE FUNCTION chilito_proteger_relacion();

-- Cada huerto nuevo nace con sus 3 zonas: «Planta 1», «Planta 2» y «Planta 3», de chile habanero.
CREATE FUNCTION public.chilito_crear_tres_zonas() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 INSERT INTO public.huerto_zona(huerto_id,numero,nombre,cultivo)
 SELECT NEW.id,n,'Planta '||n,'Chile habanero' FROM generate_series(1,3) n;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_crear_tres_zonas AFTER INSERT ON public.huerto_huerto
 FOR EACH ROW EXECUTE FUNCTION public.chilito_crear_tres_zonas();

-- Las zonas no se borran.
CREATE FUNCTION public.chilito_conservar_zona() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'Las tres zonas se conservan; no se permite borrarlas' USING ERRCODE='23514';
END $$;
CREATE TRIGGER chilito_conservar_zona BEFORE DELETE ON public.huerto_zona
 FOR EACH ROW EXECUTE FUNCTION public.chilito_conservar_zona();

-- Un aviso solo puede apuntar a una zona de su propio huerto y no se reasigna.
CREATE FUNCTION chilito_proteger_aviso() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.zona_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM huerto_zona WHERE id=NEW.zona_id AND huerto_id=NEW.huerto_id
  ) THEN
    RAISE EXCEPTION 'La zona no pertenece al huerto del aviso' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' AND (NEW.huerto_id IS DISTINCT FROM OLD.huerto_id OR NEW.zona_id IS DISTINCT FROM OLD.zona_id) THEN
    RAISE EXCEPTION 'No se puede reasignar un aviso' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER chilito_aviso_estable BEFORE INSERT OR UPDATE ON huerto_aviso
FOR EACH ROW EXECUTE FUNCTION chilito_proteger_aviso();

-- Una lectura de aviso no se reasigna…
CREATE FUNCTION chilito_proteger_lectura_aviso() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.aviso_id IS DISTINCT FROM OLD.aviso_id OR NEW.usuario_id IS DISTINCT FROM OLD.usuario_id THEN
    RAISE EXCEPTION 'No se puede reasignar una lectura de aviso' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER chilito_lectura_aviso_estable BEFORE UPDATE ON huerto_avisoleido
FOR EACH ROW EXECUTE FUNCTION chilito_proteger_lectura_aviso();

-- …y solo puede marcarla quien tiene membresía activa en ese huerto.
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

-- 8.4 Soporte técnico ---------------------------------------------------------------------------------
-- Un permiso de soporte solo admite revocarse, una vez y sin vuelta atrás.
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
CREATE TRIGGER permiso_solo_revocar BEFORE UPDATE OR DELETE ON public.datos_permisosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_permiso_revocar();

-- Una sesión técnica solo admite cerrarse, una vez.
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
CREATE TRIGGER tecnica_solo_cerrar BEFORE UPDATE OR DELETE ON public.datos_sesiontecnica FOR EACH ROW EXECUTE FUNCTION public.chilito_tecnica_cerrar();

-- Coherencia entre recursos: dispositivo del mismo huerto, permiso del mismo solicitante, sesión con
-- permiso vigente, solicitud dentro de la autorización y auditoría que apunta a registros del mismo actor.
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
CREATE TRIGGER relacion_casosoporte BEFORE INSERT ON public.datos_casosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();
CREATE TRIGGER relacion_permisosoporte BEFORE INSERT ON public.datos_permisosoporte FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();
CREATE TRIGGER relacion_sesiontecnica BEFORE INSERT ON public.datos_sesiontecnica FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();
CREATE TRIGGER relacion_solicitud BEFORE INSERT ON public.datos_solicitud FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();
CREATE TRIGGER relacion_auditoria BEFORE INSERT ON public.datos_auditoria FOR EACH ROW EXECUTE FUNCTION public.chilito_datos_relaciones();

-- 8.5 Mantenimientos ----------------------------------------------------------------------------------
-- Una revisión exige: editor asignado al huerto, número consecutivo y que el registro no esté anulado.
CREATE FUNCTION public.chilito_revision_mantenimiento() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE g bigint; ultimo integer; anulado boolean;
BEGIN
 SELECT huerto_id INTO g FROM public.datos_mantenimiento WHERE id=NEW.mantenimiento_id;
 IF NOT FOUND THEN
  RAISE EXCEPTION 'Mantenimiento inexistente' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.datos_asignacionmantenimiento
               WHERE usuario_id=NEW.editor_id AND huerto_id=g AND activa) THEN
  RAISE EXCEPTION 'Editor sin asignacion en este huerto' USING ERRCODE='23514';
 END IF;
 SELECT coalesce(max(numero),0),coalesce(bool_or(tipo='anulacion'),false) INTO ultimo,anulado
  FROM public.datos_revisionmantenimiento WHERE mantenimiento_id=NEW.mantenimiento_id;
 IF anulado THEN
  RAISE EXCEPTION 'Un registro anulado no admite revisiones' USING ERRCODE='23514';
 END IF;
 -- En concurrencia ambas transacciones calculan igual: decide el UNIQUE de numero.
 IF NEW.numero<>ultimo+1 THEN
  RAISE EXCEPTION 'Numero de revision fuera de orden' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER relacion_revisionmantenimiento BEFORE INSERT ON public.datos_revisionmantenimiento
 FOR EACH ROW EXECUTE FUNCTION public.chilito_revision_mantenimiento();

-- La auditoría de una revisión debe ser del mismo editor y del mismo huerto.
CREATE FUNCTION public.chilito_auditoria_revision() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE e bigint; g bigint;
BEGIN
 IF NEW.revision_mantenimiento_id IS NOT NULL THEN
  SELECT r.editor_id,m.huerto_id INTO e,g FROM public.datos_revisionmantenimiento r
   JOIN public.datos_mantenimiento m ON m.id=r.mantenimiento_id
   WHERE r.id=NEW.revision_mantenimiento_id;
  IF NOT FOUND OR e IS DISTINCT FROM NEW.actor_id OR g IS DISTINCT FROM NEW.huerto_id THEN
   RAISE EXCEPTION 'Auditoria de otra revision de mantenimiento' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER relacion_auditoria_revision BEFORE INSERT ON public.datos_auditoria
 FOR EACH ROW EXECUTE FUNCTION public.chilito_auditoria_revision();

-- Una asignación solo puede activarse o desactivarse; no cambia de persona, huerto ni fecha.
CREATE FUNCTION public.chilito_asignacion_estable() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.usuario_id IS DISTINCT FROM OLD.usuario_id
    OR NEW.huerto_id IS DISTINCT FROM OLD.huerto_id OR NEW.asignada_en IS DISTINCT FROM OLD.asignada_en THEN
  RAISE EXCEPTION 'La identidad de una asignacion no puede reasignarse' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_asignacion_estable BEFORE UPDATE ON public.datos_asignacionmantenimiento
 FOR EACH ROW EXECUTE FUNCTION public.chilito_asignacion_estable();

-- 8.6 Buzón y avisos por correo -----------------------------------------------------------------------
-- Una consulta no se borra y solo avanza: nueva→atendida|archivada, atendida→archivada, archivada→atendida.
CREATE FUNCTION public.chilito_consulta_atencion() RETURNS trigger
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
CREATE TRIGGER consulta_solo_avanzar BEFORE UPDATE OR DELETE ON public.datos_consultaproducto FOR EACH ROW EXECUTE FUNCTION public.chilito_consulta_atencion();

-- Un aviso por correo no se borra; solo registra intentos hasta que el servidor de correo lo acepta.
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

-- 8.7 Vinculación de huertos --------------------------------------------------------------------------
-- Un código no se borra; se cierra una sola vez (consumido, revocado, reemplazado o bloqueado).
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

-- Al confirmar la transacción, toda membresía nueva debe venir de un código consumido coherente.
-- Excepción: el propietario de la tabla (chilito_pkg_owner) puede crearlas a mano.
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

-- 8.8 Guías de cuidado --------------------------------------------------------------------------------
-- Las guías no se borran; no cambian identidad ni autoría; cada edición sube la versión en 1.
CREATE FUNCTION public.chilito_guia_cuidado() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'Las guias no se borran: se retiran' USING ERRCODE='23514';
 END IF;
 IF NEW.id<>OLD.id OR NEW.clave<>OLD.clave OR NEW.creado_en<>OLD.creado_en
    OR NEW.creado_por_id IS DISTINCT FROM OLD.creado_por_id THEN
  RAISE EXCEPTION 'La identidad y autoria de una guia no cambian' USING ERRCODE='23514';
 END IF;
 IF NEW.version<>OLD.version+1 OR NEW.actualizado_por_id IS NULL THEN
  RAISE EXCEPTION 'Cada cambio avanza la version e indica su responsable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER historial_guiacuidado BEFORE UPDATE OR DELETE ON public.datos_guiacuidado
 FOR EACH ROW EXECUTE FUNCTION public.chilito_guia_cuidado();

-- 8.9 Privacidad --------------------------------------------------------------------------------------
-- Documentos, finalidades, decisiones y eventos no se modifican ni se borran.
CREATE FUNCTION public.chilito_privacidad_historial_inmutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'El historial de privacidad no se modifica ni elimina mediante operaciones ordinarias'
  USING ERRCODE='23514';
END $$;
CREATE TRIGGER privacidad_documentoversion_inmutable BEFORE UPDATE OR DELETE
 ON public.privacidad_documentoversion FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_historial_inmutable();
CREATE TRIGGER privacidad_finalidadopcional_inmutable BEFORE UPDATE OR DELETE
 ON public.privacidad_finalidadopcional FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_historial_inmutable();
CREATE TRIGGER privacidad_decisionprivacidad_inmutable BEFORE UPDATE OR DELETE
 ON public.privacidad_decisionprivacidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_historial_inmutable();
CREATE TRIGGER privacidad_eventoprivacidad_inmutable BEFORE UPDATE OR DELETE
 ON public.privacidad_eventoprivacidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_historial_inmutable();

-- Un sujeto no cambia de identificador, fecha ni ámbito, ni se desvincula de su cuenta.
CREATE FUNCTION public.chilito_privacidad_sujeto_estable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.creado_en IS DISTINCT FROM OLD.creado_en
    OR NEW.ambito IS DISTINCT FROM OLD.ambito
    OR (OLD.usuario_id IS NOT NULL AND NEW.usuario_id IS DISTINCT FROM OLD.usuario_id) THEN
  RAISE EXCEPTION 'No se reasigna un sujeto, su ámbito ni su cuenta vinculada' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER privacidad_sujeto_vinculo_estable BEFORE UPDATE
 ON public.privacidad_sujetoprivacidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_sujeto_estable();

-- Cada acto corresponde a su documento; la preferencia y los eventos, al mismo sujeto y finalidad.
CREATE FUNCTION public.chilito_privacidad_relaciones() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE
 tipo_documento varchar(16);
 tipo_politica varchar(16);
 d public.privacidad_decisionprivacidad%ROWTYPE;
 titular bigint;
BEGIN
 IF TG_TABLE_NAME='privacidad_decisionprivacidad' THEN
  SELECT tipo INTO tipo_documento FROM public.privacidad_documentoversion WHERE id=NEW.documento_id;
  IF (NEW.acto='aceptacion_terminos' AND tipo_documento IS DISTINCT FROM 'terminos')
     OR (NEW.acto IN ('lectura_aviso','consentimiento','cookies') AND tipo_documento IS DISTINCT FROM 'aviso_privacidad') THEN
   RAISE EXCEPTION 'El acto no corresponde al tipo de documento'
    USING ERRCODE='23514';
  END IF;
  IF NEW.acto='cookies' THEN
   SELECT tipo INTO tipo_politica FROM public.privacidad_documentoversion WHERE id=NEW.politica_cookies_id;
   IF tipo_politica IS DISTINCT FROM 'politica_cookies' THEN
    RAISE EXCEPTION 'La decisión de cookies exige una política de cookies versionada'
     USING ERRCODE='23514';
   END IF;
  END IF;
 ELSIF TG_TABLE_NAME='privacidad_preferenciafinalidad' THEN
  IF TG_OP='UPDATE' THEN
   IF NEW.id IS DISTINCT FROM OLD.id OR NEW.sujeto_id IS DISTINCT FROM OLD.sujeto_id
      OR NEW.finalidad_id IS DISTINCT FROM OLD.finalidad_id THEN
    RAISE EXCEPTION 'No se reasigna la identidad de una preferencia'
     USING ERRCODE='23514';
   END IF;
  END IF;
  SELECT * INTO d FROM public.privacidad_decisionprivacidad WHERE id=NEW.decision_id;
  IF NOT FOUND OR d.sujeto_id IS DISTINCT FROM NEW.sujeto_id
     OR d.finalidad_id IS DISTINCT FROM NEW.finalidad_id OR (d.acto IS DISTINCT FROM 'consentimiento' AND d.acto IS DISTINCT FROM 'cookies') THEN
   RAISE EXCEPTION 'La preferencia exige consentimiento del mismo sujeto y finalidad'
    USING ERRCODE='23514';
  END IF;
 ELSIF TG_TABLE_NAME='privacidad_eventoprivacidad' THEN
  SELECT usuario_id INTO titular FROM public.privacidad_sujetoprivacidad WHERE id=NEW.sujeto_id;
  IF NOT FOUND OR NEW.actor_id IS DISTINCT FROM titular THEN
   RAISE EXCEPTION 'El actor del evento no corresponde a la cuenta del sujeto'
    USING ERRCODE='23514';
  END IF;
  IF NEW.decision_id IS NOT NULL THEN
   SELECT * INTO d FROM public.privacidad_decisionprivacidad WHERE id=NEW.decision_id;
   IF NOT FOUND OR d.sujeto_id IS DISTINCT FROM NEW.sujeto_id
      OR d.finalidad_id IS DISTINCT FROM NEW.finalidad_id THEN
    RAISE EXCEPTION 'La decisión del evento pertenece a otro sujeto o finalidad'
     USING ERRCODE='23514';
   END IF;
   IF NEW.accion='oposicion' AND NEW.resultado='completado' THEN
    IF (d.acto IS DISTINCT FROM 'consentimiento' AND d.acto IS DISTINCT FROM 'cookies')
       OR d.decision IS DISTINCT FROM FALSE THEN
     RAISE EXCEPTION 'La oposición completada requiere una decisión de rechazo'
      USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM public.privacidad_preferenciafinalidad
                  WHERE sujeto_id=NEW.sujeto_id AND finalidad_id=NEW.finalidad_id
                    AND decision_id=NEW.decision_id) THEN
     RAISE EXCEPTION 'La oposición completada debe corresponder a la preferencia vigente'
      USING ERRCODE='23514';
    END IF;
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER privacidad_decision_documento BEFORE INSERT
 ON public.privacidad_decisionprivacidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_relaciones();
CREATE TRIGGER privacidad_preferencia_coherente BEFORE INSERT OR UPDATE
 ON public.privacidad_preferenciafinalidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_relaciones();
CREATE TRIGGER privacidad_evento_coherente BEFORE INSERT
 ON public.privacidad_eventoprivacidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_relaciones();

-- Las cookies se deciden por navegador; el resto de actos, por cuenta.
CREATE FUNCTION public.chilito_privacidad_ambitos() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE alcance varchar(9);
BEGIN
 SELECT ambito INTO alcance FROM public.privacidad_sujetoprivacidad WHERE id=NEW.sujeto_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Sujeto inexistente' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='privacidad_decisionprivacidad' THEN
  IF (NEW.acto='cookies' AND alcance <> 'navegador')
     OR (NEW.acto<>'cookies' AND alcance <> 'cuenta') THEN
   RAISE EXCEPTION 'El acto no corresponde al ámbito del sujeto' USING ERRCODE='23514';
  END IF;
 ELSIF NEW.accion IN ('acceso','rectificacion') AND alcance <> 'cuenta' THEN
  RAISE EXCEPTION 'El perfil corresponde al ámbito cuenta' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER privacidad_decision_ambito BEFORE INSERT ON public.privacidad_decisionprivacidad
 FOR EACH ROW EXECUTE FUNCTION public.chilito_privacidad_ambitos();
CREATE TRIGGER privacidad_evento_ambito BEFORE INSERT ON public.privacidad_eventoprivacidad
 FOR EACH ROW EXECUTE FUNCTION public.chilito_privacidad_ambitos();


-- =====================================================================================================
-- 9. DATOS INICIALES
-- =====================================================================================================

-- 9.1 Tipos de contenido (uno por modelo de Django) ----------------------------------------------------
INSERT INTO public.django_content_type(app_label,model) VALUES
('auth','permission'),('auth','group'),('contenttypes','contenttype'),('sessions','session'),
('account','emailaddress'),('account','emailconfirmation'),('mfa','authenticator'),
('cuentas','usuario'),('cuentas','cuotaacceso'),('cuentas','confirmacionregistrolocal'),
('huerto','huerto'),('huerto','zona'),('huerto','membresia'),('huerto','aviso'),('huerto','avisoleido'),
('datos','dispositivo'),('datos','mantenimiento'),('datos','asignacionmantenimiento'),('datos','revisionmantenimiento'),
('datos','casosoporte'),('datos','permisosoporte'),('datos','resolucionsoporte'),('datos','sesiontecnica'),
('datos','validacionversion'),('datos','revisionconocimiento'),('datos','solicitud'),('datos','codigovinculacion'),
('datos','guiacuidado'),('datos','auditoria'),('datos','consultaproducto'),('datos','avisocorreo'),
('web','idempotencia'),
('privacidad','documentoversion'),('privacidad','sujetoprivacidad'),('privacidad','finalidadopcional'),
('privacidad','decisionprivacidad'),('privacidad','preferenciafinalidad'),('privacidad','eventoprivacidad'),
('privacidad','conteonavegacion');

-- 9.2 Permisos ----------------------------------------------------------------------------------------
-- Los cuatro estándar de Django por modelo (add/change/delete/view) y, colgadas de datos.dispositivo,
-- las SEIS CAPACIDADES DE ADMINISTRACIÓN:
--   ver_flota                 Telemetría de flota
--   atender_soporte           Consola remota (casos de soporte)
--   gestionar_mantenimientos  Mantenimientos de huertos asignados
--   atender_consultas         Solicitudes del producto (buzón de «Consíguelo»)
--   vincular_huertos          Vinculación de huertos (y la pestaña «Equipos y ventas»)
--   gestionar_guias           Guías de cuidado
INSERT INTO public.auth_permission(name,content_type_id,codename)
SELECT p.nombre, c.id, p.codigo
FROM (VALUES
 ('auth','permission','add_permission','Can add permission',1),
 ('auth','permission','change_permission','Can change permission',2),
 ('auth','permission','delete_permission','Can delete permission',3),
 ('auth','permission','view_permission','Can view permission',4),
 ('auth','group','add_group','Can add group',5),
 ('auth','group','change_group','Can change group',6),
 ('auth','group','delete_group','Can delete group',7),
 ('auth','group','view_group','Can view group',8),
 ('contenttypes','contenttype','add_contenttype','Can add content type',9),
 ('contenttypes','contenttype','change_contenttype','Can change content type',10),
 ('contenttypes','contenttype','delete_contenttype','Can delete content type',11),
 ('contenttypes','contenttype','view_contenttype','Can view content type',12),
 ('sessions','session','add_session','Can add session',13),
 ('sessions','session','change_session','Can change session',14),
 ('sessions','session','delete_session','Can delete session',15),
 ('sessions','session','view_session','Can view session',16),
 ('account','emailaddress','add_emailaddress','Can add email address',17),
 ('account','emailaddress','change_emailaddress','Can change email address',18),
 ('account','emailaddress','delete_emailaddress','Can delete email address',19),
 ('account','emailaddress','view_emailaddress','Can view email address',20),
 ('account','emailconfirmation','add_emailconfirmation','Can add email confirmation',21),
 ('account','emailconfirmation','change_emailconfirmation','Can change email confirmation',22),
 ('account','emailconfirmation','delete_emailconfirmation','Can delete email confirmation',23),
 ('account','emailconfirmation','view_emailconfirmation','Can view email confirmation',24),
 ('mfa','authenticator','add_authenticator','Can add authenticator',25),
 ('mfa','authenticator','change_authenticator','Can change authenticator',26),
 ('mfa','authenticator','delete_authenticator','Can delete authenticator',27),
 ('mfa','authenticator','view_authenticator','Can view authenticator',28),
 ('cuentas','usuario','add_usuario','Can add usuario',29),
 ('cuentas','usuario','change_usuario','Can change usuario',30),
 ('cuentas','usuario','delete_usuario','Can delete usuario',31),
 ('cuentas','usuario','view_usuario','Can view usuario',32),
 ('cuentas','cuotaacceso','add_cuotaacceso','Can add cuota acceso',33),
 ('cuentas','cuotaacceso','change_cuotaacceso','Can change cuota acceso',34),
 ('cuentas','cuotaacceso','delete_cuotaacceso','Can delete cuota acceso',35),
 ('cuentas','cuotaacceso','view_cuotaacceso','Can view cuota acceso',36),
 ('cuentas','confirmacionregistrolocal','add_confirmacionregistrolocal','Can add confirmacion registro local',37),
 ('cuentas','confirmacionregistrolocal','change_confirmacionregistrolocal','Can change confirmacion registro local',38),
 ('cuentas','confirmacionregistrolocal','delete_confirmacionregistrolocal','Can delete confirmacion registro local',39),
 ('cuentas','confirmacionregistrolocal','view_confirmacionregistrolocal','Can view confirmacion registro local',40),
 ('huerto','huerto','add_huerto','Can add huerto',41),
 ('huerto','huerto','change_huerto','Can change huerto',42),
 ('huerto','huerto','delete_huerto','Can delete huerto',43),
 ('huerto','huerto','view_huerto','Can view huerto',44),
 ('huerto','zona','add_zona','Can add zona',45),
 ('huerto','zona','change_zona','Can change zona',46),
 ('huerto','zona','delete_zona','Can delete zona',47),
 ('huerto','zona','view_zona','Can view zona',48),
 ('huerto','membresia','add_membresia','Can add membresia',49),
 ('huerto','membresia','change_membresia','Can change membresia',50),
 ('huerto','membresia','delete_membresia','Can delete membresia',51),
 ('huerto','membresia','view_membresia','Can view membresia',52),
 ('huerto','aviso','add_aviso','Can add aviso',53),
 ('huerto','aviso','change_aviso','Can change aviso',54),
 ('huerto','aviso','delete_aviso','Can delete aviso',55),
 ('huerto','aviso','view_aviso','Can view aviso',56),
 ('huerto','avisoleido','add_avisoleido','Can add aviso leido',57),
 ('huerto','avisoleido','change_avisoleido','Can change aviso leido',58),
 ('huerto','avisoleido','delete_avisoleido','Can delete aviso leido',59),
 ('huerto','avisoleido','view_avisoleido','Can view aviso leido',60),
 ('datos','dispositivo','add_dispositivo','Can add dispositivo',61),
 ('datos','dispositivo','change_dispositivo','Can change dispositivo',62),
 ('datos','dispositivo','delete_dispositivo','Can delete dispositivo',63),
 ('datos','dispositivo','view_dispositivo','Can view dispositivo',64),
 ('datos','dispositivo','ver_flota','Consultar flota agregada',65),
 ('datos','dispositivo','atender_soporte','Atender casos de soporte',66),
 ('datos','dispositivo','gestionar_mantenimientos','Gestionar mantenimientos de huertos asignados',67),
 ('datos','dispositivo','atender_consultas','Atender consultas del producto',68),
 ('datos','dispositivo','vincular_huertos','Emitir y revocar códigos de vinculación de huertos',69),
 ('datos','dispositivo','gestionar_guias','Crear, editar, publicar y retirar guías de cuidado',70),
 ('datos','mantenimiento','add_mantenimiento','Can add mantenimiento',71),
 ('datos','mantenimiento','change_mantenimiento','Can change mantenimiento',72),
 ('datos','mantenimiento','delete_mantenimiento','Can delete mantenimiento',73),
 ('datos','mantenimiento','view_mantenimiento','Can view mantenimiento',74),
 ('datos','asignacionmantenimiento','add_asignacionmantenimiento','Can add asignacion mantenimiento',75),
 ('datos','asignacionmantenimiento','change_asignacionmantenimiento','Can change asignacion mantenimiento',76),
 ('datos','asignacionmantenimiento','delete_asignacionmantenimiento','Can delete asignacion mantenimiento',77),
 ('datos','asignacionmantenimiento','view_asignacionmantenimiento','Can view asignacion mantenimiento',78),
 ('datos','revisionmantenimiento','add_revisionmantenimiento','Can add revision mantenimiento',79),
 ('datos','revisionmantenimiento','change_revisionmantenimiento','Can change revision mantenimiento',80),
 ('datos','revisionmantenimiento','delete_revisionmantenimiento','Can delete revision mantenimiento',81),
 ('datos','revisionmantenimiento','view_revisionmantenimiento','Can view revision mantenimiento',82),
 ('datos','casosoporte','add_casosoporte','Can add caso soporte',83),
 ('datos','casosoporte','change_casosoporte','Can change caso soporte',84),
 ('datos','casosoporte','delete_casosoporte','Can delete caso soporte',85),
 ('datos','casosoporte','view_casosoporte','Can view caso soporte',86),
 ('datos','permisosoporte','add_permisosoporte','Can add permiso soporte',87),
 ('datos','permisosoporte','change_permisosoporte','Can change permiso soporte',88),
 ('datos','permisosoporte','delete_permisosoporte','Can delete permiso soporte',89),
 ('datos','permisosoporte','view_permisosoporte','Can view permiso soporte',90),
 ('datos','resolucionsoporte','add_resolucionsoporte','Can add resolucion soporte',91),
 ('datos','resolucionsoporte','change_resolucionsoporte','Can change resolucion soporte',92),
 ('datos','resolucionsoporte','delete_resolucionsoporte','Can delete resolucion soporte',93),
 ('datos','resolucionsoporte','view_resolucionsoporte','Can view resolucion soporte',94),
 ('datos','sesiontecnica','add_sesiontecnica','Can add sesion tecnica',95),
 ('datos','sesiontecnica','change_sesiontecnica','Can change sesion tecnica',96),
 ('datos','sesiontecnica','delete_sesiontecnica','Can delete sesion tecnica',97),
 ('datos','sesiontecnica','view_sesiontecnica','Can view sesion tecnica',98),
 ('datos','validacionversion','add_validacionversion','Can add validacion version',99),
 ('datos','validacionversion','change_validacionversion','Can change validacion version',100),
 ('datos','validacionversion','delete_validacionversion','Can delete validacion version',101),
 ('datos','validacionversion','view_validacionversion','Can view validacion version',102),
 ('datos','revisionconocimiento','add_revisionconocimiento','Can add revision conocimiento',103),
 ('datos','revisionconocimiento','change_revisionconocimiento','Can change revision conocimiento',104),
 ('datos','revisionconocimiento','delete_revisionconocimiento','Can delete revision conocimiento',105),
 ('datos','revisionconocimiento','view_revisionconocimiento','Can view revision conocimiento',106),
 ('datos','solicitud','add_solicitud','Can add solicitud',107),
 ('datos','solicitud','change_solicitud','Can change solicitud',108),
 ('datos','solicitud','delete_solicitud','Can delete solicitud',109),
 ('datos','solicitud','view_solicitud','Can view solicitud',110),
 ('datos','codigovinculacion','add_codigovinculacion','Can add codigo vinculacion',111),
 ('datos','codigovinculacion','change_codigovinculacion','Can change codigo vinculacion',112),
 ('datos','codigovinculacion','delete_codigovinculacion','Can delete codigo vinculacion',113),
 ('datos','codigovinculacion','view_codigovinculacion','Can view codigo vinculacion',114),
 ('datos','guiacuidado','add_guiacuidado','Can add guia cuidado',115),
 ('datos','guiacuidado','change_guiacuidado','Can change guia cuidado',116),
 ('datos','guiacuidado','delete_guiacuidado','Can delete guia cuidado',117),
 ('datos','guiacuidado','view_guiacuidado','Can view guia cuidado',118),
 ('datos','auditoria','add_auditoria','Can add auditoria',119),
 ('datos','auditoria','change_auditoria','Can change auditoria',120),
 ('datos','auditoria','delete_auditoria','Can delete auditoria',121),
 ('datos','auditoria','view_auditoria','Can view auditoria',122),
 ('datos','consultaproducto','add_consultaproducto','Can add consulta producto',123),
 ('datos','consultaproducto','change_consultaproducto','Can change consulta producto',124),
 ('datos','consultaproducto','delete_consultaproducto','Can delete consulta producto',125),
 ('datos','consultaproducto','view_consultaproducto','Can view consulta producto',126),
 ('datos','avisocorreo','add_avisocorreo','Can add aviso correo',127),
 ('datos','avisocorreo','change_avisocorreo','Can change aviso correo',128),
 ('datos','avisocorreo','delete_avisocorreo','Can delete aviso correo',129),
 ('datos','avisocorreo','view_avisocorreo','Can view aviso correo',130),
 ('web','idempotencia','add_idempotencia','Can add idempotencia',131),
 ('web','idempotencia','change_idempotencia','Can change idempotencia',132),
 ('web','idempotencia','delete_idempotencia','Can delete idempotencia',133),
 ('web','idempotencia','view_idempotencia','Can view idempotencia',134),
 ('privacidad','documentoversion','add_documentoversion','Can add documento version',135),
 ('privacidad','documentoversion','change_documentoversion','Can change documento version',136),
 ('privacidad','documentoversion','delete_documentoversion','Can delete documento version',137),
 ('privacidad','documentoversion','view_documentoversion','Can view documento version',138),
 ('privacidad','sujetoprivacidad','add_sujetoprivacidad','Can add sujeto privacidad',139),
 ('privacidad','sujetoprivacidad','change_sujetoprivacidad','Can change sujeto privacidad',140),
 ('privacidad','sujetoprivacidad','delete_sujetoprivacidad','Can delete sujeto privacidad',141),
 ('privacidad','sujetoprivacidad','view_sujetoprivacidad','Can view sujeto privacidad',142),
 ('privacidad','finalidadopcional','add_finalidadopcional','Can add finalidad opcional',143),
 ('privacidad','finalidadopcional','change_finalidadopcional','Can change finalidad opcional',144),
 ('privacidad','finalidadopcional','delete_finalidadopcional','Can delete finalidad opcional',145),
 ('privacidad','finalidadopcional','view_finalidadopcional','Can view finalidad opcional',146),
 ('privacidad','decisionprivacidad','add_decisionprivacidad','Can add decision privacidad',147),
 ('privacidad','decisionprivacidad','change_decisionprivacidad','Can change decision privacidad',148),
 ('privacidad','decisionprivacidad','delete_decisionprivacidad','Can delete decision privacidad',149),
 ('privacidad','decisionprivacidad','view_decisionprivacidad','Can view decision privacidad',150),
 ('privacidad','preferenciafinalidad','add_preferenciafinalidad','Can add preferencia finalidad',151),
 ('privacidad','preferenciafinalidad','change_preferenciafinalidad','Can change preferencia finalidad',152),
 ('privacidad','preferenciafinalidad','delete_preferenciafinalidad','Can delete preferencia finalidad',153),
 ('privacidad','preferenciafinalidad','view_preferenciafinalidad','Can view preferencia finalidad',154),
 ('privacidad','eventoprivacidad','add_eventoprivacidad','Can add evento privacidad',155),
 ('privacidad','eventoprivacidad','change_eventoprivacidad','Can change evento privacidad',156),
 ('privacidad','eventoprivacidad','delete_eventoprivacidad','Can delete evento privacidad',157),
 ('privacidad','eventoprivacidad','view_eventoprivacidad','Can view evento privacidad',158),
 ('privacidad','conteonavegacion','add_conteonavegacion','Can add conteo navegacion',159),
 ('privacidad','conteonavegacion','change_conteonavegacion','Can change conteo navegacion',160),
 ('privacidad','conteonavegacion','delete_conteonavegacion','Can delete conteo navegacion',161),
 ('privacidad','conteonavegacion','view_conteonavegacion','Can view conteo navegacion',162)
) AS p(app,modelo,codigo,nombre,orden)
JOIN public.django_content_type c ON c.app_label=p.app AND c.model=p.modelo
ORDER BY p.orden;

-- 9.3 Textos legales registrados y finalidad opcional -----------------------------------------------
-- La versión vigente de cada tipo es la más reciente (0.2 para aviso y términos; 0.1 para cookies).
-- La huella SHA-256 debe coincidir con el archivo de frontend/legales para mostrarse como registrada.
INSERT INTO public.privacidad_documentoversion(id,tipo,version,contenido_ref,contenido_sha256,registrado_en) VALUES
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e01','aviso_privacidad','0.1-borrador',
 'privacidad/documentos/aviso_privacidad-0.1-borrador.md',
 '9a55eaadc15d7fca8724a2136c872b14056c8d7faa6a4c4b105261d8197742bd',now()),
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e02','terminos','0.1-borrador',
 'privacidad/documentos/terminos-0.1-borrador.md',
 'e4887c9723ab81eff3771264c4734647f299ceeaef5cbc23fa5e15a62e209b08',now()),
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e03','politica_cookies','0.1-borrador',
 'privacidad/documentos/politica_cookies-0.1-borrador.md',
 'b529f06fc64c3f62f4f891af2fad9f6ff3f868f9cabecc5b36a22ae2b037efd9',now()),
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e05','aviso_privacidad','0.2-borrador',
 'privacidad/documentos/aviso_privacidad-0.2-borrador.md',
 'c1b1a3e626e43344b685e9c671d48c223126abd330985642702f6f48549e1c02',now()),
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e06','terminos','0.2-borrador',
 'privacidad/documentos/terminos-0.2-borrador.md',
 '565e817bab5f7fa8f65127db1d7c00033b6ce100757ac8a63c6b72d188ee5ce5',now());
INSERT INTO public.privacidad_finalidadopcional(id,codigo,descripcion,creada_en) VALUES
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e04','estadisticas_internas_navegacion',
 'Estadísticas internas voluntarias de navegación',now());

-- 9.4 Las 9 guías de cuidado iniciales, ya publicadas --------------------------------------------------
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('799107f9-96d5-5536-86dc-9bc276475df2'::uuid,'germinacion-inicio','¿Cómo comienzo a germinar mis semillas de habanero?','Etapa de germinación. Se hace fuera del sistema, en un semillero aparte con mezcla limpia para semillas. Cubre las semillas con una capa ligera y mantén la mezcla húmeda, sin encharcarla.

Las semillas de chile germinan mejor en un lugar cálido y estable que en uno frío. Cuando asomen los brotes, dales luz abundante: con poca luz, el tallo se alarga y se inclina.

Registrar la germinación solo deja constancia de lo que ya hiciste. El sistema no la realiza ni la comprueba.',10,'publicada','University of Minnesota Extension','https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/growing-peppers',1,now(),now(),NULL,NULL);
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('f849ea28-3a9e-5eae-9d67-ee7dca35aa0a'::uuid,'brotacion-tiempo','¿Cuánto puede tardar en brotar y qué debo observar?','No hay un plazo fijo. Depende de la edad de la semilla, la variedad, la temperatura y la humedad. El habanero puede tardar varias semanas, así que una espera larga no significa por sí sola que la siembra haya fallado.

Mientras tanto, observa que la mezcla siga húmeda y sin charcos, y que no aparezca moho ni mal olor. Si la mezcla se seca por completo o se mantiene empapada, la germinación puede fallar.

Cuando broten, vigila que el tallo no se alargue ni se doble hacia la luz.',20,'publicada','University of Minnesota Extension','https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/growing-peppers',1,now(),now(),NULL,NULL);
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('82e02837-ab58-5847-b9c9-873dad3def6e'::uuid,'trasplante-plantula','¿Cómo reconozco que la plántula está lista para trasplantar?','Etapa de trasplante. Guíate por la plántula y no por el calendario: tallo firme, hojas verdaderas además de las dos primeras, buen color y raíces que ya sostienen la mezcla al sacarla.

Si creció en otro lugar, acostúmbrala poco a poco a la luz y a las condiciones del huerto. Al trasplantar, no entierres el tallo más de lo que estaba y riega después. Si ya tiene flores, puedes retirarlas para que se concentre en crecer.

Las fechas de las guías para exteriores dependen de las heladas y de cada clima. No se aplican tal cual a un huerto interior.',30,'publicada','Oregon State University Extension','https://extension.oregonstate.edu/catalog/ec-1227-grow-your-own-peppers',1,now(),now(),NULL,NULL);
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('26fb7ca5-cd6e-5e36-8687-790308a24f8b'::uuid,'sustrato-perlita','¿Para qué sirve la perlita y cómo reviso el sustrato?','La perlita ayuda a conservar la aireación: mantiene espacios en la mezcla para que entren aire y agua y para que las raíces respiren.

Revisa si el agua drena con facilidad. Si notas compactación, malos olores o acumulación de sales, revisa la mezcla antes de volver a regar. Con el tiempo la mezcla se degrada y pierde esos espacios, así que conviene renovarla cuando deje de drenar bien.

Marcar la revisión hecha declara que ya la realizaste. El sistema no inspecciona el sustrato.',40,'publicada','University of Maryland Extension','https://extension.umd.edu/resource/growing-vegetables-containers-and-salad-tables',1,now(),now(),NULL,NULL);
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('4a0a2210-b48d-52a8-9058-a6c23d3f2cbc'::uuid,'riego-revision','¿Cuándo debo revisar el riego de mis plantas?','Etapa de crecimiento. Revisa antes de regar, no por un horario fijo: toca el sustrato un poco por debajo de la superficie. La velocidad con que se seca cambia con el tamaño de la planta, la luz, la temperatura y el recipiente.

Que una planta se marchite no prueba que le falte agua: el exceso de riego también la marchita. Un sustrato siempre empapado deja a las raíces sin aire y puede dañarlas. Evita que quede agua estancada.

La lectura de humedad, cuando existe, es un dato más. Confírmala revisando la planta y el sustrato.',50,'publicada','University of Maryland Extension','https://extension.umd.edu/resource/growing-vegetables-containers-and-salad-tables',1,now(),now(),NULL,NULL);
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('0cb10161-67a5-5b32-b6e7-2858e80f0e6e'::uuid,'deposito-recarga','¿Qué significa rellenar el depósito y registrar la recarga?','Rellenar es añadir agua limpia al depósito con tus propias manos. Después, «Ya rellené el depósito» guarda la fecha de ese cuidado.

Registrar un cuidado declara una acción que ya realizaste físicamente. No significa que el sistema la haya ejecutado o comprobado.

El flotador detecta nivel bajo. No mide los litros restantes ni confirma que el depósito esté lleno, así que comprueba el nivel a simple vista al rellenarlo.',60,'publicada','','',1,now(),now(),NULL,NULL);
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('492a0e27-a4ad-5bff-bc1a-d693e5a6cb6a'::uuid,'mangueras-goteros','¿Cómo reviso las mangueras y los goteros?','Mira que las mangueras no estén dobladas, aplastadas ni sueltas, y que no haya fugas en las uniones. Comprueba que los cables y las conexiones estén secos.

Observa si cada gotero entrega agua de forma parecida a los demás. Un gotero que no gotea puede estar obstruido o tener la manguera doblada.

Si encuentras una fuga o algo no parece seguro, usa el paro físico del equipo y solicita soporte técnico. «Registrar inspección» declara que hiciste la revisión; el sistema no la comprueba.',70,'publicada','','',1,now(),now(),NULL,NULL);
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('75729f99-13f0-5f6d-95e8-acd12f6d7268'::uuid,'cosecha-registro','¿Cómo identifico y registro una cosecha?','Etapa de cosecha. Fíjate en el fruto y no en una fecha: firme, de tamaño completo y con el color final de su variedad. El tiempo y la cantidad de frutos varían de una planta a otra.

Corta con utensilios limpios y deja un poco de tallo unido al fruto, sin tirar para no romper las ramas. Usa guantes: el habanero irrita la piel y los ojos. Retirar los frutos maduros con regularidad favorece que la planta siga produciendo.

Después, «Registrar cosecha» guarda la fecha de lo que ya hiciste. El sistema no detecta la cosecha ni la comprueba.',80,'publicada','Oregon State University Extension','https://extension.oregonstate.edu/catalog/ec-1227-grow-your-own-peppers',1,now(),now(),NULL,NULL);
INSERT INTO public.datos_guiacuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('e4848719-fa76-5bbe-8267-8c140f0db5ac'::uuid,'sin-lecturas','¿Qué hago si no hay lecturas o el dispositivo está desconectado?','Sin lecturas válidas no puede deducirse el estado de la planta: «sin datos» no significa que esté bien ni que le falte agua. Una lectura antigua tampoco describe lo que ocurre ahora.

Mientras tanto, revisa directamente las plantas, el sustrato y el depósito. Comprueba que el equipo tenga corriente y que tu red Wi-Fi funcione.

Si el problema continúa, repórtalo en Soporte técnico.',90,'publicada','','',1,now(),now(),NULL,NULL);

-- 9.5 Registro de migraciones: Django las da por aplicadas y no intenta crear nada de nuevo -----------
INSERT INTO public.django_migrations(app,name,applied) VALUES
('contenttypes','0001_initial',now()),
('contenttypes','0002_remove_content_type_name',now()),
('auth','0001_initial',now()),
('auth','0002_alter_permission_name_max_length',now()),
('auth','0003_alter_user_email_max_length',now()),
('auth','0004_alter_user_username_opts',now()),
('auth','0005_alter_user_last_login_null',now()),
('auth','0006_require_contenttypes_0002',now()),
('auth','0007_alter_validators_add_error_messages',now()),
('auth','0008_alter_user_username_max_length',now()),
('auth','0009_alter_user_last_name_max_length',now()),
('auth','0010_alter_group_name_max_length',now()),
('auth','0011_update_proxy_permissions',now()),
('auth','0012_alter_user_first_name_max_length',now()),
('cuentas','0001_initial',now()),
('account','0001_initial',now()),
('account','0002_email_max_length',now()),
('account','0003_alter_emailaddress_create_unique_verified_email',now()),
('account','0004_alter_emailaddress_drop_unique_email',now()),
('account','0005_emailaddress_idx_upper_email',now()),
('account','0006_emailaddress_lower',now()),
('account','0007_emailaddress_idx_email',now()),
('account','0008_emailaddress_unique_primary_email_fixup',now()),
('account','0009_emailaddress_unique_primary_email',now()),
('mfa','0001_initial',now()),
('mfa','0002_authenticator_timestamps',now()),
('mfa','0003_authenticator_type_uniq',now()),
('cuentas','0002_cuotas_acceso',now()),
('cuentas','0003_confirmacion_registro_local',now()),
('cuentas','0004_identidad_correo_gmail',now()),
('cuentas','0005_perfil_bienvenida',now()),
('cuentas','0006_identidad_correo_ampliada',now()),
('cuentas','0007_proteger_mfa',now()),
('huerto','0001_initial',now()),
('huerto','0002_identidades_estables',now()),
('huerto','0003_avisos',now()),
('huerto','0004_relaciones_avisos',now()),
('huerto','0005_aviso_aviso_titulo_significativo_and_more',now()),
('huerto','0006_tres_zonas_y_lecturas',now()),
('huerto','0007_una_membresia_activa_por_cuenta',now()),
('datos','0001_initial',now()),
('datos','0002_integridad_historial',now()),
('datos','0003_sesiontecnica_tecnica_admin_una_abierta',now()),
('datos','0004_revisiones_y_asignacion_mantenimiento',now()),
('datos','0005_integridad_revisiones',now()),
('datos','0006_correccion_exige_tipo',now()),
('datos','0007_auditoria_retiro_factores',now()),
('datos','0008_soporte_resuelto_y_buzon',now()),
('datos','0009_consulta_archivada_a_atendida',now()),
('datos','0010_vinculacion_huerto',now()),
('datos','0011_guias_cuidado',now()),
('datos','0012_guias_iniciales',now()),
('datos','0013_retiro_capacidades_gobernanza',now()),
('privacidad','0001_initial',now()),
('privacidad','0002_integridad_privacidad',now()),
('privacidad','0003_cookies_y_acceso',now()),
('privacidad','0004_perfil_navegadores_estadisticas',now()),
('privacidad','0005_catalogo_inicial',now()),
('privacidad','0006_documentos_con_texto_publicado',now()),
('sessions','0001_initial',now()),
('web','0001_initial',now());


-- =====================================================================================================
-- 10. PRIVILEGIOS DEL ROL DE LA APLICACIÓN (chilito_pkg_runtime)
--     Mínimo privilegio: sin DDL, sin DELETE en historiales y con UPDATE solo en las columnas necesarias.
--     Lo que no aparece aquí, la aplicación NO lo puede hacer aunque lo intente.
-- =====================================================================================================

-- Nadie más puede conectarse a la base ni usar el esquema; la aplicación sí.
DO $$ BEGIN
 EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
 EXECUTE format('GRANT CONNECT ON DATABASE %I TO chilito_pkg_runtime', current_database());
END $$;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO chilito_pkg_runtime;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM chilito_pkg_runtime;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM chilito_pkg_runtime;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;

-- Cuentas, permisos y huertos: lectura.
GRANT SELECT ON public.cuentas_usuario,public.account_emailaddress,public.account_emailconfirmation,
 public.cuentas_confirmacionregistrolocal,public.huerto_huerto,public.huerto_zona,public.huerto_membresia,
 public.huerto_aviso,public.huerto_avisoleido,public.auth_permission,public.auth_group,
 public.auth_group_permissions,public.cuentas_usuario_groups,public.cuentas_usuario_user_permissions,
 public.django_content_type TO chilito_pkg_runtime;
-- Registro de cuentas y lectura de avisos.
GRANT INSERT ON public.cuentas_usuario,public.cuentas_confirmacionregistrolocal,public.huerto_avisoleido TO chilito_pkg_runtime;
-- Perfil, contraseña y último acceso. NO puede tocar is_staff, is_superuser ni is_active.
GRANT UPDATE(email,password,last_login,first_name,last_name,alias,bienvenida_atendida_en) ON public.cuentas_usuario TO chilito_pkg_runtime;
-- Sesiones, cuotas y correos: control completo (son datos de trabajo que caducan).
GRANT SELECT,INSERT,UPDATE,DELETE ON public.django_session,public.cuentas_cuotas_acceso,
 public.account_emailaddress,public.account_emailconfirmation TO chilito_pkg_runtime;
-- Segundo factor: allauth guarda con save() completo; el trigger impide cambiar dueño o tipo.
GRANT SELECT,INSERT,DELETE ON public.mfa_authenticator TO chilito_pkg_runtime;
GRANT UPDATE(user_id,type,data,created_at,last_used_at) ON public.mfa_authenticator TO chilito_pkg_runtime;

-- Operación: casi todo es solo lectura e inserción.
GRANT SELECT ON public.datos_dispositivo TO chilito_pkg_runtime;
GRANT SELECT,INSERT ON public.datos_mantenimiento,public.datos_casosoporte,public.datos_permisosoporte,
 public.datos_sesiontecnica,public.datos_validacionversion,public.datos_revisionconocimiento,
 public.datos_solicitud,public.datos_auditoria TO chilito_pkg_runtime;
GRANT UPDATE(revocado_en) ON public.datos_permisosoporte TO chilito_pkg_runtime;
GRANT UPDATE(cerrada_en,motivo_cierre) ON public.datos_sesiontecnica TO chilito_pkg_runtime;
-- Soporte resuelto y buzón: resoluciones solo se insertan; consultas y avisos solo avanzan su estado.
GRANT SELECT,INSERT ON public.datos_resolucionsoporte,public.datos_consultaproducto,public.datos_avisocorreo TO chilito_pkg_runtime;
GRANT UPDATE(estado,atendida_por_id,atendida_en) ON public.datos_consultaproducto TO chilito_pkg_runtime;
GRANT UPDATE(estado,intentos,ultimo_intento_en,aceptado_en) ON public.datos_avisocorreo TO chilito_pkg_runtime;
-- Vinculación: los códigos se insertan y solo cierran su estado; la membresía solo se crea.
GRANT SELECT,INSERT ON public.datos_codigovinculacion TO chilito_pkg_runtime;
GRANT UPDATE(estado,intentos,cerrado_en,membresia_id,envio) ON public.datos_codigovinculacion TO chilito_pkg_runtime;
GRANT INSERT ON public.huerto_membresia TO chilito_pkg_runtime;
-- Guías: sin DELETE (baja lógica) y sin UPDATE de identidad, autoría ni fecha de creación.
GRANT SELECT,INSERT ON public.datos_guiacuidado TO chilito_pkg_runtime;
GRANT UPDATE(pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,actualizado_en,actualizado_por_id) ON public.datos_guiacuidado TO chilito_pkg_runtime;
-- Mantenimientos: revisiones de solo inserción. Las asignaciones solo las administra el propietario.
GRANT SELECT,INSERT ON public.datos_revisionmantenimiento TO chilito_pkg_runtime;
GRANT SELECT ON public.datos_asignacionmantenimiento TO chilito_pkg_runtime;
-- Bloquear filas (SELECT … FOR UPDATE) exige UPDATE; las columnas siguen protegidas por triggers.
GRANT UPDATE(usuario_id) ON public.huerto_membresia TO chilito_pkg_runtime;
GRANT UPDATE(id) ON public.datos_casosoporte,public.datos_validacionversion TO chilito_pkg_runtime;
GRANT UPDATE(id) ON public.datos_mantenimiento TO chilito_pkg_runtime;

-- Privacidad: catálogos de solo lectura; decisiones e historial sin UPDATE ni DELETE.
GRANT SELECT ON public.privacidad_documentoversion,public.privacidad_finalidadopcional TO chilito_pkg_runtime;
GRANT SELECT,INSERT ON public.privacidad_sujetoprivacidad,public.privacidad_decisionprivacidad,
 public.privacidad_preferenciafinalidad TO chilito_pkg_runtime;
GRANT UPDATE(usuario_id) ON public.privacidad_sujetoprivacidad TO chilito_pkg_runtime;
GRANT UPDATE(decision_id,actualizada_en) ON public.privacidad_preferenciafinalidad TO chilito_pkg_runtime;
GRANT INSERT ON public.privacidad_eventoprivacidad TO chilito_pkg_runtime;
GRANT SELECT(id,creado_en) ON public.privacidad_eventoprivacidad TO chilito_pkg_runtime;
-- Contador de visitas: solo totales diarios.
GRANT SELECT,INSERT ON public.privacidad_conteonavegacion TO chilito_pkg_runtime;
GRANT UPDATE(visitas) ON public.privacidad_conteonavegacion TO chilito_pkg_runtime;

-- Recibos de idempotencia y lectura del registro de migraciones (Django lo revisa al arrancar).
GRANT SELECT,INSERT ON public.web_idempotencia TO chilito_pkg_runtime;
GRANT SELECT ON public.django_migrations TO chilito_pkg_runtime;

-- Secuencias de las tablas en las que la aplicación inserta con id automático.
DO $$ DECLARE tab text; seq text; BEGIN
 FOREACH tab IN ARRAY ARRAY['cuentas_usuario','cuentas_confirmacionregistrolocal','account_emailaddress',
 'account_emailconfirmation','huerto_avisoleido','datos_revisionconocimiento','huerto_membresia',
 'web_idempotencia','privacidad_conteonavegacion','mfa_authenticator'] LOOP
  seq:=pg_get_serial_sequence('public.'||tab,'id');
  IF seq IS NOT NULL THEN EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %s TO chilito_pkg_runtime',seq); END IF;
 END LOOP;
END $$;

-- La única función que la aplicación llama directamente.
GRANT EXECUTE ON FUNCTION public.chilito_identidad_correo(text) TO chilito_pkg_runtime;

-- Lo que el propietario cree en el futuro tampoco quedará abierto a todos.
ALTER DEFAULT PRIVILEGES FOR ROLE chilito_pkg_owner IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE chilito_pkg_owner IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

COMMIT;

-- Comprobación rápida (opcional): debe mostrar 43 tablas.
-- SELECT count(*) FROM information_schema.tables WHERE table_schema='public';
