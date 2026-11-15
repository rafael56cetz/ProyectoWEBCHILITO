-- =====================================================================================================
--  EL CHILITO · BASE DE DATOS v2 (PostgreSQL 17)
--  Script único de instalación desde cero. Sustituye por completo a el_chilito_base_completa.sql (v1).
--  Huerto urbano inteligente de chile habanero · 1 huerto = 1 ESP32 = 3 plantas · Solo Yucatán.
--  Guía completa: FUNCIONAMIENTO-BASE-DE-DATOS-v2.md · No contiene contraseñas ni cuentas de personas.
--  Fecha: 14 de noviembre de 2026.
-- =====================================================================================================
--
--  CÓMO SE INSTALA
--  ---------------
--  PASO 1 · Como «postgres», conectado a la base «postgres» (quita los dos guiones de cada línea):
--
--    CREATE ROLE chilito_pkg_owner   LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
--    CREATE ROLE chilito_pkg_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
--    CREATE ROLE chilito_pkg_iot     LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
--    ALTER ROLE chilito_pkg_runtime SET search_path = pg_catalog, public;
--    ALTER ROLE chilito_pkg_iot     SET search_path = pg_catalog, public;
--
--         Pon las contraseñas en pgAdmin (Login/Group Roles › Definition). Nunca en un archivo.
--         Si la base v1 existe y no tiene datos que conservar, bórrala antes:
--           DROP DATABASE chilito_integracion_sinteticos;
--
--  PASO 2 · Como «postgres», esta línea SOLA:
--
--    CREATE DATABASE chilito_integracion_sinteticos OWNER chilito_pkg_owner;
--
--  PASO 3 · (Solo para revisar o probar) Conéctate a la base como chilito_pkg_owner y ejecuta ESTE ARCHIVO COMPLETO.
--           Es una sola transacción: si algo falla, no queda nada a medias.
--
--  IMPORTANTE · La base OFICIAL la crean las migraciones de Django (python manage.py migrate, como
--             chilito_pkg_owner): son la fuente de verdad del esquema y producen una base equivalente a este
--             script. Usa este script para revisar la estructura en una base aparte o para las pruebas de
--             sql/pruebas/. Nunca uses «migrate --fake». Ver sección 3 de la guía.
--  PASO 4 · Publica los textos legales (sin ellos nadie puede registrarse). Ver sección 12 de la guía.
--  PASO 5 · Regístrate en la página y nómbrate super administrador:
--             SELECT chilito_designar_super_admin('tu-correo@dominio.com');
--
--  ROLES
--    chilito_pkg_owner    Tú (pgAdmin). Dueño de todo. Instala, nombra super admins, tareas periódicas.
--    chilito_pkg_runtime  La página (Django). Solo lo que cada pantalla necesita.
--    chilito_pkg_iot      Servicios en la nube: receptor MQTT (ESP32) e IA. Solo telemetría, estados y avisos.
--
--  ÍNDICE
--     0. Comprobaciones                    9. Comunicación: notificaciones, IA, buzón, correos, ventas
--     1. Funciones de apoyo               10. Legal y privacidad
--     2. Tablas internas de Django         11. Administración: historial de capacidades y auditoría
--     3. Cuentas                           12. Reglas (triggers) de cada área
--     4. Huertos y plantas                 13. Funciones de negocio y de administración
--     5. Dispositivos y vinculación        14. Vistas de consulta
--     6. Telemetría                        15. Datos iniciales
--     7. Comandos y autodiagnóstico        16. Privilegios de los roles
--     8. Cuidados, guías y soporte
--
--  CONVENCIONES
--    · Nombres de tablas, columnas y valores en español, sin acentos.
--    · Toda regla rota responde con el error 23514 (check_violation) y no guarda nada.
--    · «Actor»: en cada transacción que hace un cambio administrativo, Django ejecuta
--        SELECT set_config('chilito.actor_id', '<id de la cuenta>', true);
--      y, si quiere dejar motivo, set_config('chilito.motivo', '<texto>', true).
--      Sin actor, la base rechaza los cambios administrativos hechos por la aplicación.
-- =====================================================================================================

BEGIN;

-- =====================================================================================================
-- 0. COMPROBACIONES
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
 OR NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='chilito_pkg_iot')
 THEN RAISE EXCEPTION 'Faltan los roles chilito_pkg_runtime o chilito_pkg_iot: ejecuta antes el paso 1'; END IF;
END $$;

SET LOCAL search_path = public;  -- pg_catalog se busca siempre primero de forma implícita


-- =====================================================================================================
-- 1. FUNCIONES DE APOYO (sin acceso a tablas)
-- =====================================================================================================

-- Buzón real de un correo, para impedir cuentas duplicadas. En Gmail ignora mayúsculas, puntos y lo que
-- va tras «+», y trata googlemail.com como gmail.com. Ej.: Juan.Perez+huerto@googlemail.com → juanperez@gmail.com
CREATE FUNCTION public.chilito_identidad_correo(correo text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
 SELECT CASE WHEN lower(split_part(btrim(correo),'@',2)) IN ('gmail.com','googlemail.com')
   THEN replace(split_part(lower(split_part(btrim(correo),'@',1)),'+',1),'.','') || '@gmail.com'
   ELSE lower(btrim(correo)) END
$$;

-- Cuenta que realiza el cambio en esta transacción (la fija Django con set_config). NULL si no hay.
CREATE FUNCTION public.chilito_actor() RETURNS bigint
LANGUAGE sql STABLE PARALLEL SAFE AS $$
 SELECT nullif(current_setting('chilito.actor_id', true), '')::bigint
$$;

-- ¿Quién está conectado? Los triggers distinguen la aplicación, el servicio IoT y el propietario (pgAdmin
-- o tareas periódicas). Se usa session_user (el usuario con el que se inició la conexión), porque dentro de
-- una función SECURITY DEFINER current_user siempre es el propietario.
CREATE FUNCTION public.chilito_es_aplicacion() RETURNS boolean
LANGUAGE sql STABLE PARALLEL SAFE AS $$ SELECT session_user = 'chilito_pkg_runtime' $$;
CREATE FUNCTION public.chilito_es_propietario_bd() RETURNS boolean
LANGUAGE sql STABLE PARALLEL SAFE AS $$ SELECT session_user = 'chilito_pkg_owner' $$;

-- Error estándar de regla de negocio.
CREATE FUNCTION public.chilito_rechazar(mensaje text) RETURNS void
LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION '%', mensaje USING ERRCODE='23514'; END $$;


-- =====================================================================================================
-- 2. TABLAS INTERNAS DE DJANGO (formato exacto de Django; no cambiar nombres)
-- =====================================================================================================
CREATE TABLE django_migrations (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 app varchar(255) NOT NULL,
 name varchar(255) NOT NULL,
 applied timestamptz NOT NULL);

CREATE TABLE django_content_type (
 id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 app_label varchar(100) NOT NULL,
 model varchar(100) NOT NULL,
 CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model));

-- Permisos de Django. Las 10 capacidades de administración son filas de esta tabla (app «cuentas»).
CREATE TABLE auth_permission (
 id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 name varchar(255) NOT NULL,
 content_type_id integer NOT NULL REFERENCES django_content_type(id),
 codename varchar(100) NOT NULL,
 CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename));
CREATE INDEX auth_permission_content_type_id_2f476e4b ON auth_permission(content_type_id);

-- Grupos: Django los exige; El Chilito no los usa (las capacidades se dan cuenta por cuenta).
CREATE TABLE auth_group (
 id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 name varchar(150) NOT NULL UNIQUE);
CREATE TABLE auth_group_permissions (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 group_id integer NOT NULL REFERENCES auth_group(id),
 permission_id integer NOT NULL REFERENCES auth_permission(id),
 CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id));
CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON auth_group_permissions(permission_id);

-- Sesiones web. La cookie «sessionid» es la clave. Aquí viven también los códigos de verificación y de
-- acceso por correo (6 dígitos), firmados y con caducidad.
CREATE TABLE django_session (
 session_key varchar(40) NOT NULL PRIMARY KEY,
 session_data text NOT NULL,
 expire_date timestamptz NOT NULL);
CREATE INDEX django_session_expire_date_a5c62663 ON django_session(expire_date);


-- =====================================================================================================
-- 3. CUENTAS
-- =====================================================================================================

-- La cuenta. El correo es el usuario. La contraseña solo como resumen (hash). is_staff/is_superuser no se
-- usan (siempre false): la administración se da con capacidades.
-- Anonimizar: la persona lo pide (anonimizacion_solicitada_en); a los 15 días la tarea periódica borra sus
-- datos personales (anonimizada_en). Antes de eso puede cancelarlo.
CREATE TABLE cuentas_usuario (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 password varchar(128) NOT NULL,
 last_login timestamptz NULL,
 is_superuser boolean NOT NULL DEFAULT false,
 first_name varchar(150) NOT NULL DEFAULT '',
 last_name varchar(150) NOT NULL DEFAULT '',
 is_staff boolean NOT NULL DEFAULT false,
 is_active boolean NOT NULL DEFAULT true,
 date_joined timestamptz NOT NULL DEFAULT now(),
 email varchar(254) NOT NULL UNIQUE,
 alias varchar(64) NOT NULL DEFAULT '',
 bienvenida_atendida_en timestamptz NULL,
 anonimizacion_solicitada_en timestamptz NULL,
 anonimizada_en timestamptz NULL,
 CONSTRAINT usuario_alias_vacio_o_con_texto CHECK (alias = '' OR alias ~ '\S'),
 CONSTRAINT usuario_correo_con_arroba CHECK (email ~ '^[^@\s]+@[^@\s]+$'),
 CONSTRAINT usuario_sin_privilegios_django CHECK (NOT is_staff AND NOT is_superuser),
 CONSTRAINT usuario_anonimizada_inactiva CHECK (anonimizada_en IS NULL OR NOT is_active));
-- Un buzón real, una cuenta (también impide duplicados por mayúsculas).
CREATE UNIQUE INDEX usuario_identidad_correo_unica ON cuentas_usuario (chilito_identidad_correo(email));
CREATE INDEX usuario_anonimizacion_pendiente_idx ON cuentas_usuario(anonimizacion_solicitada_en)
 WHERE anonimizacion_solicitada_en IS NOT NULL AND anonimizada_en IS NULL;

CREATE TABLE cuentas_usuario_groups (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 usuario_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 group_id integer NOT NULL REFERENCES auth_group(id),
 CONSTRAINT cuentas_usuario_groups_usuario_id_group_id_f5ef6c73_uniq UNIQUE (usuario_id, group_id));
CREATE INDEX cuentas_usuario_groups_group_id_e6725cc8 ON cuentas_usuario_groups(group_id);

-- CAPACIDADES DE CADA CUENTA. Una fila por capacidad. Cada alta o baja queda en capacidad_historial.
CREATE TABLE cuentas_usuario_user_permissions (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 usuario_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 permission_id integer NOT NULL REFERENCES auth_permission(id),
 CONSTRAINT cuentas_usuario_user_per_usuario_id_permission_id_26c0acea_uniq UNIQUE (usuario_id, permission_id));
CREATE INDEX cuentas_usuario_user_permissions_permission_id_1753ad79 ON cuentas_usuario_user_permissions(permission_id);

-- Correo de cada cuenta y si está verificado (django-allauth). Sin correo verificado no se entra.
CREATE TABLE account_emailaddress (
 id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 email varchar(254) NOT NULL,
 verified boolean NOT NULL,
 "primary" boolean NOT NULL,
 user_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 CONSTRAINT account_emailaddress_user_id_email_987c8728_uniq UNIQUE (user_id, email));
CREATE UNIQUE INDEX unique_verified_email ON account_emailaddress(email) WHERE verified;
CREATE UNIQUE INDEX unique_primary_email ON account_emailaddress(user_id, "primary") WHERE "primary";
CREATE INDEX account_emailaddress_email_03be32b2 ON account_emailaddress(email);
CREATE INDEX account_emailaddress_user_id_2c513194 ON account_emailaddress(user_id);

-- Confirmación por enlace de allauth. La página verifica por CÓDIGO, así que queda vacía (allauth la exige).
CREATE TABLE account_emailconfirmation (
 id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 created timestamptz NOT NULL,
 sent timestamptz NULL,
 key varchar(64) NOT NULL UNIQUE,
 email_address_id integer NOT NULL REFERENCES account_emailaddress(id));
CREATE INDEX account_emailconfirmation_email_address_id_5b7f8c58 ON account_emailconfirmation(email_address_id);

-- Segundo factor: 'totp' (app autenticadora), 'recovery_codes' (códigos de recuperación), 'webauthn'
-- (llaves de acceso). Secretos cifrados por allauth.
CREATE TABLE mfa_authenticator (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 type varchar(20) NOT NULL,
 data jsonb NOT NULL,
 user_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 created_at timestamptz NOT NULL,
 last_used_at timestamptz NULL,
 CONSTRAINT mfa_tipo_valido CHECK (type IN ('totp','recovery_codes','webauthn')));
CREATE UNIQUE INDEX unique_authenticator_type ON mfa_authenticator(user_id, type) WHERE type IN ('totp','recovery_codes');
CREATE INDEX mfa_authenticator_user_id_0c3a50c0 ON mfa_authenticator(user_id);

-- Caché de Django en la base (formato de «createcachetable»): límites de intentos y marcas temporales.
CREATE TABLE cuentas_cuotas_acceso (
 cache_key varchar(255) NOT NULL PRIMARY KEY,
 value text NOT NULL,
 expires timestamptz NOT NULL);
CREATE INDEX cuentas_cuotas_acceso_expires_c8e0ee83 ON cuentas_cuotas_acceso(expires);

-- =====================================================================================================
-- 4. HUERTOS Y PLANTAS
-- =====================================================================================================

-- El huerto lo crea la propia persona. Máximo 3 activos por cuenta y solo 1 de ellos sin equipo.
-- No se borra: se archiva (antes hay que desvincular su equipo). Solo Yucatán → zona America/Merida.
CREATE TABLE huerto (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 propietario_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 nombre varchar(60) NOT NULL DEFAULT 'Mi huerto',
 zona_horaria varchar(64) NOT NULL DEFAULT 'America/Merida',
 estado varchar(10) NOT NULL DEFAULT 'activo',
 creado_en timestamptz NOT NULL DEFAULT now(),
 archivado_en timestamptz NULL,
 CONSTRAINT huerto_nombre_significativo CHECK (nombre ~ '\S'),
 CONSTRAINT huerto_solo_yucatan CHECK (zona_horaria = 'America/Merida'),
 CONSTRAINT huerto_estado_valido CHECK (estado IN ('activo','archivado')),
 CONSTRAINT huerto_archivo_coherente CHECK ((estado='activo' AND archivado_en IS NULL)
                                         OR (estado='archivado' AND archivado_en IS NOT NULL AND archivado_en >= creado_en)));
CREATE INDEX huerto_propietario_idx ON huerto(propietario_id) WHERE estado='activo';

-- Las 3 plantas de cada huerto. Las crea un trigger al crear el huerto; no se borran.
-- etapa: sin_sembrar → germinacion → plantula → crecimiento → floracion → fructificacion.
CREATE TABLE huerto_planta (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 numero smallint NOT NULL,
 nombre varchar(40) NOT NULL,
 fecha_siembra date NULL,
 etapa varchar(16) NOT NULL DEFAULT 'sin_sembrar',
 etapa_desde date NULL,
 CONSTRAINT planta_numero_unico UNIQUE (huerto_id, numero),
 CONSTRAINT planta_numero_1_3 CHECK (numero BETWEEN 1 AND 3),
 CONSTRAINT planta_nombre_significativo CHECK (nombre ~ '\S'),
 CONSTRAINT planta_etapa_valida CHECK (etapa IN ('sin_sembrar','germinacion','plantula','crecimiento','floracion','fructificacion')),
 CONSTRAINT planta_etapa_fecha CHECK ((etapa='sin_sembrar' AND etapa_desde IS NULL) OR (etapa<>'sin_sembrar' AND etapa_desde IS NOT NULL)),
 CONSTRAINT planta_fechas_coherentes CHECK (fecha_siembra IS NULL OR etapa_desde IS NULL OR etapa_desde >= fecha_siembra));

-- Historial de etapas de cada planta. Lo llena un trigger cada vez que cambia la etapa. No cambia.
CREATE TABLE huerto_planta_etapa (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 planta_id bigint NOT NULL REFERENCES huerto_planta(id),
 etapa varchar(16) NOT NULL,
 desde date NOT NULL,
 registrada_por_id bigint NULL REFERENCES cuentas_usuario(id),
 registrada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT planta_etapa_hist_valida CHECK (etapa IN ('sin_sembrar','germinacion','plantula','crecimiento','floracion','fructificacion')));
CREATE INDEX planta_etapa_hist_idx ON huerto_planta_etapa(planta_id, registrada_en DESC);


-- =====================================================================================================
-- 5. DISPOSITIVOS Y VINCULACIÓN
-- =====================================================================================================

-- Inventario de ESP32. Un admin con «gestionar_dispositivos» los da de alta ANTES de venderlos.
-- estado: disponible (en inventario o desvinculado) · vinculado (a un huerto) · retirado (baja definitiva).
-- conexion la actualiza el servicio IoT: nunca · en_linea · desconectado.
-- credencial_hash: resumen de la credencial MQTT individual (p. ej. PBKDF2). NUNCA la contraseña en claro.
CREATE TABLE dispositivo (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 identificador varchar(32) NOT NULL UNIQUE,
 mac macaddr NOT NULL UNIQUE,
 credencial_hash varchar(255) NOT NULL,
 firmware_version varchar(32) NOT NULL DEFAULT '',
 estado varchar(12) NOT NULL DEFAULT 'disponible',
 huerto_id bigint NULL UNIQUE REFERENCES huerto(id),
 vinculado_en timestamptz NULL,
 conexion varchar(12) NOT NULL DEFAULT 'nunca',
 ultima_conexion_en timestamptz NULL,
 registrado_por_id bigint NULL REFERENCES cuentas_usuario(id),
 registrado_en timestamptz NOT NULL DEFAULT now(),
 retirado_en timestamptz NULL,
 CONSTRAINT dispositivo_identificador_valido CHECK (identificador ~ '^[A-Za-z0-9][A-Za-z0-9-]{3,31}$'),
 CONSTRAINT dispositivo_credencial_resumida CHECK (length(credencial_hash) BETWEEN 32 AND 255 AND credencial_hash !~ '\s'),
 CONSTRAINT dispositivo_firmware_valido CHECK (firmware_version = '' OR firmware_version ~ '^[A-Za-z0-9._-]{1,32}$'),
 CONSTRAINT dispositivo_estado_valido CHECK (estado IN ('disponible','vinculado','retirado')),
 CONSTRAINT dispositivo_conexion_valida CHECK (conexion IN ('nunca','en_linea','desconectado')),
 CONSTRAINT dispositivo_vinculo_coherente CHECK (
      (estado='vinculado'  AND huerto_id IS NOT NULL AND vinculado_en IS NOT NULL AND retirado_en IS NULL)
   OR (estado='disponible' AND huerto_id IS NULL AND vinculado_en IS NULL AND retirado_en IS NULL)
   OR (estado='retirado'   AND huerto_id IS NULL AND vinculado_en IS NULL AND retirado_en IS NOT NULL)),
 CONSTRAINT dispositivo_conexion_coherente CHECK ((conexion='nunca') = (ultima_conexion_en IS NULL)));

-- Código de vinculación. Lo genera el DUEÑO del huerto en la web; lo escribe en el portal local del ESP32,
-- y el ESP32 lo presenta al backend. 10 minutos, un solo uso. Solo se guarda su HMAC-SHA256 (hex).
-- estado: pendiente → utilizado | expirado | cancelado (una sola vez).
CREATE TABLE codigo_vinculacion (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 generado_por_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 codigo_hash char(64) NOT NULL UNIQUE,
 generado_en timestamptz NOT NULL DEFAULT now(),
 vence_en timestamptz NOT NULL DEFAULT now() + interval '10 minutes',
 estado varchar(10) NOT NULL DEFAULT 'pendiente',
 dispositivo_id bigint NULL REFERENCES dispositivo(id),
 cerrado_en timestamptz NULL,
 CONSTRAINT codigo_hash_hex CHECK (codigo_hash ~ '^[0-9a-f]{64}$'),
 CONSTRAINT codigo_vigencia_10min CHECK (vence_en > generado_en AND vence_en <= generado_en + interval '10 minutes'),
 CONSTRAINT codigo_estado_valido CHECK (estado IN ('pendiente','utilizado','expirado','cancelado')),
 CONSTRAINT codigo_cierre_coherente CHECK (
      (estado='pendiente' AND cerrado_en IS NULL AND dispositivo_id IS NULL)
   OR (estado='utilizado' AND cerrado_en IS NOT NULL AND cerrado_en <= vence_en AND dispositivo_id IS NOT NULL)
   OR (estado IN ('expirado','cancelado') AND cerrado_en IS NOT NULL AND dispositivo_id IS NULL)));
CREATE UNIQUE INDEX codigo_pendiente_por_huerto ON codigo_vinculacion(huerto_id) WHERE estado='pendiente';
CREATE INDEX codigo_vencidos_idx ON codigo_vinculacion(vence_en) WHERE estado='pendiente';

-- Historial de cada equipo: alta, vinculación, desvinculación, conexiones, errores, reinicios… No cambia.
-- Responde «¿de qué huerto fue este equipo y cuándo?». detalle: código técnico corto, sin datos personales.
CREATE TABLE dispositivo_evento (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 dispositivo_id bigint NOT NULL REFERENCES dispositivo(id),
 huerto_id bigint NULL REFERENCES huerto(id),
 tipo varchar(20) NOT NULL,
 detalle varchar(200) NOT NULL DEFAULT '',
 actor_id bigint NULL REFERENCES cuentas_usuario(id),
 ocurrido_en timestamptz NOT NULL DEFAULT now(),
 registrado_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT disp_evento_tipo_valido CHECK (tipo IN ('alta','vinculado','desvinculado','conectado','desconectado',
   'error','reinicio','credencial_rotada','firmware_actualizado','retirado')));
CREATE INDEX disp_evento_dispositivo_idx ON dispositivo_evento(dispositivo_id, ocurrido_en DESC);
CREATE INDEX disp_evento_huerto_idx ON dispositivo_evento(huerto_id, ocurrido_en DESC) WHERE huerto_id IS NOT NULL;


-- =====================================================================================================
-- 6. TELEMETRÍA
--    Detalle: 90 días (medicion + medicion_planta). Para siempre: resumen por hora.
-- =====================================================================================================

-- Una fila por mensaje del ESP32. Datos del huerto completo. NULL = el sensor no envió valor.
--   temperatura_c, humedad_aire_pct → SHT31 · luz_lux → BH1750 (opcional) · deposito_con_agua → flotador
--   (true = hay agua; false = nivel bajo: el ESP32 bloquea las bombas). El flotador NO mide litros.
CREATE TABLE medicion (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 dispositivo_id bigint NOT NULL REFERENCES dispositivo(id),
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 medida_en timestamptz NOT NULL,
 recibida_en timestamptz NOT NULL DEFAULT now(),
 temperatura_c numeric(4,1) NULL,
 humedad_aire_pct numeric(4,1) NULL,
 luz_lux numeric(8,1) NULL,
 deposito_con_agua boolean NULL,
 CONSTRAINT medicion_unica UNIQUE (dispositivo_id, medida_en),
 CONSTRAINT medicion_no_futura CHECK (medida_en <= recibida_en + interval '5 minutes'),
 CONSTRAINT medicion_temperatura_rango CHECK (temperatura_c BETWEEN -20 AND 70),
 CONSTRAINT medicion_humedad_rango CHECK (humedad_aire_pct BETWEEN 0 AND 100),
 CONSTRAINT medicion_luz_rango CHECK (luz_lux BETWEEN 0 AND 200000));
CREATE INDEX medicion_huerto_fecha_idx ON medicion(huerto_id, medida_en DESC);
CREATE INDEX medicion_fecha_brin ON medicion USING brin(medida_en);

-- Humedad del sustrato de cada planta (3 sensores capacitivos v1.2) en ese mismo mensaje: porcentaje
-- calibrado y, para calibrar y dar soporte, la lectura analógica cruda del ESP32 (ADC de 12 bits).
CREATE TABLE medicion_planta (
 medicion_id bigint NOT NULL REFERENCES medicion(id) ON DELETE CASCADE,
 planta_numero smallint NOT NULL,
 humedad_sustrato_pct numeric(4,1) NOT NULL,
 adc_crudo smallint NULL,                      -- lectura analógica sin calibrar del sensor (0–4095)
 PRIMARY KEY (medicion_id, planta_numero),
 CONSTRAINT med_planta_numero_1_3 CHECK (planta_numero BETWEEN 1 AND 3),
 CONSTRAINT med_planta_humedad_rango CHECK (humedad_sustrato_pct BETWEEN 0 AND 100),
 CONSTRAINT med_planta_adc_rango CHECK (adc_crudo BETWEEN 0 AND 4095));

-- Resumen por hora del huerto (para gráficas largas). Lo calcula chilito_resumir_mediciones().
CREATE TABLE resumen_hora_huerto (
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 hora timestamptz NOT NULL,
 muestras integer NOT NULL,
 temperatura_prom numeric(4,1), temperatura_min numeric(4,1), temperatura_max numeric(4,1),
 humedad_aire_prom numeric(4,1), humedad_aire_min numeric(4,1), humedad_aire_max numeric(4,1),
 luz_prom numeric(8,1), luz_max numeric(8,1),
 muestras_sin_agua integer NOT NULL DEFAULT 0,
 PRIMARY KEY (huerto_id, hora),
 CONSTRAINT resumen_huerto_hora_exacta CHECK (hora = date_trunc('hour', hora, 'UTC')),
 CONSTRAINT resumen_huerto_muestras CHECK (muestras > 0 AND muestras_sin_agua BETWEEN 0 AND muestras));

-- Resumen por hora de cada planta.
CREATE TABLE resumen_hora_planta (
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 hora timestamptz NOT NULL,
 planta_numero smallint NOT NULL,
 muestras integer NOT NULL,
 humedad_prom numeric(4,1) NOT NULL, humedad_min numeric(4,1) NOT NULL, humedad_max numeric(4,1) NOT NULL,
 PRIMARY KEY (huerto_id, hora, planta_numero),
 CONSTRAINT resumen_planta_numero CHECK (planta_numero BETWEEN 1 AND 3),
 CONSTRAINT resumen_planta_hora_exacta CHECK (hora = date_trunc('hour', hora, 'UTC')),
 CONSTRAINT resumen_planta_muestras CHECK (muestras > 0));


-- =====================================================================================================
-- 7. COMANDOS, ACTUACIONES Y AUTODIAGNÓSTICO
-- =====================================================================================================

-- Órdenes para el ESP32 (viajan por MQTT en la fase IoT). Antes «solicitudes», que nunca cambiaban de estado.
--   origen usuario: regar (una planta), lampara_apagar, lampara_automatico, autodiagnostico.
--   origen soporte (dentro de una sesión técnica): además reiniciar, probar_bomba, ventilador_encender,
--   ventilador_apagar y lectura_inmediata.
-- estado: pendiente → enviado → confirmado | fallido | expirado (pendiente también puede fallar o expirar).
CREATE TABLE comando (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 dispositivo_id bigint NOT NULL REFERENCES dispositivo(id),
 tipo varchar(20) NOT NULL,
 planta_numero smallint NULL,
 duracion_s smallint NULL,
 origen varchar(8) NOT NULL,
 solicitado_por_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 sesion_id uuid NULL,                      -- FK a soporte_sesion (se añade al crear esa tabla)
 estado varchar(10) NOT NULL DEFAULT 'pendiente',
 creado_en timestamptz NOT NULL DEFAULT now(),
 enviado_en timestamptz NULL,
 resuelto_en timestamptz NULL,
 detalle_error varchar(200) NOT NULL DEFAULT '',
 CONSTRAINT comando_tipo_valido CHECK (tipo IN ('regar','lampara_apagar','lampara_automatico','autodiagnostico',
   'reiniciar','probar_bomba','ventilador_encender','ventilador_apagar','lectura_inmediata')),
 CONSTRAINT comando_origen_valido CHECK (origen IN ('usuario','soporte')),
 CONSTRAINT comando_tipo_por_origen CHECK (origen='soporte' OR tipo IN ('regar','lampara_apagar','lampara_automatico','autodiagnostico')),
 CONSTRAINT comando_sesion_por_origen CHECK ((origen='soporte') = (sesion_id IS NOT NULL)),
 CONSTRAINT comando_planta_por_tipo CHECK ((tipo IN ('regar','probar_bomba')) = (planta_numero IS NOT NULL)
                                        AND (planta_numero IS NULL OR planta_numero BETWEEN 1 AND 3)),
 CONSTRAINT comando_duracion_por_tipo CHECK ((tipo IN ('regar','probar_bomba')) = (duracion_s IS NOT NULL)
                                          AND (duracion_s IS NULL OR duracion_s BETWEEN 1 AND 30)),
 CONSTRAINT comando_estado_valido CHECK (estado IN ('pendiente','enviado','confirmado','fallido','expirado')),
 CONSTRAINT comando_fechas_coherentes CHECK (
      (estado='pendiente' AND enviado_en IS NULL AND resuelto_en IS NULL)
   OR (estado='enviado'   AND enviado_en IS NOT NULL AND enviado_en >= creado_en AND resuelto_en IS NULL)
   OR (estado='confirmado' AND enviado_en IS NOT NULL AND resuelto_en IS NOT NULL AND enviado_en >= creado_en AND resuelto_en >= enviado_en)
   OR (estado IN ('fallido','expirado') AND resuelto_en IS NOT NULL AND resuelto_en >= creado_en AND (enviado_en IS NULL OR resuelto_en >= enviado_en))),
 CONSTRAINT comando_error_solo_si_falla CHECK (detalle_error = '' OR estado IN ('fallido','expirado')));
-- No se acumulan órdenes iguales sin resolver (p. ej. dos «regar planta 2» seguidos).
CREATE UNIQUE INDEX comando_uno_en_curso ON comando(dispositivo_id, tipo, coalesce(planta_numero,0))
 WHERE estado IN ('pendiente','enviado');
CREATE INDEX comando_huerto_fecha_idx ON comando(huerto_id, creado_en DESC);
CREATE INDEX comando_en_curso_idx ON comando(creado_en) WHERE estado IN ('pendiente','enviado');

-- Lo que el equipo HIZO (lo reporta el ESP32): riegos por planta y su duración, lámpara y ventilador.
-- El estado actual de la lámpara es su última fila. origen: automatico (por sensor u horario), usuario, soporte.
CREATE TABLE actuacion (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 dispositivo_id bigint NOT NULL REFERENCES dispositivo(id),
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 actuador varchar(10) NOT NULL,
 planta_numero smallint NULL,
 accion varchar(10) NOT NULL,
 duracion_s smallint NULL,
 origen varchar(10) NOT NULL,
 comando_id uuid NULL REFERENCES comando(id),
 ocurrido_en timestamptz NOT NULL,
 registrado_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT actuacion_actuador_valido CHECK (actuador IN ('bomba','lampara','ventilador')),
 CONSTRAINT actuacion_planta_si_bomba CHECK ((actuador='bomba') = (planta_numero IS NOT NULL)
                                          AND (planta_numero IS NULL OR planta_numero BETWEEN 1 AND 3)),
 CONSTRAINT actuacion_accion_valida CHECK (accion IN ('encendido','apagado')),
 CONSTRAINT actuacion_duracion CHECK (duracion_s IS NULL OR (duracion_s BETWEEN 1 AND 600)),
 CONSTRAINT actuacion_origen_valido CHECK (origen IN ('automatico','usuario','soporte')),
 CONSTRAINT actuacion_origen_comando CHECK ((origen='automatico') = (comando_id IS NULL)));
CREATE INDEX actuacion_huerto_fecha_idx ON actuacion(huerto_id, ocurrido_en DESC);
CREATE INDEX actuacion_lampara_idx ON actuacion(huerto_id, ocurrido_en DESC) WHERE actuador='lampara';

-- Autodiagnóstico («Revisar mi equipo»): nace con un comando 'autodiagnostico'; el ESP32 reporta una
-- revisión por componente. estado: en_curso → completado | sin_respuesta.
CREATE TABLE autodiagnostico (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 dispositivo_id bigint NOT NULL REFERENCES dispositivo(id),
 comando_id uuid NOT NULL UNIQUE REFERENCES comando(id),
 solicitado_por_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 estado varchar(14) NOT NULL DEFAULT 'en_curso',
 resultado_general varchar(12) NULL,
 iniciado_en timestamptz NOT NULL DEFAULT now(),
 completado_en timestamptz NULL,
 CONSTRAINT autodiag_estado_valido CHECK (estado IN ('en_curso','completado','sin_respuesta')),
 CONSTRAINT autodiag_resultado_valido CHECK (resultado_general IN ('correcto','con_fallas')),
 CONSTRAINT autodiag_cierre_coherente CHECK (
      (estado='en_curso' AND completado_en IS NULL AND resultado_general IS NULL)
   OR (estado='completado' AND completado_en IS NOT NULL AND completado_en >= iniciado_en AND resultado_general IS NOT NULL)
   OR (estado='sin_respuesta' AND completado_en IS NOT NULL AND completado_en >= iniciado_en AND resultado_general IS NULL)));
CREATE INDEX autodiag_huerto_idx ON autodiagnostico(huerto_id, iniciado_en DESC);

CREATE TABLE autodiagnostico_revision (
 autodiagnostico_id uuid NOT NULL REFERENCES autodiagnostico(id),
 componente varchar(20) NOT NULL,
 resultado varchar(14) NOT NULL,
 detalle varchar(200) NOT NULL DEFAULT '',
 PRIMARY KEY (autodiagnostico_id, componente),
 CONSTRAINT revision_componente_valido CHECK (componente IN ('conexion','sensor_ambiente','sensor_luz',
   'sensor_sustrato_1','sensor_sustrato_2','sensor_sustrato_3','flotador',
   'bomba_1','bomba_2','bomba_3','lampara','ventilador')),
 CONSTRAINT revision_resultado_valido CHECK (resultado IN ('correcto','falla','sin_respuesta','no_instalado')));


-- =====================================================================================================
-- 8. CUIDADOS, GUÍAS Y SOPORTE
-- =====================================================================================================

-- Cuidados manuales que declara la persona (el sistema no los comprueba). No cambian: se corrigen con
-- cuidado_revision.  rellenar_deposito → del huerto (un solo depósito de 19 L) · sustrato, germinacion,
-- cosecha → de una planta · inspeccion → de una planta o del huerto. Fecha real: hasta 7 días atrás.
CREATE TABLE cuidado (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 planta_numero smallint NULL,
 tipo varchar(18) NOT NULL,
 chiles_cosechados smallint NULL,
 realizado_en timestamptz NOT NULL DEFAULT now(),
 registrado_por_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 registrado_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT cuidado_tipo_valido CHECK (tipo IN ('rellenar_deposito','sustrato','germinacion','cosecha','inspeccion')),
 CONSTRAINT cuidado_planta_por_tipo CHECK (
      (tipo='rellenar_deposito' AND planta_numero IS NULL)
   OR (tipo IN ('sustrato','germinacion','cosecha') AND planta_numero IS NOT NULL AND planta_numero BETWEEN 1 AND 3)
   OR (tipo='inspeccion' AND (planta_numero IS NULL OR planta_numero BETWEEN 1 AND 3))),
 CONSTRAINT cuidado_chiles_solo_cosecha CHECK (chiles_cosechados IS NULL OR (tipo='cosecha' AND chiles_cosechados BETWEEN 0 AND 999)),
 CONSTRAINT cuidado_fecha_realista CHECK (realizado_en <= registrado_en + interval '5 minutes'
                                       AND realizado_en >= registrado_en - interval '7 days'));
CREATE INDEX cuidado_huerto_fecha_idx ON cuidado(huerto_id, realizado_en DESC);

-- Correcciones (cambia tipo/planta/chiles) y anulaciones de un cuidado. Numeradas 1, 2, 3…; solo un admin
-- con «gestionar_mantenimientos». Un cuidado anulado no admite más revisiones.
CREATE TABLE cuidado_revision (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 cuidado_id uuid NOT NULL REFERENCES cuidado(id),
 numero integer NOT NULL,
 tipo varchar(10) NOT NULL,
 tipo_corregido varchar(18) NULL,
 planta_corregida smallint NULL,
 chiles_corregidos smallint NULL,
 motivo varchar(500) NOT NULL,
 editor_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 registrada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT revision_cuidado_orden UNIQUE (cuidado_id, numero),
 CONSTRAINT revision_cuidado_numero CHECK (numero >= 1),
 CONSTRAINT revision_cuidado_tipo CHECK (tipo IN ('correccion','anulacion')),
 CONSTRAINT revision_cuidado_motivo CHECK (motivo ~ '\S'),
 CONSTRAINT revision_cuidado_coherente CHECK (
      (tipo='anulacion' AND tipo_corregido IS NULL AND planta_corregida IS NULL AND chiles_corregidos IS NULL)
   OR (tipo='correccion' AND (
         (tipo_corregido='rellenar_deposito' AND planta_corregida IS NULL)
      OR (tipo_corregido IN ('sustrato','germinacion','cosecha') AND planta_corregida IS NOT NULL AND planta_corregida BETWEEN 1 AND 3)
      OR (tipo_corregido='inspeccion' AND (planta_corregida IS NULL OR planta_corregida BETWEEN 1 AND 3)))
      AND (chiles_corregidos IS NULL OR (tipo_corregido='cosecha' AND chiles_corregidos BETWEEN 0 AND 999)))));
CREATE UNIQUE INDEX revision_cuidado_una_anulacion ON cuidado_revision(cuidado_id) WHERE tipo='anulacion';

-- Guías de cuidado (preguntas frecuentes). Se retiran, no se borran. Cada cambio sube «version».
CREATE TABLE guia_cuidado (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 clave varchar(64) NOT NULL UNIQUE,
 pregunta varchar(200) NOT NULL,
 respuesta text NOT NULL,
 orden integer NOT NULL,
 estado varchar(10) NOT NULL DEFAULT 'borrador',
 fuente_nombre varchar(120) NOT NULL DEFAULT '',
 fuente_url varchar(500) NOT NULL DEFAULT '',
 version integer NOT NULL DEFAULT 1,
 creado_en timestamptz NOT NULL DEFAULT now(),
 actualizado_en timestamptz NOT NULL DEFAULT now(),
 creado_por_id bigint NULL REFERENCES cuentas_usuario(id),
 actualizado_por_id bigint NULL REFERENCES cuentas_usuario(id),
 CONSTRAINT guia_pregunta_significativa CHECK (pregunta ~ '\S'),
 CONSTRAINT guia_respuesta_significativa CHECK (respuesta ~ '\S' AND length(respuesta) <= 4000),
 CONSTRAINT guia_clave_valida CHECK (clave ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
 CONSTRAINT guia_orden_valido CHECK (orden BETWEEN 1 AND 9999),
 CONSTRAINT guia_estado_valido CHECK (estado IN ('borrador','publicada','retirada')),
 CONSTRAINT guia_version_valida CHECK (version >= 1),
 CONSTRAINT guia_fuente_valida CHECK (fuente_url = '' OR (fuente_url ~ '^https?://[^[:space:]]+$' AND fuente_nombre <> '')));
CREATE INDEX guia_estado_orden_idx ON guia_cuidado(estado, orden);

-- Caso de soporte. SIN TOKEN: la autorización explícita de la persona (24 h, revocable) es el permiso.
-- estado: abierto (esperando admin) → en_atencion (un admin lo tomó) → resuelto | cancelado (por la persona).
-- Al revocar, resolver o cancelar, la base cierra sola cualquier sesión técnica abierta.
CREATE TABLE soporte_caso (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 folio varchar(11) GENERATED ALWAYS AS ('CS-' || upper(substr(replace(id::text,'-',''),1,8))) STORED UNIQUE,
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 dispositivo_id bigint NOT NULL REFERENCES dispositivo(id),
 solicitante_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 incidente varchar(10) NOT NULL,
 nota varchar(500) NOT NULL DEFAULT '',
 autodiagnostico_id uuid NULL REFERENCES autodiagnostico(id),
 consentimiento boolean NOT NULL,
 autorizada_en timestamptz NOT NULL DEFAULT now(),
 autorizacion_vence_en timestamptz NOT NULL DEFAULT now() + interval '24 hours',
 autorizacion_revocada_en timestamptz NULL,
 estado varchar(12) NOT NULL DEFAULT 'abierto',
 atendido_por_id bigint NULL REFERENCES cuentas_usuario(id),
 tomado_en timestamptz NULL,
 resultado varchar(14) NULL,
 nota_resolucion varchar(500) NOT NULL DEFAULT '',
 cerrado_en timestamptz NULL,
 creado_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT caso_incidente_valido CHECK (incidente IN ('bomba','humedad','lampara','conexion','otro')),
 CONSTRAINT caso_consentimiento_explicito CHECK (consentimiento),
 CONSTRAINT caso_autorizacion_24h CHECK (autorizacion_vence_en > autorizada_en AND autorizacion_vence_en <= autorizada_en + interval '24 hours'),
 CONSTRAINT caso_revocacion_coherente CHECK (autorizacion_revocada_en IS NULL OR autorizacion_revocada_en >= autorizada_en),
 CONSTRAINT caso_estado_valido CHECK (estado IN ('abierto','en_atencion','resuelto','cancelado')),
 CONSTRAINT caso_resultado_valido CHECK (resultado IN ('solucionado','sin_falla','sin_respuesta','otro')),
 CONSTRAINT caso_otro_con_nota CHECK (resultado IS DISTINCT FROM 'otro' OR nota_resolucion ~ '\S'),
 CONSTRAINT caso_estado_coherente CHECK (
      (estado='abierto'     AND atendido_por_id IS NULL AND tomado_en IS NULL AND resultado IS NULL AND cerrado_en IS NULL)
   OR (estado='en_atencion' AND atendido_por_id IS NOT NULL AND tomado_en IS NOT NULL AND tomado_en >= creado_en AND resultado IS NULL AND cerrado_en IS NULL)
   OR (estado='resuelto'    AND atendido_por_id IS NOT NULL AND resultado IS NOT NULL AND cerrado_en IS NOT NULL AND cerrado_en >= creado_en AND autorizacion_revocada_en IS NOT NULL)
   OR (estado='cancelado'   AND resultado IS NULL AND cerrado_en IS NOT NULL AND cerrado_en >= creado_en AND autorizacion_revocada_en IS NOT NULL)));
CREATE UNIQUE INDEX caso_uno_activo_por_huerto ON soporte_caso(huerto_id) WHERE estado IN ('abierto','en_atencion');
CREATE INDEX caso_bandeja_idx ON soporte_caso(estado, creado_en DESC);
CREATE INDEX caso_solicitante_idx ON soporte_caso(solicitante_id, creado_en DESC);

-- Sesión técnica: el admin pulsa «Conectar». Solo con autorización vigente. Una abierta por admin y por caso.
-- motivo_cierre: manual, revocada (la persona revocó), caso_cerrado, vencida (24 h), cierre_sesion (logout).
CREATE TABLE soporte_sesion (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 caso_id uuid NOT NULL REFERENCES soporte_caso(id),
 administrador_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 iniciada_en timestamptz NOT NULL DEFAULT now(),
 cerrada_en timestamptz NULL,
 motivo_cierre varchar(14) NOT NULL DEFAULT '',
 CONSTRAINT sesion_cierre_coherente CHECK ((cerrada_en IS NULL AND motivo_cierre='')
   OR (cerrada_en IS NOT NULL AND cerrada_en >= iniciada_en AND motivo_cierre IN ('manual','revocada','caso_cerrado','vencida','cierre_sesion'))));
CREATE UNIQUE INDEX sesion_una_abierta_por_admin ON soporte_sesion(administrador_id) WHERE cerrada_en IS NULL;
CREATE UNIQUE INDEX sesion_una_abierta_por_caso ON soporte_sesion(caso_id) WHERE cerrada_en IS NULL;
ALTER TABLE comando ADD CONSTRAINT comando_sesion_fk FOREIGN KEY (sesion_id) REFERENCES soporte_sesion(id);


-- =====================================================================================================
-- 9. COMUNICACIÓN: NOTIFICACIONES, IA, BUZÓN, CORREOS Y VENTAS
-- =====================================================================================================

-- Centro de avisos de cada cuenta (pantalla «Avisos»), para usuarios y administradores.
-- origen: dispositivo (alertas del equipo) · ia · legal (nueva versión) · soporte · vinculacion · sistema.
-- Solo se marca como leída o resuelta (una vez). enlace: ruta interna de la página (#avisos, #soporte…).
CREATE TABLE notificacion (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 destinatario_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 origen varchar(12) NOT NULL,
 severidad varchar(12) NOT NULL DEFAULT 'informacion',
 titulo varchar(120) NOT NULL,
 texto varchar(1000) NOT NULL DEFAULT '',
 huerto_id bigint NULL REFERENCES huerto(id),
 enlace varchar(120) NOT NULL DEFAULT '',
 creada_en timestamptz NOT NULL DEFAULT now(),
 leida_en timestamptz NULL,
 resuelta_en timestamptz NULL,
 CONSTRAINT notif_origen_valido CHECK (origen IN ('dispositivo','ia','legal','soporte','vinculacion','sistema')),
 CONSTRAINT notif_severidad_valida CHECK (severidad IN ('informacion','advertencia','critico')),
 CONSTRAINT notif_titulo_significativo CHECK (titulo ~ '\S'),
 CONSTRAINT notif_enlace_interno CHECK (enlace = '' OR enlace ~ '^#[A-Za-z0-9/_-]{1,119}$'),
 CONSTRAINT notif_fechas CHECK ((leida_en IS NULL OR leida_en >= creada_en) AND (resuelta_en IS NULL OR resuelta_en >= creada_en)));
CREATE INDEX notif_bandeja_idx ON notificacion(destinatario_id, creada_en DESC);
CREATE INDEX notif_no_leidas_idx ON notificacion(destinatario_id) WHERE leida_en IS NULL;

-- Ficha de IA de «Mi huerto». La escribe el servicio de IA en Google Cloud. Historial de 30 días.
CREATE TABLE ia_resumen (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 huerto_id bigint NOT NULL REFERENCES huerto(id),
 contenido varchar(2000) NOT NULL,
 modelo varchar(64) NOT NULL,
 datos_hasta timestamptz NOT NULL,
 generado_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT ia_contenido_significativo CHECK (contenido ~ '\S'),
 CONSTRAINT ia_modelo_significativo CHECK (modelo ~ '\S'),
 CONSTRAINT ia_datos_previos CHECK (datos_hasta <= generado_en + interval '5 minutes'));
CREATE INDEX ia_huerto_fecha_idx ON ia_resumen(huerto_id, generado_en DESC);

-- Mensajes del formulario público «Consíguelo». estado: nueva → atendida | archivada; atendida ↔ archivada.
-- A los 365 días de atendida/archivada, la tarea periódica borra nombre, correo y mensaje (anonimizada_en).
CREATE TABLE consulta_producto (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 folio varchar(11) GENERATED ALWAYS AS ('CP-' || upper(substr(replace(id::text,'-',''),1,8))) STORED UNIQUE,
 recibida_en timestamptz NOT NULL DEFAULT now(),
 nombre varchar(100) NOT NULL DEFAULT '',
 correo varchar(254) NOT NULL,
 mensaje varchar(2000) NOT NULL,
 huella char(64) NOT NULL,
 estado varchar(10) NOT NULL DEFAULT 'nueva',
 atendida_en timestamptz NULL,
 atendida_por_id bigint NULL REFERENCES cuentas_usuario(id),
 anonimizada_en timestamptz NULL,
 CONSTRAINT consulta_correo_significativo CHECK (correo ~ '\S'),
 CONSTRAINT consulta_mensaje_significativo CHECK (mensaje ~ '\S'),
 CONSTRAINT consulta_huella_valida CHECK (huella ~ '^[0-9a-f]{64}$'),
 CONSTRAINT consulta_estado_valido CHECK (estado IN ('nueva','atendida','archivada')),
 CONSTRAINT consulta_atencion_coherente CHECK (
      (estado='nueva' AND atendida_en IS NULL AND atendida_por_id IS NULL AND anonimizada_en IS NULL)
   OR (estado IN ('atendida','archivada') AND atendida_en IS NOT NULL AND atendida_por_id IS NOT NULL)));
CREATE INDEX consulta_estado_fecha_idx ON consulta_producto(estado, recibida_en DESC);
CREATE INDEX consulta_huella_idx ON consulta_producto(huella, recibida_en DESC);

-- Cola de correos automáticos al buzón de soporte (caso nuevo, consulta nueva). Hasta 5 intentos.
-- El correo de soporte NO está aquí: está en la configuración del servidor (.env).
CREATE TABLE correo_pendiente (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 tipo varchar(16) NOT NULL,
 caso_id uuid NULL REFERENCES soporte_caso(id),
 consulta_id uuid NULL REFERENCES consulta_producto(id),
 estado varchar(14) NOT NULL DEFAULT 'pendiente',
 intentos smallint NOT NULL DEFAULT 0,
 creado_en timestamptz NOT NULL DEFAULT now(),
 ultimo_intento_en timestamptz NULL,
 aceptado_en timestamptz NULL,
 CONSTRAINT correo_tipo_valido CHECK (tipo IN ('caso_nuevo','consulta_nueva')),
 CONSTRAINT correo_referencia_coherente CHECK ((tipo='caso_nuevo' AND caso_id IS NOT NULL AND consulta_id IS NULL)
                                            OR (tipo='consulta_nueva' AND consulta_id IS NOT NULL AND caso_id IS NULL)),
 CONSTRAINT correo_estado_valido CHECK (estado IN ('pendiente','aceptado_smtp','fallido')),
 CONSTRAINT correo_intentos_limite CHECK (intentos BETWEEN 0 AND 5),
 CONSTRAINT correo_aceptacion_coherente CHECK ((estado='aceptado_smtp') = (aceptado_en IS NOT NULL)));
CREATE UNIQUE INDEX correo_un_aviso_por_caso ON correo_pendiente(caso_id) WHERE caso_id IS NOT NULL;
CREATE UNIQUE INDEX correo_un_aviso_por_consulta ON correo_pendiente(consulta_id) WHERE consulta_id IS NOT NULL;
CREATE INDEX correo_pendientes_idx ON correo_pendiente(estado, creado_en) WHERE estado <> 'aceptado_smtp';

-- Ventas de equipos. Solo una venta vigente por equipo. Municipio de Yucatán, sin dirección.
-- Pago: importe recibido declarado (0…precio) y referencia textual; estado_pago lo calcula la base
-- (pendiente · parcial · completo). Entrega: a domicilio o recogida acordada, con fecha prevista y real.
CREATE TABLE venta (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 dispositivo_id bigint NOT NULL REFERENCES dispositivo(id),
 comprador_nombre varchar(120) NOT NULL,
 comprador_correo varchar(254) NOT NULL,
 comprador_usuario_id bigint NULL REFERENCES cuentas_usuario(id),
 municipio varchar(60) NOT NULL,
 precio_mxn numeric(10,2) NOT NULL,
 importe_recibido_mxn numeric(10,2) NOT NULL DEFAULT 0,
 referencia_pago varchar(120) NOT NULL DEFAULT '',
 estado_pago varchar(10) GENERATED ALWAYS AS (CASE WHEN importe_recibido_mxn = 0 THEN 'pendiente'
   WHEN importe_recibido_mxn < precio_mxn THEN 'parcial' ELSE 'completo' END) STORED,
 modalidad_entrega varchar(10) NOT NULL,
 vendida_en date NOT NULL,
 entrega_prevista_en date NULL,
 entregada_en date NULL,
 estado varchar(10) NOT NULL DEFAULT 'vigente',
 cancelada_en timestamptz NULL,
 nota varchar(500) NOT NULL DEFAULT '',
 registrada_por_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 registrada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT venta_nombre_significativo CHECK (comprador_nombre ~ '\S'),
 CONSTRAINT venta_correo_valido CHECK (comprador_correo ~ '^[^@\s]+@[^@\s]+$'),
 CONSTRAINT venta_municipio_significativo CHECK (municipio ~ '\S'),
 CONSTRAINT venta_precio_valido CHECK (precio_mxn > 0 AND precio_mxn <= 99999999.99),
 CONSTRAINT venta_importe_valido CHECK (importe_recibido_mxn >= 0 AND importe_recibido_mxn <= precio_mxn),
 CONSTRAINT venta_referencia_una_linea CHECK (referencia_pago !~ '[\r\n]'),
 CONSTRAINT venta_modalidad_valida CHECK (modalidad_entrega IN ('domicilio','recogida')),
 CONSTRAINT venta_entrega_coherente CHECK ((entregada_en IS NULL OR entregada_en >= vendida_en)
                                        AND (entrega_prevista_en IS NULL OR entrega_prevista_en >= vendida_en)),
 CONSTRAINT venta_estado_valido CHECK ((estado='vigente' AND cancelada_en IS NULL) OR (estado='cancelada' AND cancelada_en IS NOT NULL)));
CREATE UNIQUE INDEX venta_vigente_por_equipo ON venta(dispositivo_id) WHERE estado='vigente';
CREATE INDEX venta_fecha_idx ON venta(vendida_en DESC);


-- =====================================================================================================
-- 10. LEGAL Y PRIVACIDAD
-- =====================================================================================================

-- Textos legales con versiones. El TEXTO COMPLETO vive aquí (antes era un HTML en el servidor).
-- borrador: editable y borrable · publicada: no cambia nunca. La vigente de cada tipo es la última publicada.
-- Publicar términos o aviso obliga a todas las cuentas a aceptarlos de nuevo al entrar (y les avisa).
CREATE TABLE documento_legal (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 tipo varchar(18) NOT NULL,
 version varchar(20) NOT NULL,
 titulo varchar(120) NOT NULL,
 contenido text NOT NULL,
 contenido_sha256 char(64) NOT NULL,
 estado varchar(10) NOT NULL DEFAULT 'borrador',
 creado_por_id bigint NULL REFERENCES cuentas_usuario(id),
 creado_en timestamptz NOT NULL DEFAULT now(),
 actualizado_en timestamptz NOT NULL DEFAULT now(),
 publicado_por_id bigint NULL REFERENCES cuentas_usuario(id),
 publicado_en timestamptz NULL,
 CONSTRAINT legal_version_unica UNIQUE (tipo, version),
 CONSTRAINT legal_tipo_valido CHECK (tipo IN ('terminos','aviso_privacidad','politica_cookies')),
 CONSTRAINT legal_version_formato CHECK (version ~ '^[0-9]{1,3}\.[0-9]{1,3}(\.[0-9]{1,3})?$'),
 CONSTRAINT legal_titulo_significativo CHECK (titulo ~ '\S'),
 CONSTRAINT legal_contenido_significativo CHECK (contenido ~ '\S' AND length(contenido) <= 200000),
 CONSTRAINT legal_hash_hex CHECK (contenido_sha256 ~ '^[0-9a-f]{64}$'),
 CONSTRAINT legal_estado_valido CHECK (estado IN ('borrador','publicada')),
 CONSTRAINT legal_publicacion_coherente CHECK ((estado='borrador') = (publicado_en IS NULL)));
CREATE INDEX legal_vigente_idx ON documento_legal(tipo, publicado_en DESC) WHERE estado='publicada';

-- Finalidades opcionales. Hoy solo «estadisticas_internas_navegacion».
CREATE TABLE privacidad_finalidad (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 codigo varchar(64) NOT NULL UNIQUE,
 descripcion varchar(255) NOT NULL,
 creada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT priv_finalidad_codigo_valido CHECK (codigo ~ '^[a-z][a-z0-9_]{0,63}$'),
 CONSTRAINT priv_finalidad_descripcion CHECK (descripcion ~ '\S'));

-- «Sujeto» seudónimo: una CUENTA (términos y aviso) o un NAVEGADOR (cookies; la cookie
-- chilito_preferencia guarda su id firmado). Un navegador queda ligado a la cuenta que tenía sesión.
CREATE TABLE privacidad_sujeto (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 ambito varchar(9) NOT NULL,
 usuario_id bigint NULL REFERENCES cuentas_usuario(id),
 creado_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT priv_sujeto_ambito_valido CHECK (ambito IN ('cuenta','navegador')),
 CONSTRAINT priv_sujeto_cuenta_con_usuario CHECK (ambito <> 'cuenta' OR usuario_id IS NOT NULL));
CREATE UNIQUE INDEX priv_sujeto_cuenta_unica ON privacidad_sujeto(usuario_id) WHERE ambito='cuenta';
CREATE INDEX priv_sujeto_usuario_idx ON privacidad_sujeto(usuario_id) WHERE usuario_id IS NOT NULL;

-- BITÁCORA DE CONSENTIMIENTOS. Una fila por cada decisión; nunca se modifica ni se borra.
--   aceptacion_terminos / lectura_aviso: de una cuenta, decision = true, documento del tipo que corresponde.
--   cookies: de un navegador, con finalidad, decision true/false y la política de cookies vigente.
-- usuario_id: cuenta con sesión en ese momento (para mostrar su correo). ip_recortada: IPv4 con el último
-- bloque en 0 o IPv6 recortada a /48. navegador: resumen («Chrome 130 · Android»), no el user-agent entero.
CREATE TABLE privacidad_decision (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 sujeto_id uuid NOT NULL REFERENCES privacidad_sujeto(id),
 acto varchar(20) NOT NULL,
 decision boolean NOT NULL,
 documento_id uuid NOT NULL REFERENCES documento_legal(id),
 finalidad_id uuid NULL REFERENCES privacidad_finalidad(id),
 usuario_id bigint NULL REFERENCES cuentas_usuario(id),
 ip_recortada varchar(45) NOT NULL DEFAULT '',
 navegador varchar(120) NOT NULL DEFAULT '',
 registrada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT priv_decision_acto_valido CHECK (acto IN ('aceptacion_terminos','lectura_aviso','cookies')),
 CONSTRAINT priv_decision_coherente CHECK (
      (acto IN ('aceptacion_terminos','lectura_aviso') AND decision AND finalidad_id IS NULL AND usuario_id IS NOT NULL)
   OR (acto='cookies' AND finalidad_id IS NOT NULL)),
 CONSTRAINT priv_decision_ip_recortada CHECK (ip_recortada = '' OR ip_recortada ~ '^([0-9]{1,3}\.){3}0$' OR ip_recortada ~ '^[0-9a-f:]+::$'));
CREATE INDEX priv_decision_bitacora_idx ON privacidad_decision(registrada_en DESC);
CREATE INDEX priv_decision_sujeto_idx ON privacidad_decision(sujeto_id, acto, registrada_en DESC);
CREATE INDEX priv_decision_usuario_idx ON privacidad_decision(usuario_id, registrada_en DESC) WHERE usuario_id IS NOT NULL;

-- Decisión VIGENTE de cada navegador para cada finalidad (apunta a la última de la bitácora).
CREATE TABLE privacidad_preferencia (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 sujeto_id uuid NOT NULL REFERENCES privacidad_sujeto(id),
 finalidad_id uuid NOT NULL REFERENCES privacidad_finalidad(id),
 decision_id uuid NOT NULL REFERENCES privacidad_decision(id),
 actualizada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT priv_preferencia_unica UNIQUE (sujeto_id, finalidad_id));

-- Visitas por día y sección. Solo totales, sin identidad; solo si el navegador aceptó estadísticas.
CREATE TABLE conteo_navegacion (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 dia date NOT NULL,
 seccion varchar(16) NOT NULL,
 visitas bigint NOT NULL DEFAULT 0,
 CONSTRAINT conteo_dia_seccion_unico UNIQUE (dia, seccion),
 CONSTRAINT conteo_visitas_positivas CHECK (visitas >= 0),
 CONSTRAINT conteo_seccion_valida CHECK (seccion IN ('inicio','proyecto','prototipo','funcionamiento','huerto',
   'panel_tecnico','mantenimiento','soporte','avisos','cuenta','privacidad')));


-- =====================================================================================================
-- 11. ADMINISTRACIÓN: HISTORIAL DE CAPACIDADES, AUDITORÍA E IDEMPOTENCIA
-- =====================================================================================================

-- Cada capacidad dada o quitada, para siempre. La llena un trigger: nadie puede saltársela.
-- realizada_por_id NULL = se hizo desde pgAdmin (chilito_pkg_owner).
CREATE TABLE capacidad_historial (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 usuario_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 capacidad varchar(64) NOT NULL,
 accion varchar(10) NOT NULL,
 realizada_por_id bigint NULL REFERENCES cuentas_usuario(id),
 motivo varchar(300) NOT NULL DEFAULT '',
 realizada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT cap_hist_accion_valida CHECK (accion IN ('concedida','retirada')));
CREATE INDEX cap_hist_usuario_idx ON capacidad_historial(usuario_id, realizada_en DESC);
CREATE INDEX cap_hist_fecha_idx ON capacidad_historial(realizada_en DESC);

-- Auditoría: quién hizo qué, sobre qué y cuándo. Sin contraseñas, códigos ni textos libres de personas.
-- accion: verbo_objeto en minúsculas (catálogo en la guía). detalle: datos técnicos cortos (jsonb objeto).
CREATE TABLE auditoria (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 actor_id bigint NULL REFERENCES cuentas_usuario(id),
 accion varchar(48) NOT NULL,
 entidad varchar(40) NOT NULL DEFAULT '',
 entidad_id varchar(64) NOT NULL DEFAULT '',
 huerto_id bigint NULL REFERENCES huerto(id),
 resultado varchar(10) NOT NULL DEFAULT 'exito',
 detalle jsonb NOT NULL DEFAULT '{}'::jsonb,
 ip_recortada varchar(45) NOT NULL DEFAULT '',
 creada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT auditoria_accion_formato CHECK (accion ~ '^[a-z]+(_[a-z]+)*$'),
 CONSTRAINT auditoria_resultado_valido CHECK (resultado IN ('exito','rechazado')),
 CONSTRAINT auditoria_detalle_objeto CHECK (jsonb_typeof(detalle)='object' AND length(detalle::text) <= 2000),
 CONSTRAINT auditoria_ip_recortada CHECK (ip_recortada = '' OR ip_recortada ~ '^([0-9]{1,3}\.){3}0$' OR ip_recortada ~ '^[0-9a-f:]+::$'));
CREATE INDEX auditoria_actor_idx ON auditoria(actor_id, creada_en DESC);
CREATE INDEX auditoria_entidad_idx ON auditoria(entidad, entidad_id);
CREATE INDEX auditoria_huerto_idx ON auditoria(huerto_id, creada_en DESC) WHERE huerto_id IS NOT NULL;
CREATE INDEX auditoria_fecha_idx ON auditoria(creada_en DESC);

-- Recibos de idempotencia: si el navegador reintenta una escritura con la misma Idempotency-Key, se
-- devuelve el mismo resultado. Se limpian a los 7 días.
CREATE TABLE web_idempotencia (
 id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
 clave uuid NOT NULL,
 ruta varchar(240) NOT NULL,
 huella char(64) NOT NULL,
 respuesta jsonb NOT NULL,
 creada_en timestamptz NOT NULL DEFAULT now(),
 actor_id bigint NOT NULL REFERENCES cuentas_usuario(id),
 CONSTRAINT web_idempotencia_actor_clave UNIQUE (actor_id, clave));
CREATE INDEX web_idempotencia_fecha_idx ON web_idempotencia(creada_en);

-- =====================================================================================================
-- 12. REGLAS EN LA BASE (FUNCIONES DE CONSULTA Y TRIGGERS)
--     Segunda barrera: aunque la aplicación tuviera un error, la base rechaza el cambio (código 23514).
-- =====================================================================================================

-- 12.0 Consultas de apoyo ------------------------------------------------------------------------------
-- Se ejecutan con permisos del propietario (SECURITY DEFINER) para que los triggers puedan comprobar
-- datos aunque quien escribe (la página o el servicio IoT) no pueda leer esas tablas. Solo devuelven sí/no
-- o un id; no exponen datos.

-- Las 10 capacidades de administración.
CREATE FUNCTION public.chilito_capacidades() RETURNS text[]
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT ARRAY['ver_flota','atender_soporte','gestionar_mantenimientos','atender_consultas',
              'gestionar_dispositivos','gestionar_ventas','gestionar_guias','gestionar_legales',
              'ver_consentimientos','gestionar_administradores']
$$;

CREATE FUNCTION public.chilito_cuenta_activa(u bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT coalesce((SELECT is_active AND anonimizada_en IS NULL FROM public.cuentas_usuario WHERE id=u), false)
$$;

-- ¿La cuenta (activa) tiene esa capacidad?
CREATE FUNCTION public.chilito_tiene_capacidad(u bigint, capacidad text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT public.chilito_cuenta_activa(u) AND EXISTS(
  SELECT 1 FROM public.cuentas_usuario_user_permissions up
  JOIN public.auth_permission p ON p.id=up.permission_id
  JOIN public.django_content_type c ON c.id=p.content_type_id AND c.app_label='cuentas'
  WHERE up.usuario_id=u AND p.codename=capacidad)
$$;

-- ¿Es administradora (tiene al menos una capacidad)?
CREATE FUNCTION public.chilito_es_admin(u bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT public.chilito_cuenta_activa(u) AND EXISTS(
  SELECT 1 FROM public.cuentas_usuario_user_permissions up
  JOIN public.auth_permission p ON p.id=up.permission_id
  JOIN public.django_content_type c ON c.id=p.content_type_id AND c.app_label='cuentas'
  WHERE up.usuario_id=u AND p.codename = ANY(public.chilito_capacidades()))
$$;

-- Dueño de un huerto ACTIVO (NULL si no existe o está archivado).
CREATE FUNCTION public.chilito_dueno_huerto(h bigint) RETURNS bigint
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT propietario_id FROM public.huerto WHERE id=h AND estado='activo'
$$;

-- Equipo vinculado a un huerto (NULL si no tiene).
CREATE FUNCTION public.chilito_equipo_de_huerto(h bigint) RETURNS bigint
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT id FROM public.dispositivo WHERE huerto_id=h AND estado='vinculado'
$$;

-- Actor obligatorio para cambios hechos por la aplicación.
CREATE FUNCTION public.chilito_actor_requerido() RETURNS bigint
LANGUAGE plpgsql STABLE AS $$
DECLARE a bigint := public.chilito_actor();
BEGIN
 IF a IS NULL THEN
  RAISE EXCEPTION 'Falta el actor: la aplicación debe fijar chilito.actor_id en la transacción' USING ERRCODE='23514';
 END IF;
 IF NOT public.chilito_cuenta_activa(a) THEN
  RAISE EXCEPTION 'El actor no es una cuenta activa' USING ERRCODE='23514';
 END IF;
 RETURN a;
END $$;

-- Comprueba que el actor de la aplicación sea esa cuenta concreta.
CREATE FUNCTION public.chilito_exigir_actor(esperado bigint) RETURNS void
LANGUAGE plpgsql STABLE AS $$
BEGIN
 IF public.chilito_es_aplicacion() AND public.chilito_actor_requerido() IS DISTINCT FROM esperado THEN
  RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
 END IF;
END $$;

-- Comprueba que el actor de la aplicación tenga una capacidad.
CREATE FUNCTION public.chilito_exigir_capacidad(capacidad text) RETURNS bigint
LANGUAGE plpgsql STABLE AS $$
DECLARE a bigint;
BEGIN
 IF NOT public.chilito_es_aplicacion() THEN RETURN public.chilito_actor(); END IF;
 a := public.chilito_actor_requerido();
 IF NOT public.chilito_tiene_capacidad(a, capacidad) THEN
  RAISE EXCEPTION 'Se requiere la capacidad %', capacidad USING ERRCODE='23514';
 END IF;
 RETURN a;
END $$;

-- Versión legal comparable: '1.10' > '1.9'.
CREATE FUNCTION public.chilito_version_num(v text) RETURNS integer[]
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$ SELECT string_to_array(v,'.')::integer[] $$;

-- Documento legal vigente de un tipo: el último publicado.
CREATE FUNCTION public.chilito_documento_vigente(tipo_doc text) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT id FROM public.documento_legal WHERE tipo=tipo_doc AND estado='publicada'
 ORDER BY publicado_en DESC, public.chilito_version_num(version) DESC LIMIT 1
$$;

-- Hoy en Mérida.
CREATE FUNCTION public.chilito_hoy() RETURNS date
LANGUAGE sql STABLE AS $$ SELECT (now() AT TIME ZONE 'America/Merida')::date $$;


-- 12.1 Historiales que no se modifican -----------------------------------------------------------------
-- Argumentos opcionales: columna de fecha e intervalo. Solo el propietario (tareas periódicas) puede borrar
-- filas más antiguas que ese intervalo. 'propietario' = el propietario puede borrar (borrado en cascada).
CREATE FUNCTION public.chilito_inmutable() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' AND public.chilito_es_propietario_bd() AND TG_NARGS >= 1 THEN
  IF TG_ARGV[0]='propietario' THEN RETURN OLD; END IF;
  IF (to_jsonb(OLD)->>TG_ARGV[0])::timestamptz < now() - TG_ARGV[1]::interval THEN RETURN OLD; END IF;
 END IF;
 RAISE EXCEPTION 'Historial inmutable (%): no se permite modificar ni borrar', TG_TABLE_NAME USING ERRCODE='23514';
END $$;

CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON huerto_planta_etapa FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON dispositivo_evento FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON medicion FOR EACH ROW EXECUTE FUNCTION chilito_inmutable('medida_en','90 days');
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON medicion_planta FOR EACH ROW EXECUTE FUNCTION chilito_inmutable('propietario');
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON actuacion FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON autodiagnostico_revision FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON cuidado FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON cuidado_revision FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON ia_resumen FOR EACH ROW EXECUTE FUNCTION chilito_inmutable('generado_en','30 days');
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON privacidad_decision FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON privacidad_finalidad FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON capacidad_historial FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON auditoria FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON web_idempotencia FOR EACH ROW EXECUTE FUNCTION chilito_inmutable('creada_en','7 days');


-- 12.2 Cuentas ----------------------------------------------------------------------------------------
-- Las cuentas no se borran: se anonimizan. La aplicación no crea cuentas inactivas ni anonimizadas.
CREATE FUNCTION public.chilito_cuenta_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'Las cuentas no se borran: se anonimizan' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' THEN
  IF public.chilito_es_aplicacion() AND (NOT NEW.is_active OR NEW.anonimizada_en IS NOT NULL
     OR NEW.anonimizacion_solicitada_en IS NOT NULL) THEN
   RAISE EXCEPTION 'La aplicación solo crea cuentas activas' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF OLD.anonimizada_en IS NOT NULL AND public.chilito_es_aplicacion() THEN
  RAISE EXCEPTION 'Una cuenta anonimizada no cambia' USING ERRCODE='23514';
 END IF;
 IF NEW.date_joined IS DISTINCT FROM OLD.date_joined OR NEW.id IS DISTINCT FROM OLD.id THEN
  RAISE EXCEPTION 'La identidad de la cuenta no cambia' USING ERRCODE='23514';
 END IF;
 IF OLD.anonimizada_en IS NOT NULL AND NEW.anonimizada_en IS NULL THEN
  RAISE EXCEPTION 'La anonimización no tiene vuelta atrás' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER cuenta_reglas BEFORE INSERT OR UPDATE OR DELETE ON cuentas_usuario
 FOR EACH ROW EXECUTE FUNCTION chilito_cuenta_reglas();

-- REGISTRO: al confirmar la transacción, la cuenta nueva debe haber aceptado los términos y el aviso de
-- privacidad VIGENTES. Sin las dos casillas no existe la cuenta.
CREATE FUNCTION public.chilito_registro_exige_aceptacion() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE t uuid := public.chilito_documento_vigente('terminos');
        a uuid := public.chilito_documento_vigente('aviso_privacidad');
BEGIN
 IF t IS NULL OR a IS NULL THEN
  RAISE EXCEPTION 'No hay términos y aviso de privacidad publicados: publícalos antes de abrir el registro' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.privacidad_decision d WHERE d.usuario_id=NEW.id AND d.acto='aceptacion_terminos' AND d.documento_id=t)
 OR NOT EXISTS(SELECT 1 FROM public.privacidad_decision d WHERE d.usuario_id=NEW.id AND d.acto='lectura_aviso' AND d.documento_id=a) THEN
  RAISE EXCEPTION 'Para crear la cuenta hay que aceptar los términos y el aviso de privacidad vigentes' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER registro_exige_aceptacion AFTER INSERT ON cuentas_usuario
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION chilito_registro_exige_aceptacion();

-- Un segundo factor no cambia de dueño, tipo ni fecha de alta.
CREATE FUNCTION public.chilito_proteger_mfa() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.user_id IS DISTINCT FROM OLD.user_id
    OR NEW.type IS DISTINCT FROM OLD.type OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
  RAISE EXCEPTION 'La identidad de un autenticador no puede reasignarse' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mfa_estable BEFORE UPDATE ON mfa_authenticator FOR EACH ROW EXECUTE FUNCTION chilito_proteger_mfa();


-- 12.3 Capacidades de administración -------------------------------------------------------------------
-- · La aplicación solo puede tocar las 10 capacidades, nunca otros permisos de Django.
-- · Desde el panel: el actor debe tener «gestionar_administradores», no puede cambiarse a sí mismo y no
--   puede dar ni quitar «gestionar_administradores» (eso solo desde pgAdmin).
-- · Siempre debe quedar al menos un super administrador activo.
-- · Cada alta o baja se copia en capacidad_historial con quién, cuándo y motivo (chilito.motivo).
CREATE FUNCTION public.chilito_capacidad_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE fila public.cuentas_usuario_user_permissions%ROWTYPE; cod text; app text; a bigint;
BEGIN
 IF TG_OP='UPDATE' THEN
  RAISE EXCEPTION 'Una capacidad no se modifica: se retira y se concede' USING ERRCODE='23514';
 END IF;
 fila := CASE WHEN TG_OP='INSERT' THEN NEW ELSE OLD END;
 SELECT p.codename, c.app_label INTO cod, app FROM auth_permission p JOIN django_content_type c ON c.id=p.content_type_id
  WHERE p.id=fila.permission_id;
 -- Dentro de una función SECURITY DEFINER current_user es el propietario: se mira quién llamó de verdad.
 IF session_user <> 'chilito_pkg_owner' THEN
  IF app IS DISTINCT FROM 'cuentas' OR NOT cod = ANY(chilito_capacidades()) THEN
   RAISE EXCEPTION 'La aplicación solo gestiona las capacidades de El Chilito' USING ERRCODE='23514';
  END IF;
  a := chilito_actor();
  IF a IS NULL OR NOT chilito_tiene_capacidad(a, 'gestionar_administradores') THEN
   RAISE EXCEPTION 'Solo un super administrador puede dar o quitar capacidades' USING ERRCODE='23514';
  END IF;
  IF a = fila.usuario_id THEN
   RAISE EXCEPTION 'Nadie puede cambiar sus propias capacidades' USING ERRCODE='23514';
  END IF;
  IF cod = 'gestionar_administradores' THEN
   RAISE EXCEPTION 'La capacidad de super administrador solo se da o quita desde pgAdmin' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='INSERT' AND app='cuentas' AND cod = ANY(chilito_capacidades()) THEN
  IF NOT chilito_cuenta_activa(fila.usuario_id) THEN
   RAISE EXCEPTION 'Solo se dan capacidades a cuentas activas' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM account_emailaddress e JOIN cuentas_usuario u ON u.id=e.user_id
                WHERE e.user_id=fila.usuario_id AND e.verified AND lower(e.email)=lower(u.email)) THEN
   RAISE EXCEPTION 'La cuenta debe tener el correo verificado' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='DELETE' AND cod='gestionar_administradores' AND NOT EXISTS(
   SELECT 1 FROM cuentas_usuario_user_permissions up WHERE up.permission_id=fila.permission_id
     AND up.usuario_id<>fila.usuario_id AND chilito_cuenta_activa(up.usuario_id)) THEN
  RAISE EXCEPTION 'Debe quedar al menos un super administrador activo' USING ERRCODE='23514';
 END IF;
 IF app='cuentas' AND cod = ANY(chilito_capacidades()) THEN
  INSERT INTO capacidad_historial(usuario_id, capacidad, accion, realizada_por_id, motivo)
  VALUES (fila.usuario_id, cod, CASE WHEN TG_OP='INSERT' THEN 'concedida' ELSE 'retirada' END,
          chilito_actor(), left(coalesce(current_setting('chilito.motivo', true),''),300));
 END IF;
 RETURN fila;
END $$;
CREATE TRIGGER capacidad_reglas BEFORE INSERT OR UPDATE OR DELETE ON cuentas_usuario_user_permissions
 FOR EACH ROW EXECUTE FUNCTION chilito_capacidad_reglas();


-- 12.4 Huertos y plantas ------------------------------------------------------------------------------
CREATE FUNCTION public.chilito_huerto_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE activos integer; sin_equipo integer; app boolean := (session_user='chilito_pkg_runtime');
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Los huertos no se borran: se archivan' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF app AND chilito_actor() IS DISTINCT FROM NEW.propietario_id THEN
   RAISE EXCEPTION 'Cada persona crea sus propios huertos' USING ERRCODE='23514';
  END IF;
  IF NOT chilito_cuenta_activa(NEW.propietario_id) THEN
   RAISE EXCEPTION 'La cuenta no está activa' USING ERRCODE='23514';
  END IF;
  IF NEW.estado<>'activo' THEN RAISE EXCEPTION 'Un huerto nace activo' USING ERRCODE='23514'; END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('chilito_huertos_' || NEW.propietario_id, 0));
  SELECT count(*), count(*) FILTER (WHERE NOT EXISTS(SELECT 1 FROM dispositivo d WHERE d.huerto_id=h.id))
   INTO activos, sin_equipo FROM huerto h WHERE h.propietario_id=NEW.propietario_id AND h.estado='activo';
  IF activos >= 3 THEN RAISE EXCEPTION 'Máximo 3 huertos activos por cuenta' USING ERRCODE='23514'; END IF;
  IF sin_equipo >= 1 THEN
   RAISE EXCEPTION 'Ya tienes un huerto sin equipo: vincúlalo antes de crear otro' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF NEW.id<>OLD.id OR NEW.propietario_id<>OLD.propietario_id OR NEW.creado_en<>OLD.creado_en THEN
  RAISE EXCEPTION 'El dueño y la identidad del huerto no cambian' USING ERRCODE='23514';
 END IF;
 IF app THEN PERFORM chilito_exigir_actor(OLD.propietario_id); END IF;
 IF OLD.estado='archivado' AND (NEW.estado<>'archivado' OR NEW.nombre<>OLD.nombre) THEN
  RAISE EXCEPTION 'Un huerto archivado no cambia' USING ERRCODE='23514';
 END IF;
 IF OLD.estado='activo' AND NEW.estado='archivado' THEN
  IF EXISTS(SELECT 1 FROM dispositivo WHERE huerto_id=OLD.id) THEN
   RAISE EXCEPTION 'Desvincula el equipo antes de archivar el huerto' USING ERRCODE='23514';
  END IF;
  NEW.archivado_en := now();
  UPDATE codigo_vinculacion SET estado='cancelado', cerrado_en=now() WHERE huerto_id=OLD.id AND estado='pendiente';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER huerto_reglas BEFORE INSERT OR UPDATE OR DELETE ON huerto FOR EACH ROW EXECUTE FUNCTION chilito_huerto_reglas();

-- Cada huerto nace con sus 3 plantas: «Planta 1», «Planta 2», «Planta 3».
CREATE FUNCTION public.chilito_crear_plantas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 INSERT INTO huerto_planta(huerto_id, numero, nombre) SELECT NEW.id, n, 'Planta ' || n FROM generate_series(1,3) n;
 RETURN NULL;
END $$;
CREATE TRIGGER crear_plantas AFTER INSERT ON huerto FOR EACH ROW EXECUTE FUNCTION chilito_crear_plantas();

-- Plantas: solo las crea el trigger anterior; no se borran ni cambian de huerto o número. El dueño cambia
-- nombre, fecha de siembra y etapa. Al cambiar de etapa, la fecha se pone sola y queda en el historial.
CREATE FUNCTION public.chilito_planta_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE dueno bigint;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Las plantas no se borran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF pg_trigger_depth() < 2 AND NOT chilito_es_propietario_bd() THEN
   RAISE EXCEPTION 'Las plantas las crea la base al crear el huerto' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF NEW.id<>OLD.id OR NEW.huerto_id<>OLD.huerto_id OR NEW.numero<>OLD.numero THEN
  RAISE EXCEPTION 'La planta no cambia de huerto ni de número' USING ERRCODE='23514';
 END IF;
 dueno := chilito_dueno_huerto(OLD.huerto_id);
 IF dueno IS NULL THEN RAISE EXCEPTION 'El huerto está archivado' USING ERRCODE='23514'; END IF;
 IF chilito_es_aplicacion() THEN PERFORM chilito_exigir_actor(dueno); END IF;
 IF NEW.fecha_siembra > chilito_hoy() THEN
  RAISE EXCEPTION 'La fecha de siembra no puede ser futura' USING ERRCODE='23514';
 END IF;
 IF NEW.etapa IS DISTINCT FROM OLD.etapa THEN
  IF NEW.etapa='sin_sembrar' THEN NEW.etapa_desde := NULL;
  ELSIF NEW.etapa_desde IS NOT DISTINCT FROM OLD.etapa_desde THEN NEW.etapa_desde := chilito_hoy(); END IF;
 END IF;
 IF NEW.etapa_desde > chilito_hoy() THEN
  RAISE EXCEPTION 'La fecha de la etapa no puede ser futura' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER planta_reglas BEFORE INSERT OR UPDATE OR DELETE ON huerto_planta FOR EACH ROW EXECUTE FUNCTION chilito_planta_reglas();

CREATE FUNCTION public.chilito_planta_historial() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 INSERT INTO huerto_planta_etapa(planta_id, etapa, desde, registrada_por_id)
 VALUES (NEW.id, NEW.etapa, coalesce(NEW.etapa_desde, chilito_hoy()), chilito_actor());
 RETURN NULL;
END $$;
CREATE TRIGGER planta_historial AFTER UPDATE OF etapa ON huerto_planta FOR EACH ROW
 WHEN (NEW.etapa IS DISTINCT FROM OLD.etapa) EXECUTE FUNCTION chilito_planta_historial();


-- 12.5 Dispositivos y vinculación ---------------------------------------------------------------------
-- · Alta: solo con «gestionar_dispositivos», nace disponible y sin conexión.
-- · Servicio IoT: solo actualiza conexión, última conexión y firmware.
-- · Página: vincular (solo con un código utilizado en ESTA transacción para ese equipo y huerto),
--   desvincular (dueño del huerto o «gestionar_dispositivos»), retirar y rotar credencial («gestionar_dispositivos»).
-- · Identificador, MAC y alta no cambian. Retirado es definitivo. No se borran.
CREATE FUNCTION public.chilito_dispositivo_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE quien text := session_user; a bigint := chilito_actor();
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Los equipos no se borran: se retiran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF quien='chilito_pkg_iot' THEN RAISE EXCEPTION 'El servicio IoT no da de alta equipos' USING ERRCODE='23514'; END IF;
  IF quien='chilito_pkg_runtime' THEN
   IF a IS NULL OR NOT chilito_tiene_capacidad(a,'gestionar_dispositivos') OR NEW.registrado_por_id IS DISTINCT FROM a THEN
    RAISE EXCEPTION 'Dar de alta equipos requiere «gestionar_dispositivos»' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.estado<>'disponible' OR NEW.conexion<>'nunca' THEN
   RAISE EXCEPTION 'Un equipo nace disponible y sin conexión' USING ERRCODE='23514';
  END IF;
  NEW.registrado_en := now();
  RETURN NEW;
 END IF;
 IF NEW.id<>OLD.id OR NEW.identificador<>OLD.identificador OR NEW.mac<>OLD.mac
    OR NEW.registrado_por_id IS DISTINCT FROM OLD.registrado_por_id OR NEW.registrado_en<>OLD.registrado_en THEN
  RAISE EXCEPTION 'La identidad del equipo no cambia' USING ERRCODE='23514';
 END IF;
 IF OLD.estado='retirado' AND NEW.estado<>'retirado' THEN
  RAISE EXCEPTION 'Un equipo retirado no vuelve' USING ERRCODE='23514';
 END IF;
 IF NEW.ultima_conexion_en < OLD.ultima_conexion_en THEN
  RAISE EXCEPTION 'La última conexión no retrocede' USING ERRCODE='23514';
 END IF;
 IF quien='chilito_pkg_iot' THEN
  IF (NEW.estado, NEW.huerto_id, NEW.vinculado_en, NEW.credencial_hash, NEW.retirado_en)
     IS DISTINCT FROM (OLD.estado, OLD.huerto_id, OLD.vinculado_en, OLD.credencial_hash, OLD.retirado_en) THEN
   RAISE EXCEPTION 'El servicio IoT solo actualiza conexión y firmware' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF quien='chilito_pkg_runtime' THEN
  IF OLD.estado='disponible' AND NEW.estado='vinculado' THEN
   IF NOT EXISTS(SELECT 1 FROM codigo_vinculacion c WHERE c.dispositivo_id=NEW.id AND c.huerto_id=NEW.huerto_id
                 AND c.estado='utilizado' AND c.cerrado_en >= now()) THEN
    RAISE EXCEPTION 'Vincular exige un código utilizado en esta operación' USING ERRCODE='23514';
   END IF;
   NEW.vinculado_en := now();
  ELSIF OLD.estado='vinculado' AND NEW.estado='disponible' THEN
   IF a IS NULL OR NOT (a = chilito_dueno_huerto(OLD.huerto_id) OR chilito_tiene_capacidad(a,'gestionar_dispositivos')) THEN
    RAISE EXCEPTION 'Desvincular lo hace el dueño del huerto o un admin de dispositivos' USING ERRCODE='23514';
   END IF;
  ELSIF NEW.estado<>OLD.estado THEN
   IF NOT (OLD.estado='disponible' AND NEW.estado='retirado') THEN
    RAISE EXCEPTION 'Cambio de estado del equipo no permitido' USING ERRCODE='23514';
   END IF;
   IF a IS NULL OR NOT chilito_tiene_capacidad(a,'gestionar_dispositivos') THEN
    RAISE EXCEPTION 'Retirar equipos requiere «gestionar_dispositivos»' USING ERRCODE='23514';
   END IF;
   NEW.retirado_en := now();
  ELSIF NEW.huerto_id IS DISTINCT FROM OLD.huerto_id THEN
   RAISE EXCEPTION 'Para cambiar de huerto hay que desvincular y volver a vincular' USING ERRCODE='23514';
  END IF;
  IF NEW.credencial_hash<>OLD.credencial_hash AND (a IS NULL OR NOT chilito_tiene_capacidad(a,'gestionar_dispositivos')) THEN
   RAISE EXCEPTION 'Rotar la credencial requiere «gestionar_dispositivos»' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.estado='vinculado' AND NEW.huerto_id IS NOT NULL AND chilito_dueno_huerto(NEW.huerto_id) IS NULL THEN
  RAISE EXCEPTION 'El huerto no existe o está archivado' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER dispositivo_reglas BEFORE INSERT OR UPDATE OR DELETE ON dispositivo FOR EACH ROW EXECUTE FUNCTION chilito_dispositivo_reglas();

-- Cada cambio importante del equipo queda en su historial y, si toca, avisa al dueño.
CREATE FUNCTION public.chilito_dispositivo_historial() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE a bigint := chilito_actor(); dueno bigint;
BEGIN
 IF TG_OP='INSERT' THEN
  INSERT INTO dispositivo_evento(dispositivo_id, tipo, actor_id) VALUES (NEW.id, 'alta', a);
  RETURN NULL;
 END IF;
 IF OLD.estado<>'vinculado' AND NEW.estado='vinculado' THEN
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, actor_id) VALUES (NEW.id, NEW.huerto_id, 'vinculado', a);
  dueno := chilito_dueno_huerto(NEW.huerto_id);
  INSERT INTO notificacion(destinatario_id, origen, titulo, texto, huerto_id, enlace)
  VALUES (dueno, 'vinculacion', 'Tu equipo quedó vinculado',
          'El equipo ' || NEW.identificador || ' ya está conectado a tu huerto.', NEW.huerto_id, '#huerto');
 ELSIF OLD.estado='vinculado' AND NEW.estado<>'vinculado' THEN
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, actor_id) VALUES (NEW.id, OLD.huerto_id, 'desvinculado', a);
  dueno := (SELECT propietario_id FROM huerto WHERE id=OLD.huerto_id);
  IF chilito_cuenta_activa(dueno) THEN
   INSERT INTO notificacion(destinatario_id, origen, severidad, titulo, texto, huerto_id, enlace)
   VALUES (dueno, 'vinculacion', 'advertencia', 'Tu equipo se desvinculó',
           'El equipo ' || NEW.identificador || ' ya no está unido a tu huerto.', OLD.huerto_id, '#huerto');
  END IF;
 END IF;
 IF OLD.estado<>'retirado' AND NEW.estado='retirado' THEN
  INSERT INTO dispositivo_evento(dispositivo_id, tipo, actor_id) VALUES (NEW.id, 'retirado', a);
 END IF;
 IF NEW.credencial_hash<>OLD.credencial_hash THEN
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, actor_id) VALUES (NEW.id, NEW.huerto_id, 'credencial_rotada', a);
 END IF;
 IF NEW.firmware_version<>OLD.firmware_version THEN
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, detalle) VALUES (NEW.id, NEW.huerto_id, 'firmware_actualizado', NEW.firmware_version);
 END IF;
 IF NEW.conexion<>OLD.conexion AND NEW.conexion IN ('en_linea','desconectado') THEN
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, ocurrido_en)
  VALUES (NEW.id, NEW.huerto_id, CASE NEW.conexion WHEN 'en_linea' THEN 'conectado' ELSE 'desconectado' END,
          coalesce(NEW.ultima_conexion_en, now()));
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER dispositivo_historial AFTER INSERT OR UPDATE ON dispositivo FOR EACH ROW EXECUTE FUNCTION chilito_dispositivo_historial();

-- Código de vinculación: lo genera el dueño para su huerto activo y sin equipo; se cierra una sola vez.
CREATE FUNCTION public.chilito_codigo_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Los códigos no se borran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF chilito_dueno_huerto(NEW.huerto_id) IS DISTINCT FROM NEW.generado_por_id THEN
   RAISE EXCEPTION 'Solo el dueño de un huerto activo genera su código' USING ERRCODE='23514';
  END IF;
  IF session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.generado_por_id THEN
   RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
  END IF;
  IF chilito_equipo_de_huerto(NEW.huerto_id) IS NOT NULL THEN
   RAISE EXCEPTION 'Este huerto ya tiene equipo' USING ERRCODE='23514';
  END IF;
  IF NEW.estado<>'pendiente' THEN RAISE EXCEPTION 'Un código nace pendiente' USING ERRCODE='23514'; END IF;
  NEW.generado_en := now();
  IF NEW.vence_en > now() + interval '10 minutes' THEN NEW.vence_en := now() + interval '10 minutes'; END IF;
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW) - 'estado' - 'cerrado_en' - 'dispositivo_id') IS DISTINCT FROM (to_jsonb(OLD) - 'estado' - 'cerrado_en' - 'dispositivo_id')
    OR OLD.estado<>'pendiente' THEN
  RAISE EXCEPTION 'Un código solo se cierra una vez' USING ERRCODE='23514';
 END IF;
 IF NEW.estado='utilizado' AND now() > OLD.vence_en THEN
  RAISE EXCEPTION 'El código venció' USING ERRCODE='23514';
 END IF;
 IF NEW.estado='expirado' AND now() <= OLD.vence_en THEN
  RAISE EXCEPTION 'El código aún no vence' USING ERRCODE='23514';
 END IF;
 IF NEW.estado='cancelado' AND session_user='chilito_pkg_runtime' AND pg_trigger_depth() = 1 THEN
  PERFORM chilito_exigir_actor(OLD.generado_por_id);
 END IF;
 IF NEW.estado<>'pendiente' THEN NEW.cerrado_en := now(); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER codigo_reglas BEFORE INSERT OR UPDATE OR DELETE ON codigo_vinculacion FOR EACH ROW EXECUTE FUNCTION chilito_codigo_reglas();


-- 12.6 Telemetría y actuaciones ------------------------------------------------------------------------
-- Una medición o actuación solo se acepta del equipo vinculado a ese huerto.
CREATE FUNCTION public.chilito_telemetria_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE c comando%ROWTYPE;
BEGIN
 IF chilito_equipo_de_huerto(NEW.huerto_id) IS DISTINCT FROM NEW.dispositivo_id THEN
  RAISE EXCEPTION 'El equipo no está vinculado a ese huerto' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME='actuacion' THEN
  IF NEW.comando_id IS NOT NULL THEN
   SELECT * INTO c FROM comando WHERE id=NEW.comando_id;
   IF c.huerto_id<>NEW.huerto_id OR c.dispositivo_id<>NEW.dispositivo_id OR c.origen<>NEW.origen THEN
    RAISE EXCEPTION 'La actuación no corresponde a ese comando' USING ERRCODE='23514';
   END IF;
  END IF;
 END IF;
 IF TG_TABLE_NAME='medicion' THEN NEW.recibida_en := now(); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER telemetria_reglas BEFORE INSERT ON medicion FOR EACH ROW EXECUTE FUNCTION chilito_telemetria_reglas();
CREATE TRIGGER telemetria_reglas BEFORE INSERT ON actuacion FOR EACH ROW EXECUTE FUNCTION chilito_telemetria_reglas();


-- 12.7 Comandos y autodiagnóstico ---------------------------------------------------------------------
-- · Usuario: solo en su huerto, con su equipo vinculado.
-- · Soporte: solo dentro de una sesión técnica abierta, del mismo admin, con autorización vigente.
-- · Solo cambian estado y fechas, avanzando: pendiente → enviado → confirmado | fallido | expirado.
CREATE FUNCTION public.chilito_comando_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE s soporte_sesion%ROWTYPE; k soporte_caso%ROWTYPE;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Los comandos no se borran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF session_user='chilito_pkg_iot' THEN RAISE EXCEPTION 'El servicio IoT no crea comandos' USING ERRCODE='23514'; END IF;
  IF chilito_equipo_de_huerto(NEW.huerto_id) IS DISTINCT FROM NEW.dispositivo_id THEN
   RAISE EXCEPTION 'El huerto no tiene ese equipo vinculado' USING ERRCODE='23514';
  END IF;
  IF session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.solicitado_por_id THEN
   RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
  END IF;
  IF NEW.origen='usuario' THEN
   IF chilito_dueno_huerto(NEW.huerto_id) IS DISTINCT FROM NEW.solicitado_por_id THEN
    RAISE EXCEPTION 'Solo el dueño da órdenes a su huerto' USING ERRCODE='23514';
   END IF;
  ELSE
   SELECT * INTO s FROM soporte_sesion WHERE id=NEW.sesion_id FOR SHARE;
   SELECT * INTO k FROM soporte_caso WHERE id=s.caso_id FOR SHARE;
   IF s.cerrada_en IS NOT NULL OR s.administrador_id<>NEW.solicitado_por_id OR k.huerto_id<>NEW.huerto_id
      OR k.autorizacion_revocada_en IS NOT NULL OR now() >= k.autorizacion_vence_en
      OR NOT chilito_tiene_capacidad(NEW.solicitado_por_id,'atender_soporte') THEN
    RAISE EXCEPTION 'Orden fuera de una sesión técnica autorizada' USING ERRCODE='23514';
   END IF;
  END IF;
  IF NEW.estado<>'pendiente' THEN RAISE EXCEPTION 'Un comando nace pendiente' USING ERRCODE='23514'; END IF;
  NEW.creado_en := now();
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW) - 'estado' - 'enviado_en' - 'resuelto_en' - 'detalle_error')
    IS DISTINCT FROM (to_jsonb(OLD) - 'estado' - 'enviado_en' - 'resuelto_en' - 'detalle_error')
 OR NOT ((OLD.estado='pendiente' AND NEW.estado IN ('enviado','fallido','expirado'))
      OR (OLD.estado='enviado' AND NEW.estado IN ('confirmado','fallido','expirado'))) THEN
  RAISE EXCEPTION 'Transición de comando no permitida' USING ERRCODE='23514';
 END IF;
 IF NEW.estado='enviado' AND NEW.enviado_en IS NULL THEN NEW.enviado_en := now(); END IF;
 IF NEW.estado<>'enviado' AND NEW.resuelto_en IS NULL THEN NEW.resuelto_en := now(); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER comando_reglas BEFORE INSERT OR UPDATE OR DELETE ON comando FOR EACH ROW EXECUTE FUNCTION chilito_comando_reglas();

-- Un comando 'autodiagnostico' crea su autodiagnóstico; si falla o expira, queda «sin_respuesta».
CREATE FUNCTION public.chilito_comando_autodiagnostico() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  INSERT INTO autodiagnostico(huerto_id, dispositivo_id, comando_id, solicitado_por_id)
  VALUES (NEW.huerto_id, NEW.dispositivo_id, NEW.id, NEW.solicitado_por_id);
 ELSIF NEW.estado IN ('fallido','expirado') THEN
  UPDATE autodiagnostico SET estado='sin_respuesta', completado_en=now() WHERE comando_id=NEW.id AND estado='en_curso';
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER comando_autodiagnostico AFTER INSERT OR UPDATE OF estado ON comando FOR EACH ROW
 WHEN (NEW.tipo='autodiagnostico') EXECUTE FUNCTION chilito_comando_autodiagnostico();

-- El autodiagnóstico solo lo crea su comando; se cierra una vez. Al completarse, la base calcula el
-- resultado general (con_fallas si alguna revisión dio falla o sin_respuesta).
CREATE FUNCTION public.chilito_autodiagnostico_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Los autodiagnósticos no se borran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF pg_trigger_depth() < 2 THEN
   RAISE EXCEPTION 'El autodiagnóstico se crea con un comando «autodiagnostico»' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW) - 'estado' - 'resultado_general' - 'completado_en') IS DISTINCT FROM (to_jsonb(OLD) - 'estado' - 'resultado_general' - 'completado_en')
    OR OLD.estado<>'en_curso' OR NEW.estado='en_curso' THEN
  RAISE EXCEPTION 'Un autodiagnóstico solo se cierra una vez' USING ERRCODE='23514';
 END IF;
 NEW.completado_en := coalesce(NEW.completado_en, now());
 IF NEW.estado='completado' THEN
  IF NOT EXISTS(SELECT 1 FROM autodiagnostico_revision WHERE autodiagnostico_id=NEW.id) THEN
   RAISE EXCEPTION 'No hay revisiones registradas' USING ERRCODE='23514';
  END IF;
  NEW.resultado_general := CASE WHEN EXISTS(SELECT 1 FROM autodiagnostico_revision WHERE autodiagnostico_id=NEW.id
                                AND resultado IN ('falla','sin_respuesta')) THEN 'con_fallas' ELSE 'correcto' END;
 ELSE
  NEW.resultado_general := NULL;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER autodiagnostico_reglas BEFORE INSERT OR UPDATE OR DELETE ON autodiagnostico FOR EACH ROW EXECUTE FUNCTION chilito_autodiagnostico_reglas();

CREATE FUNCTION public.chilito_revision_autodiag_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM autodiagnostico WHERE id=NEW.autodiagnostico_id AND estado='en_curso') THEN
  RAISE EXCEPTION 'El autodiagnóstico ya está cerrado' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER revision_autodiag_reglas BEFORE INSERT ON autodiagnostico_revision FOR EACH ROW EXECUTE FUNCTION chilito_revision_autodiag_reglas();


-- 12.8 Cuidados ---------------------------------------------------------------------------------------
-- Registra el dueño (o un admin de mantenimientos). Revisiones: admin, número consecutivo, sin anulados.
CREATE FUNCTION public.chilito_cuidado_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE ultimo integer; anulado boolean;
BEGIN
 IF TG_TABLE_NAME='cuidado' THEN
  IF chilito_dueno_huerto(NEW.huerto_id) IS NULL THEN RAISE EXCEPTION 'El huerto no está activo' USING ERRCODE='23514'; END IF;
  IF NOT (chilito_dueno_huerto(NEW.huerto_id) = NEW.registrado_por_id
          OR chilito_tiene_capacidad(NEW.registrado_por_id,'gestionar_mantenimientos')) THEN
   RAISE EXCEPTION 'Solo el dueño del huerto o un admin de mantenimientos registra cuidados' USING ERRCODE='23514';
  END IF;
  IF session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.registrado_por_id THEN
   RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
  END IF;
  NEW.registrado_en := now();
  RETURN NEW;
 END IF;
 IF NOT chilito_tiene_capacidad(NEW.editor_id,'gestionar_mantenimientos') THEN
  RAISE EXCEPTION 'Corregir cuidados requiere «gestionar_mantenimientos»' USING ERRCODE='23514';
 END IF;
 IF session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.editor_id THEN
  RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
 END IF;
 PERFORM 1 FROM cuidado WHERE id=NEW.cuidado_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Cuidado inexistente' USING ERRCODE='23514'; END IF;
 SELECT coalesce(max(numero),0), coalesce(bool_or(tipo='anulacion'),false) INTO ultimo, anulado
  FROM cuidado_revision WHERE cuidado_id=NEW.cuidado_id;
 IF anulado THEN RAISE EXCEPTION 'Un cuidado anulado no admite revisiones' USING ERRCODE='23514'; END IF;
 IF NEW.numero<>ultimo+1 THEN RAISE EXCEPTION 'Número de revisión fuera de orden (registro desactualizado)' USING ERRCODE='23514'; END IF;
 NEW.registrada_en := now();
 RETURN NEW;
END $$;
CREATE TRIGGER cuidado_reglas BEFORE INSERT ON cuidado FOR EACH ROW EXECUTE FUNCTION chilito_cuidado_reglas();
CREATE TRIGGER cuidado_revision_reglas BEFORE INSERT ON cuidado_revision FOR EACH ROW EXECUTE FUNCTION chilito_cuidado_reglas();

-- Guías: nacen como borrador (salvo carga inicial), no se borran, no cambian identidad; cada cambio sube
-- la versión en 1 e indica responsable con «gestionar_guias».
CREATE FUNCTION public.chilito_guia_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Las guías no se borran: se retiran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF session_user='chilito_pkg_runtime' THEN
   IF NEW.estado<>'borrador' OR NEW.version<>1 OR NEW.creado_por_id IS NULL
      OR chilito_actor() IS DISTINCT FROM NEW.creado_por_id OR NOT chilito_tiene_capacidad(NEW.creado_por_id,'gestionar_guias') THEN
    RAISE EXCEPTION 'Crear guías requiere «gestionar_guias» y nacen como borrador' USING ERRCODE='23514';
   END IF;
  END IF;
  RETURN NEW;
 END IF;
 IF NEW.id<>OLD.id OR NEW.clave<>OLD.clave OR NEW.creado_en<>OLD.creado_en
    OR NEW.creado_por_id IS DISTINCT FROM OLD.creado_por_id THEN
  RAISE EXCEPTION 'La identidad y autoría de una guía no cambian' USING ERRCODE='23514';
 END IF;
 IF NEW.version<>OLD.version+1 OR NEW.actualizado_por_id IS NULL
    OR NOT chilito_tiene_capacidad(NEW.actualizado_por_id,'gestionar_guias')
    OR (session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.actualizado_por_id) THEN
  RAISE EXCEPTION 'Cada cambio avanza la versión e indica un responsable con «gestionar_guias»' USING ERRCODE='23514';
 END IF;
 NEW.actualizado_en := now();
 RETURN NEW;
END $$;
CREATE TRIGGER guia_reglas BEFORE INSERT OR UPDATE OR DELETE ON guia_cuidado FOR EACH ROW EXECUTE FUNCTION chilito_guia_reglas();


-- 12.9 Soporte ----------------------------------------------------------------------------------------
CREATE FUNCTION public.chilito_caso_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE a bigint := chilito_actor(); app boolean := (session_user='chilito_pkg_runtime');
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Los casos no se borran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF chilito_dueno_huerto(NEW.huerto_id) IS DISTINCT FROM NEW.solicitante_id THEN
   RAISE EXCEPTION 'Solo el dueño del huerto pide soporte para él' USING ERRCODE='23514';
  END IF;
  IF app AND a IS DISTINCT FROM NEW.solicitante_id THEN
   RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
  END IF;
  IF chilito_equipo_de_huerto(NEW.huerto_id) IS DISTINCT FROM NEW.dispositivo_id THEN
   RAISE EXCEPTION 'El huerto no tiene ese equipo vinculado' USING ERRCODE='23514';
  END IF;
  IF NEW.autodiagnostico_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM autodiagnostico WHERE id=NEW.autodiagnostico_id AND huerto_id=NEW.huerto_id) THEN
   RAISE EXCEPTION 'El autodiagnóstico es de otro huerto' USING ERRCODE='23514';
  END IF;
  IF NEW.estado<>'abierto' OR NEW.autorizacion_revocada_en IS NOT NULL THEN
   RAISE EXCEPTION 'Un caso nace abierto y autorizado' USING ERRCODE='23514';
  END IF;
  NEW.creado_en := now(); NEW.autorizada_en := now();
  IF NEW.autorizacion_vence_en > now() + interval '24 hours' OR NEW.autorizacion_vence_en <= now() THEN
   NEW.autorizacion_vence_en := now() + interval '24 hours';
  END IF;
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW) - 'folio' - 'estado' - 'atendido_por_id' - 'tomado_en' - 'resultado' - 'nota_resolucion' - 'cerrado_en' - 'autorizacion_revocada_en')
    IS DISTINCT FROM (to_jsonb(OLD) - 'folio' - 'estado' - 'atendido_por_id' - 'tomado_en' - 'resultado' - 'nota_resolucion' - 'cerrado_en' - 'autorizacion_revocada_en') THEN
  RAISE EXCEPTION 'Esos datos del caso no cambian' USING ERRCODE='23514';
 END IF;
 IF OLD.estado IN ('resuelto','cancelado') THEN RAISE EXCEPTION 'El caso está cerrado' USING ERRCODE='23514'; END IF;
 IF OLD.autorizacion_revocada_en IS NOT NULL AND NEW.autorizacion_revocada_en IS DISTINCT FROM OLD.autorizacion_revocada_en THEN
  RAISE EXCEPTION 'La revocación no tiene vuelta atrás' USING ERRCODE='23514';
 END IF;
 IF NEW.estado=OLD.estado THEN
  -- Solo revocar (la persona) o nada.
  IF (NEW.atendido_por_id, NEW.tomado_en, NEW.resultado, NEW.nota_resolucion, NEW.cerrado_en)
     IS DISTINCT FROM (OLD.atendido_por_id, OLD.tomado_en, OLD.resultado, OLD.nota_resolucion, OLD.cerrado_en) THEN
   RAISE EXCEPTION 'Cambio de caso no permitido' USING ERRCODE='23514';
  END IF;
  IF NEW.autorizacion_revocada_en IS NOT NULL AND OLD.autorizacion_revocada_en IS NULL THEN
   IF app AND a IS DISTINCT FROM OLD.solicitante_id THEN
    RAISE EXCEPTION 'Solo la persona que autorizó puede revocar' USING ERRCODE='23514';
   END IF;
   NEW.autorizacion_revocada_en := now();
  END IF;
  RETURN NEW;
 END IF;
 IF OLD.estado='abierto' AND NEW.estado='en_atencion' THEN
  IF NOT chilito_tiene_capacidad(NEW.atendido_por_id,'atender_soporte') OR (app AND a IS DISTINCT FROM NEW.atendido_por_id) THEN
   RAISE EXCEPTION 'Atender requiere «atender_soporte» y lo toma quien atiende' USING ERRCODE='23514';
  END IF;
  NEW.tomado_en := now();
 ELSIF NEW.estado='resuelto' THEN
  IF OLD.estado='abierto' THEN NEW.atendido_por_id := coalesce(NEW.atendido_por_id, a); NEW.tomado_en := now(); END IF;
  IF NOT chilito_tiene_capacidad(NEW.atendido_por_id,'atender_soporte') OR (app AND a IS DISTINCT FROM NEW.atendido_por_id)
     OR NEW.atendido_por_id IS DISTINCT FROM coalesce(OLD.atendido_por_id, NEW.atendido_por_id) THEN
   RAISE EXCEPTION 'Resuelve el caso quien lo atiende, con «atender_soporte»' USING ERRCODE='23514';
  END IF;
  NEW.cerrado_en := now(); NEW.autorizacion_revocada_en := coalesce(OLD.autorizacion_revocada_en, now());
 ELSIF NEW.estado='cancelado' THEN
  IF app AND a IS DISTINCT FROM OLD.solicitante_id THEN
   RAISE EXCEPTION 'Solo la persona que pidió soporte cancela su caso' USING ERRCODE='23514';
  END IF;
  NEW.cerrado_en := now(); NEW.autorizacion_revocada_en := coalesce(OLD.autorizacion_revocada_en, now());
 ELSE
  RAISE EXCEPTION 'Transición de caso no permitida' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER caso_reglas BEFORE INSERT OR UPDATE OR DELETE ON soporte_caso FOR EACH ROW EXECUTE FUNCTION chilito_caso_reglas();

-- Efectos del caso: al crearse, aviso al buzón de soporte y a cada admin de soporte; al revocar o cerrar,
-- se cierran sus sesiones técnicas; la persona recibe avisos cuando la atienden y cuando se resuelve.
CREATE FUNCTION public.chilito_caso_efectos() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  INSERT INTO correo_pendiente(tipo, caso_id) VALUES ('caso_nuevo', NEW.id);
  INSERT INTO notificacion(destinatario_id, origen, severidad, titulo, texto, huerto_id, enlace)
  SELECT up.usuario_id, 'soporte', 'advertencia', 'Nueva solicitud de soporte ' || NEW.folio,
         'Incidente: ' || NEW.incidente || '. Autorización vigente 24 h.', NEW.huerto_id, '#admin/consola'
  FROM cuentas_usuario_user_permissions up JOIN auth_permission p ON p.id=up.permission_id
  JOIN django_content_type c ON c.id=p.content_type_id AND c.app_label='cuentas'
  WHERE p.codename='atender_soporte' AND chilito_cuenta_activa(up.usuario_id);
  RETURN NULL;
 END IF;
 IF NEW.autorizacion_revocada_en IS NOT NULL AND OLD.autorizacion_revocada_en IS NULL OR NEW.estado IN ('resuelto','cancelado') THEN
  UPDATE soporte_sesion SET cerrada_en=now(),
         motivo_cierre=CASE WHEN NEW.estado IN ('resuelto','cancelado') THEN 'caso_cerrado' ELSE 'revocada' END
  WHERE caso_id=NEW.id AND cerrada_en IS NULL;
 END IF;
 IF NEW.estado<>OLD.estado AND NEW.estado IN ('en_atencion','resuelto') THEN
  INSERT INTO notificacion(destinatario_id, origen, titulo, texto, huerto_id, enlace)
  VALUES (NEW.solicitante_id, 'soporte',
          CASE NEW.estado WHEN 'en_atencion' THEN 'Soporte está revisando tu caso ' ELSE 'Tu caso se resolvió: ' END || NEW.folio,
          CASE NEW.estado WHEN 'en_atencion' THEN 'Puedes revocar el acceso cuando quieras desde Soporte técnico.'
               ELSE 'Resultado: ' || NEW.resultado || '. La autorización terminó.' END,
          NEW.huerto_id, '#soporte');
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER caso_efectos AFTER INSERT OR UPDATE ON soporte_caso FOR EACH ROW EXECUTE FUNCTION chilito_caso_efectos();

-- Sesión técnica: la abre el admin que atiende el caso, con autorización vigente; solo se cierra, una vez.
CREATE FUNCTION public.chilito_sesion_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE k soporte_caso%ROWTYPE;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Las sesiones técnicas no se borran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  SELECT * INTO k FROM soporte_caso WHERE id=NEW.caso_id FOR UPDATE;
  IF k.estado<>'en_atencion' OR k.atendido_por_id IS DISTINCT FROM NEW.administrador_id
     OR k.autorizacion_revocada_en IS NOT NULL OR now() >= k.autorizacion_vence_en
     OR NOT chilito_tiene_capacidad(NEW.administrador_id,'atender_soporte') THEN
   RAISE EXCEPTION 'No hay autorización vigente para conectar' USING ERRCODE='23514';
  END IF;
  IF session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.administrador_id THEN
   RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
  END IF;
  IF NEW.cerrada_en IS NOT NULL THEN RAISE EXCEPTION 'Una sesión nace abierta' USING ERRCODE='23514'; END IF;
  NEW.iniciada_en := now();
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW) - 'cerrada_en' - 'motivo_cierre') IS DISTINCT FROM (to_jsonb(OLD) - 'cerrada_en' - 'motivo_cierre')
    OR OLD.cerrada_en IS NOT NULL OR NEW.cerrada_en IS NULL THEN
  RAISE EXCEPTION 'Una sesión técnica solo se cierra, una vez' USING ERRCODE='23514';
 END IF;
 IF NEW.motivo_cierre IN ('manual','cierre_sesion') AND session_user='chilito_pkg_runtime' AND pg_trigger_depth()=1
    AND chilito_actor() IS DISTINCT FROM OLD.administrador_id THEN
  RAISE EXCEPTION 'Solo el admin de la sesión la cierra a mano' USING ERRCODE='23514';
 END IF;
 NEW.cerrada_en := now();
 RETURN NEW;
END $$;
CREATE TRIGGER sesion_reglas BEFORE INSERT OR UPDATE OR DELETE ON soporte_sesion FOR EACH ROW EXECUTE FUNCTION chilito_sesion_reglas();


-- 12.10 Notificaciones, IA, buzón, correos y ventas ----------------------------------------------------
-- Notificación: para una cuenta activa; si es de un huerto, para su dueño o para un admin. Solo se marca
-- leída o resuelta. Se borran (tarea periódica) las leídas de más de 180 días y las de cuentas anonimizadas.
CREATE FUNCTION public.chilito_notificacion_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  IF chilito_es_propietario_bd() AND (OLD.leida_en < now() - interval '180 days'
     OR EXISTS(SELECT 1 FROM cuentas_usuario WHERE id=OLD.destinatario_id AND anonimizada_en IS NOT NULL)) THEN
   RETURN OLD;
  END IF;
  RAISE EXCEPTION 'Las notificaciones no se borran' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' THEN
  IF NOT chilito_cuenta_activa(NEW.destinatario_id) THEN RETURN NULL; END IF;  -- cuentas inactivas: se omite
  IF session_user='chilito_pkg_iot' AND (NEW.origen NOT IN ('dispositivo','ia') OR NEW.huerto_id IS NULL
     OR chilito_dueno_huerto(NEW.huerto_id) IS DISTINCT FROM NEW.destinatario_id) THEN
   RAISE EXCEPTION 'El servicio IoT solo avisa al dueño de su huerto (origen dispositivo o ia)' USING ERRCODE='23514';
  END IF;
  IF NEW.huerto_id IS NOT NULL AND NOT (chilito_dueno_huerto(NEW.huerto_id) = NEW.destinatario_id OR chilito_es_admin(NEW.destinatario_id)) THEN
   RAISE EXCEPTION 'Notificación de un huerto ajeno' USING ERRCODE='23514';
  END IF;
  NEW.creada_en := now(); NEW.leida_en := NULL; NEW.resuelta_en := NULL;
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW) - 'leida_en' - 'resuelta_en') IS DISTINCT FROM (to_jsonb(OLD) - 'leida_en' - 'resuelta_en')
    OR (OLD.leida_en IS NOT NULL AND NEW.leida_en IS DISTINCT FROM OLD.leida_en)
    OR (OLD.resuelta_en IS NOT NULL AND NEW.resuelta_en IS DISTINCT FROM OLD.resuelta_en) THEN
  RAISE EXCEPTION 'Una notificación solo se marca leída o resuelta' USING ERRCODE='23514';
 END IF;
 IF session_user='chilito_pkg_runtime' THEN PERFORM chilito_exigir_actor(OLD.destinatario_id); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER notificacion_reglas BEFORE INSERT OR UPDATE OR DELETE ON notificacion FOR EACH ROW EXECUTE FUNCTION chilito_notificacion_reglas();

CREATE FUNCTION public.chilito_ia_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF chilito_dueno_huerto(NEW.huerto_id) IS NULL THEN RAISE EXCEPTION 'El huerto no está activo' USING ERRCODE='23514'; END IF;
 NEW.generado_en := now();
 RETURN NEW;
END $$;
CREATE TRIGGER ia_reglas BEFORE INSERT ON ia_resumen FOR EACH ROW EXECUTE FUNCTION chilito_ia_reglas();

-- Buzón «Consíguelo»: nueva → atendida | archivada; atendida ↔ archivada. Lo atiende quien tiene
-- «atender_consultas». No se borra. Pasado un año, solo el propietario (tarea periódica) la anonimiza.
CREATE FUNCTION public.chilito_consulta_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'La consulta se conserva' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.estado<>'nueva' THEN RAISE EXCEPTION 'Una consulta nace nueva' USING ERRCODE='23514'; END IF;
  NEW.recibida_en := now();
  RETURN NEW;
 END IF;
 IF NEW.anonimizada_en IS NOT NULL AND OLD.anonimizada_en IS NULL THEN
  IF NOT chilito_es_propietario_bd() THEN RAISE EXCEPTION 'Solo la tarea periódica anonimiza' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW) - 'folio' - 'estado' - 'atendida_por_id' - 'atendida_en') IS DISTINCT FROM (to_jsonb(OLD) - 'folio' - 'estado' - 'atendida_por_id' - 'atendida_en')
 OR NOT ((OLD.estado='nueva' AND NEW.estado IN ('atendida','archivada'))
      OR (OLD.estado='atendida' AND NEW.estado='archivada')
      OR (OLD.estado='archivada' AND NEW.estado='atendida')) THEN
  RAISE EXCEPTION 'Transición de atención no permitida' USING ERRCODE='23514';
 END IF;
 IF NOT chilito_tiene_capacidad(NEW.atendida_por_id,'atender_consultas')
    OR (session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.atendida_por_id) THEN
  RAISE EXCEPTION 'Atender consultas requiere «atender_consultas»' USING ERRCODE='23514';
 END IF;
 NEW.atendida_en := now();
 RETURN NEW;
END $$;
CREATE TRIGGER consulta_reglas BEFORE INSERT OR UPDATE OR DELETE ON consulta_producto FOR EACH ROW EXECUTE FUNCTION chilito_consulta_reglas();

-- Cada consulta nueva avisa al buzón de soporte y a cada admin con «atender_consultas».
CREATE FUNCTION public.chilito_consulta_efectos() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 INSERT INTO correo_pendiente(tipo, consulta_id) VALUES ('consulta_nueva', NEW.id);
 INSERT INTO notificacion(destinatario_id, origen, titulo, enlace)
 SELECT up.usuario_id, 'sistema', 'Nueva consulta del producto ' || NEW.folio, '#admin/consultas'
 FROM cuentas_usuario_user_permissions up JOIN auth_permission p ON p.id=up.permission_id
 JOIN django_content_type c ON c.id=p.content_type_id AND c.app_label='cuentas'
 WHERE p.codename='atender_consultas' AND chilito_cuenta_activa(up.usuario_id);
 RETURN NULL;
END $$;
CREATE TRIGGER consulta_efectos AFTER INSERT ON consulta_producto FOR EACH ROW EXECUTE FUNCTION chilito_consulta_efectos();

-- Cola de correos: no se borra; solo suma intentos hasta que el servidor de correo lo acepta.
CREATE FUNCTION public.chilito_correo_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'El aviso por correo se conserva' USING ERRCODE='23514'; END IF;
 IF (to_jsonb(NEW) - 'estado' - 'intentos' - 'ultimo_intento_en' - 'aceptado_en') IS DISTINCT FROM (to_jsonb(OLD) - 'estado' - 'intentos' - 'ultimo_intento_en' - 'aceptado_en')
    OR OLD.estado='aceptado_smtp' OR NEW.intentos < OLD.intentos THEN
  RAISE EXCEPTION 'El aviso solo registra intentos hasta su aceptación' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER correo_reglas BEFORE UPDATE OR DELETE ON correo_pendiente FOR EACH ROW EXECUTE FUNCTION chilito_correo_reglas();

-- Ventas: con «gestionar_ventas». Solo cambian pago, entrega, nota y cancelación (definitiva). No se borran.
CREATE FUNCTION public.chilito_venta_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Las ventas no se borran: se cancelan' USING ERRCODE='23514'; END IF;
 IF session_user='chilito_pkg_runtime' THEN PERFORM chilito_exigir_capacidad('gestionar_ventas'); END IF;
 IF TG_OP='INSERT' THEN
  IF NOT chilito_tiene_capacidad(NEW.registrada_por_id,'gestionar_ventas')
     OR (session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.registrada_por_id) THEN
   RAISE EXCEPTION 'Registrar ventas requiere «gestionar_ventas»' USING ERRCODE='23514';
  END IF;
  IF EXISTS(SELECT 1 FROM dispositivo WHERE id=NEW.dispositivo_id AND estado='retirado') THEN
   RAISE EXCEPTION 'No se vende un equipo retirado' USING ERRCODE='23514';
  END IF;
  IF NEW.estado<>'vigente' THEN RAISE EXCEPTION 'Una venta nace vigente' USING ERRCODE='23514'; END IF;
  IF NEW.vendida_en > chilito_hoy() THEN RAISE EXCEPTION 'La fecha de venta no puede ser futura' USING ERRCODE='23514'; END IF;
  NEW.registrada_en := now();
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW) - 'estado_pago' - 'importe_recibido_mxn' - 'referencia_pago' - 'modalidad_entrega' - 'entrega_prevista_en'
     - 'entregada_en' - 'nota' - 'estado' - 'cancelada_en')
    IS DISTINCT FROM (to_jsonb(OLD) - 'estado_pago' - 'importe_recibido_mxn' - 'referencia_pago' - 'modalidad_entrega' - 'entrega_prevista_en'
     - 'entregada_en' - 'nota' - 'estado' - 'cancelada_en')
    OR OLD.estado='cancelada' THEN
  RAISE EXCEPTION 'Solo cambian pago, entrega, nota o cancelación de una venta vigente' USING ERRCODE='23514';
 END IF;
 IF NEW.estado='cancelada' THEN NEW.cancelada_en := now(); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER venta_reglas BEFORE INSERT OR UPDATE OR DELETE ON venta FOR EACH ROW EXECUTE FUNCTION chilito_venta_reglas();


-- 12.11 Legal y privacidad -----------------------------------------------------------------------------
-- Documento legal: el borrador se edita y se puede borrar; publicar exige «gestionar_legales» y una versión
-- mayor que la vigente; una versión publicada no cambia ni se borra. La huella SHA-256 la calcula la base.
CREATE FUNCTION public.chilito_legal_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE ultima text; a bigint := chilito_actor(); app boolean := (session_user='chilito_pkg_runtime');
BEGIN
 IF TG_OP='DELETE' THEN
  IF OLD.estado='publicada' THEN RAISE EXCEPTION 'Una versión publicada no se borra' USING ERRCODE='23514'; END IF;
  IF app THEN PERFORM chilito_exigir_capacidad('gestionar_legales'); END IF;
  RETURN OLD;
 END IF;
 IF app THEN PERFORM chilito_exigir_capacidad('gestionar_legales'); END IF;
 IF TG_OP='UPDATE' THEN
  IF OLD.estado='publicada' THEN RAISE EXCEPTION 'Una versión publicada no cambia: crea una nueva' USING ERRCODE='23514'; END IF;
  IF NEW.id<>OLD.id OR NEW.tipo<>OLD.tipo OR NEW.creado_en<>OLD.creado_en OR NEW.creado_por_id IS DISTINCT FROM OLD.creado_por_id THEN
   RAISE EXCEPTION 'Tipo y autoría del documento no cambian' USING ERRCODE='23514';
  END IF;
 ELSE
  NEW.creado_en := now();
  IF app AND NEW.creado_por_id IS DISTINCT FROM a THEN RAISE EXCEPTION 'El autor debe ser quien lo crea' USING ERRCODE='23514'; END IF;
  IF app AND NEW.estado<>'borrador' THEN RAISE EXCEPTION 'Un documento nace como borrador' USING ERRCODE='23514'; END IF;
 END IF;
 NEW.contenido_sha256 := encode(sha256(convert_to(NEW.contenido,'UTF8')),'hex');
 NEW.actualizado_en := now();
 IF NEW.estado='publicada' THEN
  SELECT version INTO ultima FROM documento_legal WHERE tipo=NEW.tipo AND estado='publicada' AND id<>NEW.id
   ORDER BY chilito_version_num(version) DESC LIMIT 1;
  IF ultima IS NOT NULL AND chilito_version_num(NEW.version) <= chilito_version_num(ultima) THEN
   RAISE EXCEPTION 'La versión debe ser mayor que la vigente (%)', ultima USING ERRCODE='23514';
  END IF;
  IF app THEN NEW.publicado_por_id := a; END IF;
  NEW.publicado_en := clock_timestamp();
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER legal_reglas BEFORE INSERT OR UPDATE OR DELETE ON documento_legal FOR EACH ROW EXECUTE FUNCTION chilito_legal_reglas();

-- Al publicar una versión, cada cuenta activa recibe un aviso. Términos y aviso: deberá aceptarlos al entrar.
CREATE FUNCTION public.chilito_legal_publicado() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 INSERT INTO notificacion(destinatario_id, origen, severidad, titulo, texto, enlace)
 SELECT u.id, 'legal', 'advertencia',
        CASE NEW.tipo WHEN 'terminos' THEN 'Actualizamos los términos y condiciones'
                      WHEN 'aviso_privacidad' THEN 'Actualizamos el aviso de privacidad'
                      ELSE 'Actualizamos la política de cookies' END || ' (versión ' || NEW.version || ')',
        CASE WHEN NEW.tipo IN ('terminos','aviso_privacidad') THEN 'Te pediremos aceptarla la próxima vez que entres.'
             ELSE 'Puedes revisar tu decisión sobre cookies en Mi cuenta › Privacidad.' END,
        '#cuenta/privacidad'
 FROM cuentas_usuario u WHERE u.is_active AND u.anonimizada_en IS NULL;
 RETURN NULL;
END $$;
CREATE TRIGGER legal_publicado AFTER INSERT OR UPDATE OF estado ON documento_legal FOR EACH ROW
 WHEN (NEW.estado='publicada') EXECUTE FUNCTION chilito_legal_publicado();

-- Sujeto: no cambia de ámbito ni de fecha; un navegador puede ligarse a una cuenta una sola vez.
CREATE FUNCTION public.chilito_sujeto_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'El sujeto de privacidad se conserva' USING ERRCODE='23514'; END IF;
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.creado_en IS DISTINCT FROM OLD.creado_en OR NEW.ambito IS DISTINCT FROM OLD.ambito
    OR (OLD.usuario_id IS NOT NULL AND NEW.usuario_id IS DISTINCT FROM OLD.usuario_id) THEN
  RAISE EXCEPTION 'No se reasigna un sujeto, su ámbito ni su cuenta vinculada' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sujeto_reglas BEFORE UPDATE OR DELETE ON privacidad_sujeto FOR EACH ROW EXECUTE FUNCTION chilito_sujeto_reglas();

-- Decisión: cada acto con el documento VIGENTE de su tipo y el ámbito correcto (cookies → navegador;
-- términos y aviso → la cuenta, que debe ser la misma que usuario_id).
CREATE FUNCTION public.chilito_decision_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE s privacidad_sujeto%ROWTYPE; tipo_doc text;
BEGIN
 SELECT * INTO s FROM privacidad_sujeto WHERE id=NEW.sujeto_id;
 tipo_doc := CASE NEW.acto WHEN 'aceptacion_terminos' THEN 'terminos' WHEN 'lectura_aviso' THEN 'aviso_privacidad' ELSE 'politica_cookies' END;
 IF NEW.documento_id IS DISTINCT FROM chilito_documento_vigente(tipo_doc) THEN
  RAISE EXCEPTION 'La decisión debe referirse a la versión vigente de %', tipo_doc USING ERRCODE='23514';
 END IF;
 IF NEW.acto='cookies' THEN
  IF s.ambito<>'navegador' OR (NEW.usuario_id IS NOT NULL AND NEW.usuario_id IS DISTINCT FROM s.usuario_id) THEN
   RAISE EXCEPTION 'Las cookies se deciden por navegador' USING ERRCODE='23514';
  END IF;
 ELSIF s.ambito<>'cuenta' OR s.usuario_id IS DISTINCT FROM NEW.usuario_id THEN
  RAISE EXCEPTION 'Términos y aviso se aceptan desde la propia cuenta' USING ERRCODE='23514';
 END IF;
 NEW.registrada_en := now();
 RETURN NEW;
END $$;
CREATE TRIGGER decision_reglas BEFORE INSERT ON privacidad_decision FOR EACH ROW EXECUTE FUNCTION chilito_decision_reglas();

-- Preferencia vigente: apunta a una decisión de cookies del mismo sujeto y finalidad.
CREATE FUNCTION public.chilito_preferencia_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE d privacidad_decision%ROWTYPE;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'La preferencia se conserva' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.id<>OLD.id OR NEW.sujeto_id<>OLD.sujeto_id OR NEW.finalidad_id<>OLD.finalidad_id) THEN
  RAISE EXCEPTION 'No se reasigna una preferencia' USING ERRCODE='23514';
 END IF;
 SELECT * INTO d FROM privacidad_decision WHERE id=NEW.decision_id;
 IF NOT FOUND OR d.sujeto_id<>NEW.sujeto_id OR d.finalidad_id IS DISTINCT FROM NEW.finalidad_id OR d.acto<>'cookies' THEN
  RAISE EXCEPTION 'La preferencia exige una decisión de cookies del mismo sujeto y finalidad' USING ERRCODE='23514';
 END IF;
 NEW.actualizada_en := now();
 RETURN NEW;
END $$;
CREATE TRIGGER preferencia_reglas BEFORE INSERT OR UPDATE OR DELETE ON privacidad_preferencia FOR EACH ROW EXECUTE FUNCTION chilito_preferencia_reglas();

-- 12.12 Eventos que puede reportar el servicio IoT ------------------------------------------------------
-- El servicio IoT solo reporta conexión, errores y reinicios del equipo vinculado a ese huerto. El resto de
-- eventos (alta, vinculado, desvinculado, retirado, credencial, firmware) los escribe la propia base.
CREATE FUNCTION public.chilito_evento_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF session_user='chilito_pkg_iot' AND pg_trigger_depth() = 1 THEN
  IF NEW.tipo NOT IN ('conectado','desconectado','error','reinicio') OR NEW.actor_id IS NOT NULL
     OR NEW.huerto_id IS DISTINCT FROM (SELECT huerto_id FROM dispositivo WHERE id=NEW.dispositivo_id) THEN
   RAISE EXCEPTION 'El servicio IoT solo reporta conexión, errores y reinicios de su huerto actual' USING ERRCODE='23514';
  END IF;
 END IF;
 NEW.registrado_en := now();
 RETURN NEW;
END $$;
CREATE TRIGGER evento_reglas BEFORE INSERT ON dispositivo_evento FOR EACH ROW EXECUTE FUNCTION chilito_evento_reglas();


-- =====================================================================================================
-- 13. FUNCIONES DE NEGOCIO Y DE ADMINISTRACIÓN
-- =====================================================================================================

-- 13.1 Vincular un equipo (la llama el backend cuando el ESP32 presenta su código por HTTPS) -------------
-- Antes de llamarla, el backend ya comprobó la identidad del ESP32 con su credencial (credencial_hash).
-- Recibe el identificador del equipo y el HMAC-SHA256 (hex) del código que escribió la persona.
-- resultado: vinculado · codigo_invalido · codigo_vencido · codigo_usado · dispositivo_desconocido ·
--            dispositivo_retirado · dispositivo_ocupado · huerto_no_disponible
CREATE FUNCTION public.chilito_vincular_dispositivo(p_identificador text, p_codigo_hash text,
  OUT resultado text, OUT huerto_id bigint)
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE c public.codigo_vinculacion%ROWTYPE; d public.dispositivo%ROWTYPE;
BEGIN
 SELECT * INTO c FROM public.codigo_vinculacion WHERE codigo_hash = lower(p_codigo_hash) FOR UPDATE;
 IF NOT FOUND THEN resultado := 'codigo_invalido'; RETURN; END IF;
 huerto_id := c.huerto_id;
 IF c.estado = 'utilizado' THEN resultado := 'codigo_usado'; RETURN; END IF;
 IF c.estado <> 'pendiente' THEN resultado := 'codigo_invalido'; RETURN; END IF;
 IF now() > c.vence_en THEN
  UPDATE public.codigo_vinculacion SET estado='expirado', cerrado_en=now() WHERE id=c.id;
  resultado := 'codigo_vencido'; RETURN;
 END IF;
 SELECT * INTO d FROM public.dispositivo WHERE identificador = p_identificador FOR UPDATE;
 IF NOT FOUND THEN resultado := 'dispositivo_desconocido'; RETURN; END IF;
 IF d.estado = 'retirado' THEN resultado := 'dispositivo_retirado'; RETURN; END IF;
 IF d.estado = 'vinculado' THEN resultado := 'dispositivo_ocupado'; RETURN; END IF;
 IF public.chilito_dueno_huerto(c.huerto_id) IS NULL OR public.chilito_equipo_de_huerto(c.huerto_id) IS NOT NULL THEN
  resultado := 'huerto_no_disponible'; RETURN;
 END IF;
 UPDATE public.codigo_vinculacion SET estado='utilizado', dispositivo_id=d.id, cerrado_en=now() WHERE id=c.id;
 UPDATE public.dispositivo SET estado='vinculado', huerto_id=c.huerto_id, vinculado_en=now() WHERE id=d.id;
 INSERT INTO public.auditoria(actor_id, accion, entidad, entidad_id, huerto_id, detalle)
 VALUES (c.generado_por_id, 'vincular_dispositivo', 'dispositivo', d.id::text, c.huerto_id,
         jsonb_build_object('identificador', d.identificador));
 resultado := 'vinculado';
END $$;

-- 13.2 Desvincular un equipo (dueño del huerto o admin con «gestionar_dispositivos»; actor obligatorio) ---
CREATE FUNCTION public.chilito_desvincular_dispositivo(p_dispositivo_id bigint) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE h bigint;
BEGIN
 SELECT d.huerto_id INTO h FROM public.dispositivo d WHERE d.id=p_dispositivo_id AND d.estado='vinculado' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'El equipo no está vinculado' USING ERRCODE='23514'; END IF;
 UPDATE public.dispositivo SET estado='disponible', huerto_id=NULL, vinculado_en=NULL WHERE id=p_dispositivo_id;
 INSERT INTO public.auditoria(actor_id, accion, entidad, entidad_id, huerto_id)
 VALUES (public.chilito_actor(), 'desvincular_dispositivo', 'dispositivo', p_dispositivo_id::text, h);
END $$;

-- 13.3 Textos legales que la cuenta debe aceptar al entrar (vacío = nada pendiente) ----------------------
CREATE FUNCTION public.chilito_aceptaciones_pendientes(p_usuario bigint)
RETURNS TABLE(tipo text, documento_id uuid, version text, titulo text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT d.tipo::text, d.id, d.version::text, d.titulo::text
 FROM public.documento_legal d
 WHERE d.id IN (public.chilito_documento_vigente('terminos'), public.chilito_documento_vigente('aviso_privacidad'))
   AND NOT EXISTS(SELECT 1 FROM public.privacidad_decision x WHERE x.usuario_id=p_usuario AND x.documento_id=d.id)
 ORDER BY d.tipo
$$;

-- 13.4 Resumen por hora (idempotente: se puede repetir sobre el mismo rango) ----------------------------
CREATE FUNCTION public.chilito_resumir_mediciones(desde timestamptz, hasta timestamptz) RETURNS integer
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE n integer; m integer;
BEGIN
 INSERT INTO public.resumen_hora_huerto AS r (huerto_id, hora, muestras, temperatura_prom, temperatura_min, temperatura_max,
   humedad_aire_prom, humedad_aire_min, humedad_aire_max, luz_prom, luz_max, muestras_sin_agua)
 SELECT huerto_id, date_trunc('hour', medida_en, 'UTC'), count(*),
        round(avg(temperatura_c),1), min(temperatura_c), max(temperatura_c),
        round(avg(humedad_aire_pct),1), min(humedad_aire_pct), max(humedad_aire_pct),
        round(avg(luz_lux),1), max(luz_lux), count(*) FILTER (WHERE deposito_con_agua IS FALSE)
 FROM public.medicion WHERE medida_en >= date_trunc('hour', desde, 'UTC') AND medida_en < date_trunc('hour', hasta, 'UTC')
 GROUP BY 1, 2
 ON CONFLICT (huerto_id, hora) DO UPDATE SET muestras=EXCLUDED.muestras,
   temperatura_prom=EXCLUDED.temperatura_prom, temperatura_min=EXCLUDED.temperatura_min, temperatura_max=EXCLUDED.temperatura_max,
   humedad_aire_prom=EXCLUDED.humedad_aire_prom, humedad_aire_min=EXCLUDED.humedad_aire_min, humedad_aire_max=EXCLUDED.humedad_aire_max,
   luz_prom=EXCLUDED.luz_prom, luz_max=EXCLUDED.luz_max, muestras_sin_agua=EXCLUDED.muestras_sin_agua;
 GET DIAGNOSTICS n = ROW_COUNT;
 INSERT INTO public.resumen_hora_planta AS r (huerto_id, hora, planta_numero, muestras, humedad_prom, humedad_min, humedad_max)
 SELECT m.huerto_id, date_trunc('hour', m.medida_en, 'UTC'), p.planta_numero, count(*),
        round(avg(p.humedad_sustrato_pct),1), min(p.humedad_sustrato_pct), max(p.humedad_sustrato_pct)
 FROM public.medicion m JOIN public.medicion_planta p ON p.medicion_id=m.id
 WHERE m.medida_en >= date_trunc('hour', desde, 'UTC') AND m.medida_en < date_trunc('hour', hasta, 'UTC')
 GROUP BY 1, 2, 3
 ON CONFLICT (huerto_id, hora, planta_numero) DO UPDATE SET muestras=EXCLUDED.muestras,
   humedad_prom=EXCLUDED.humedad_prom, humedad_min=EXCLUDED.humedad_min, humedad_max=EXCLUDED.humedad_max;
 GET DIAGNOSTICS m = ROW_COUNT;
 RETURN n + m;
END $$;

-- 13.5 Anonimizar una cuenta (la usa la tarea periódica a los 15 días de pedirlo) -----------------------
-- Libera sus equipos, cancela sus casos, archiva sus huertos, retira capacidades, borra correos, segundo
-- factor y avisos, y deja la cuenta sin datos personales. La bitácora de consentimientos se conserva como
-- prueba legal (ya sin correo). Las ventas conservan sus datos de facturación.
CREATE FUNCTION public.chilito_anonimizar_cuenta(p_usuario bigint) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF session_user <> 'chilito_pkg_owner' THEN RAISE EXCEPTION 'Solo el propietario anonimiza cuentas'; END IF;
 UPDATE public.dispositivo SET estado='disponible', huerto_id=NULL, vinculado_en=NULL
  WHERE huerto_id IN (SELECT id FROM public.huerto WHERE propietario_id=p_usuario);
 UPDATE public.soporte_caso SET estado='cancelado' WHERE solicitante_id=p_usuario AND estado IN ('abierto','en_atencion');
 UPDATE public.huerto SET estado='archivado' WHERE propietario_id=p_usuario AND estado='activo';
 DELETE FROM public.cuentas_usuario_user_permissions WHERE usuario_id=p_usuario;
 DELETE FROM public.account_emailconfirmation WHERE email_address_id IN (SELECT id FROM public.account_emailaddress WHERE user_id=p_usuario);
 DELETE FROM public.account_emailaddress WHERE user_id=p_usuario;
 DELETE FROM public.mfa_authenticator WHERE user_id=p_usuario;
 UPDATE public.cuentas_usuario SET email='anonimo-' || id || '@anonimo.invalid', password='!anonimizada',
        first_name='', last_name='', alias='', last_login=NULL, is_active=false, anonimizada_en=now()
  WHERE id=p_usuario AND anonimizada_en IS NULL;
 DELETE FROM public.notificacion WHERE destinatario_id=p_usuario;
 INSERT INTO public.auditoria(actor_id, accion, entidad, entidad_id) VALUES (NULL, 'anonimizar_cuenta', 'cuenta', p_usuario::text);
END $$;

-- 13.6 TAREA PERIÓDICA (cada hora, como chilito_pkg_owner; en Cloud SQL con pg_cron) ---------------------
--   SELECT chilito_mantenimiento_periodico();
CREATE FUNCTION public.chilito_mantenimiento_periodico() RETURNS jsonb
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE r jsonb := '{}'::jsonb; n integer; desde timestamptz; u bigint;
BEGIN
 IF session_user <> 'chilito_pkg_owner' THEN RAISE EXCEPTION 'La tarea periódica se ejecuta como chilito_pkg_owner'; END IF;
 -- Resúmenes de las últimas 48 h y, antes de borrar, de todo lo que va a salir del detalle.
 SELECT min(medida_en) INTO desde FROM medicion WHERE medida_en < now() - interval '90 days';
 n := chilito_resumir_mediciones(coalesce(least(desde, now() - interval '48 hours'), now() - interval '48 hours'), now());
 r := r || jsonb_build_object('resumenes', n);
 DELETE FROM medicion WHERE medida_en < now() - interval '90 days';            GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('mediciones_depuradas', n);
 UPDATE codigo_vinculacion SET estado='expirado' WHERE estado='pendiente' AND vence_en < now();
                                                                               GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('codigos_expirados', n);
 UPDATE comando SET estado='expirado', detalle_error='sin_respuesta'
  WHERE estado IN ('pendiente','enviado') AND creado_en < now() - interval '10 minutes';
                                                                               GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('comandos_expirados', n);
 UPDATE soporte_sesion s SET cerrada_en=now(), motivo_cierre='vencida' FROM soporte_caso k
  WHERE k.id=s.caso_id AND s.cerrada_en IS NULL AND now() >= k.autorizacion_vence_en;
                                                                               GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('sesiones_vencidas', n);
 DELETE FROM ia_resumen WHERE generado_en < now() - interval '30 days';       GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('resumenes_ia_depurados', n);
 DELETE FROM notificacion WHERE leida_en < now() - interval '180 days';       GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('notificaciones_depuradas', n);
 DELETE FROM web_idempotencia WHERE creada_en < now() - interval '7 days';    GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('recibos_depurados', n);
 DELETE FROM cuentas_cuotas_acceso WHERE expires < now();                     GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('cuotas_depuradas', n);
 DELETE FROM django_session WHERE expire_date < now();                        GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('sesiones_web_depuradas', n);
 n := 0;
 FOR u IN SELECT id FROM cuentas_usuario WHERE anonimizacion_solicitada_en <= now() - interval '15 days' AND anonimizada_en IS NULL LOOP
  PERFORM chilito_anonimizar_cuenta(u); n := n + 1;
 END LOOP;
 r := r || jsonb_build_object('cuentas_anonimizadas', n);
 UPDATE consulta_producto SET nombre='', correo='anonimizado', mensaje='[eliminado]', anonimizada_en=now()
  WHERE anonimizada_en IS NULL AND estado<>'nueva' AND atendida_en < now() - interval '365 days';
                                                                               GET DIAGNOSTICS n = ROW_COUNT; r := r || jsonb_build_object('consultas_anonimizadas', n);
 RETURN r;
END $$;

-- 13.7 FUNCIONES PARA pgAdmin (solo chilito_pkg_owner) ----------------------------------------------------
-- Dar o quitar una capacidad a una cuenta ya registrada. Devuelve un mensaje con avisos útiles.
--   SELECT chilito_conceder_capacidad('correo@x.com', 'ver_flota', 'Motivo');
--   SELECT chilito_retirar_capacidad('correo@x.com', 'ver_flota', 'Motivo');
CREATE FUNCTION public.chilito_cambiar_capacidad(p_correo text, p_capacidad text, p_conceder boolean, p_motivo text)
RETURNS text LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE u bigint; perm integer; n integer; factor boolean; msg text;
BEGIN
 IF session_user <> 'chilito_pkg_owner' THEN RAISE EXCEPTION 'Ejecútalo como chilito_pkg_owner desde pgAdmin'; END IF;
 IF NOT p_capacidad = ANY(chilito_capacidades()) THEN
  RAISE EXCEPTION 'Capacidad desconocida. Válidas: %', array_to_string(chilito_capacidades(), ', ');
 END IF;
 SELECT id INTO u FROM cuentas_usuario WHERE chilito_identidad_correo(email) = chilito_identidad_correo(p_correo);
 IF NOT FOUND THEN RAISE EXCEPTION 'No existe esa cuenta: la persona debe registrarse primero en la página'; END IF;
 SELECT p.id INTO perm FROM auth_permission p JOIN django_content_type c ON c.id=p.content_type_id
  WHERE c.app_label='cuentas' AND p.codename=p_capacidad;
 PERFORM set_config('chilito.motivo', left(coalesce(p_motivo,''),300), true);
 PERFORM set_config('chilito.actor_id', '', true);
 IF p_conceder THEN
  INSERT INTO cuentas_usuario_user_permissions(usuario_id, permission_id) VALUES (u, perm) ON CONFLICT DO NOTHING;
 ELSE
  DELETE FROM cuentas_usuario_user_permissions WHERE usuario_id=u AND permission_id=perm;
 END IF;
 GET DIAGNOSTICS n = ROW_COUNT;
 msg := CASE WHEN n=0 THEN 'Sin cambios (ya estaba así)' WHEN p_conceder THEN 'Capacidad concedida' ELSE 'Capacidad retirada' END;
 SELECT EXISTS(SELECT 1 FROM mfa_authenticator WHERE user_id=u AND type IN ('totp','webauthn')) INTO factor;
 IF p_conceder AND NOT factor THEN
  msg := msg || '. OJO: no tiene app autenticadora ni llave de acceso; la página le pedirá activarla antes de usar el panel';
 END IF;
 RETURN msg;
END $$;
CREATE FUNCTION public.chilito_conceder_capacidad(p_correo text, p_capacidad text, p_motivo text DEFAULT 'Desde pgAdmin')
RETURNS text LANGUAGE sql AS $$ SELECT public.chilito_cambiar_capacidad(p_correo, p_capacidad, true, p_motivo) $$;
CREATE FUNCTION public.chilito_retirar_capacidad(p_correo text, p_capacidad text, p_motivo text DEFAULT 'Desde pgAdmin')
RETURNS text LANGUAGE sql AS $$ SELECT public.chilito_cambiar_capacidad(p_correo, p_capacidad, false, p_motivo) $$;

-- Nombrar o retirar un SUPER ADMINISTRADOR. Recibe las 10 capacidades (o se le retiran todas).
--   SELECT chilito_designar_super_admin('tu-correo@dominio.com');
--   SELECT chilito_retirar_super_admin('correo@dominio.com');
CREATE FUNCTION public.chilito_designar_super_admin(p_correo text, p_motivo text DEFAULT 'Super administrador designado desde pgAdmin')
RETURNS text LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE c text; msg text;
BEGIN
 FOREACH c IN ARRAY chilito_capacidades() LOOP msg := chilito_cambiar_capacidad(p_correo, c, true, p_motivo); END LOOP;
 RETURN 'Super administrador listo con las 10 capacidades' || coalesce(substring(msg from '\. OJO.*$'), '');
END $$;
CREATE FUNCTION public.chilito_retirar_super_admin(p_correo text, p_motivo text DEFAULT 'Retirado desde pgAdmin')
RETURNS text LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE c text;
BEGIN
 FOREACH c IN ARRAY chilito_capacidades() LOOP PERFORM chilito_cambiar_capacidad(p_correo, c, false, p_motivo); END LOOP;
 RETURN 'La cuenta vuelve a ser normal (sin capacidades)';
END $$;

-- Publicar un texto legal desde pgAdmin (carga inicial). Después se hace desde el panel con «gestionar_legales».
--   SELECT chilito_publicar_documento_legal('terminos', '1.0', 'Términos y condiciones', $texto$ … $texto$);
CREATE FUNCTION public.chilito_publicar_documento_legal(p_tipo text, p_version text, p_titulo text, p_contenido text)
RETURNS uuid LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE i uuid;
BEGIN
 IF session_user <> 'chilito_pkg_owner' THEN RAISE EXCEPTION 'Ejecútalo como chilito_pkg_owner desde pgAdmin'; END IF;
 INSERT INTO documento_legal(tipo, version, titulo, contenido, contenido_sha256, estado)
 VALUES (p_tipo, p_version, p_titulo, p_contenido, repeat('0',64), 'publicada') RETURNING id INTO i;
 RETURN i;
END $$;


-- =====================================================================================================
-- 14. VISTAS DE CONSULTA (para el panel y para pgAdmin). Respetan los permisos de quien consulta.
-- =====================================================================================================

-- Administradores actuales, sus capacidades y si tienen segundo factor fuerte.
CREATE VIEW v_administradores WITH (security_invoker = true) AS
SELECT u.id AS usuario_id, u.email, nullif(btrim(u.first_name || ' ' || u.last_name), '') AS nombre,
       bool_or(p.codename='gestionar_administradores') AS es_super_admin,
       string_agg(p.codename, ', ' ORDER BY p.codename) AS capacidades,
       EXISTS(SELECT 1 FROM mfa_authenticator m WHERE m.user_id=u.id AND m.type IN ('totp','webauthn')) AS segundo_factor,
       u.last_login AS ultimo_acceso
FROM cuentas_usuario u
JOIN cuentas_usuario_user_permissions up ON up.usuario_id=u.id
JOIN auth_permission p ON p.id=up.permission_id
JOIN django_content_type c ON c.id=p.content_type_id AND c.app_label='cuentas'
WHERE p.codename = ANY(chilito_capacidades())
GROUP BY u.id;

-- Historial de capacidades con correos legibles.
CREATE VIEW v_capacidad_historial WITH (security_invoker = true) AS
SELECT h.realizada_en, u.email AS cuenta, h.capacidad, h.accion,
       coalesce(r.email, 'pgAdmin (propietario)') AS realizada_por, h.motivo
FROM capacidad_historial h
JOIN cuentas_usuario u ON u.id=h.usuario_id
LEFT JOIN cuentas_usuario r ON r.id=h.realizada_por_id;

-- BITÁCORA DE CONSENTIMIENTOS: quién (correo o visitante anónimo), qué, qué versión, cuándo, IP y navegador.
CREATE VIEW v_bitacora_consentimientos WITH (security_invoker = true) AS
SELECT d.registrada_en,
       (d.registrada_en AT TIME ZONE 'America/Merida') AS registrada_en_merida,
       CASE WHEN u.id IS NULL THEN 'Visitante anónimo'
            WHEN u.anonimizada_en IS NOT NULL THEN 'Cuenta eliminada'
            ELSE u.email END AS cuenta,
       s.ambito,
       CASE d.acto WHEN 'aceptacion_terminos' THEN 'Términos y condiciones'
                   WHEN 'lectura_aviso' THEN 'Aviso de privacidad' ELSE 'Cookies' END AS que,
       doc.version AS version_documento,
       CASE WHEN d.decision THEN 'Aceptó' ELSE 'Rechazó' END AS decision,
       f.codigo AS finalidad, d.ip_recortada, d.navegador, d.id AS decision_id
FROM privacidad_decision d
JOIN privacidad_sujeto s ON s.id=d.sujeto_id
JOIN documento_legal doc ON doc.id=d.documento_id
LEFT JOIN cuentas_usuario u ON u.id=coalesce(d.usuario_id, s.usuario_id)
LEFT JOIN privacidad_finalidad f ON f.id=d.finalidad_id;

-- Versión vigente de cada texto legal.
CREATE VIEW v_documento_legal_vigente WITH (security_invoker = true) AS
SELECT DISTINCT ON (tipo) tipo, id, version, titulo, publicado_en, contenido_sha256
FROM documento_legal WHERE estado='publicada'
ORDER BY tipo, publicado_en DESC;

-- Estado de cada equipo: huerto, dueño, conexión y última medición.
CREATE VIEW v_estado_equipos WITH (security_invoker = true) AS
SELECT d.id AS dispositivo_id, d.identificador, d.estado, d.conexion, d.ultima_conexion_en, d.firmware_version,
       h.id AS huerto_id, h.nombre AS huerto, u.email AS dueno,
       (SELECT max(m.medida_en) FROM medicion m WHERE m.dispositivo_id=d.id) AS ultima_medicion_en
FROM dispositivo d
LEFT JOIN huerto h ON h.id=d.huerto_id
LEFT JOIN cuentas_usuario u ON u.id=h.propietario_id;

-- =====================================================================================================
-- 15. DATOS INICIALES
--     No crea cuentas, huertos, equipos ni textos legales (los textos se publican en el paso 4).
-- =====================================================================================================

-- Las 10 CAPACIDADES de administración (permisos de Django de la app «cuentas», modelo «usuario»).
-- En Django se consultan con user.has_perm('cuentas.<capacidad>').
INSERT INTO django_content_type(app_label, model) VALUES ('cuentas','usuario');
INSERT INTO auth_permission(name, content_type_id, codename)
SELECT x.nombre, c.id, x.codigo
FROM (VALUES
 ('ver_flota',                 'Ver telemetría de flota'),
 ('atender_soporte',           'Atender soporte remoto (consola remota)'),
 ('gestionar_mantenimientos',  'Corregir y anular cuidados registrados'),
 ('atender_consultas',         'Atender consultas del producto (Consíguelo)'),
 ('gestionar_dispositivos',    'Gestionar inventario y desvinculación de equipos'),
 ('gestionar_ventas',          'Registrar y gestionar ventas'),
 ('gestionar_guias',           'Crear, editar, publicar y retirar guías de cuidado'),
 ('gestionar_legales',         'Subir y publicar versiones de textos legales'),
 ('ver_consentimientos',       'Ver la bitácora de consentimientos'),
 ('gestionar_administradores', 'Super administrador: dar y quitar capacidades')
) AS x(codigo, nombre)
CROSS JOIN django_content_type c WHERE c.app_label='cuentas' AND c.model='usuario';

-- Finalidad opcional de privacidad.
INSERT INTO privacidad_finalidad(id, codigo, descripcion) VALUES
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e04','estadisticas_internas_navegacion','Estadísticas internas voluntarias de navegación');

-- Las 9 guías de cuidado iniciales, publicadas (mismo contenido y fuentes que la versión anterior).
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('799107f9-96d5-5536-86dc-9bc276475df2'::uuid,'germinacion-inicio','¿Cómo comienzo a germinar mis semillas de habanero?','Etapa de germinación. Se hace fuera del sistema, en un semillero aparte con mezcla limpia para semillas. Cubre las semillas con una capa ligera y mantén la mezcla húmeda, sin encharcarla.

Las semillas de chile germinan mejor en un lugar cálido y estable que en uno frío. Cuando asomen los brotes, dales luz abundante: con poca luz, el tallo se alarga y se inclina.

Registrar la germinación solo deja constancia de lo que ya hiciste. El sistema no la realiza ni la comprueba.',10,'publicada','University of Minnesota Extension','https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/growing-peppers',1,now(),now(),NULL,NULL);
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('f849ea28-3a9e-5eae-9d67-ee7dca35aa0a'::uuid,'brotacion-tiempo','¿Cuánto puede tardar en brotar y qué debo observar?','No hay un plazo fijo. Depende de la edad de la semilla, la variedad, la temperatura y la humedad. El habanero puede tardar varias semanas, así que una espera larga no significa por sí sola que la siembra haya fallado.

Mientras tanto, observa que la mezcla siga húmeda y sin charcos, y que no aparezca moho ni mal olor. Si la mezcla se seca por completo o se mantiene empapada, la germinación puede fallar.

Cuando broten, vigila que el tallo no se alargue ni se doble hacia la luz.',20,'publicada','University of Minnesota Extension','https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/growing-peppers',1,now(),now(),NULL,NULL);
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('82e02837-ab58-5847-b9c9-873dad3def6e'::uuid,'trasplante-plantula','¿Cómo reconozco que la plántula está lista para trasplantar?','Etapa de trasplante. Guíate por la plántula y no por el calendario: tallo firme, hojas verdaderas además de las dos primeras, buen color y raíces que ya sostienen la mezcla al sacarla.

Si creció en otro lugar, acostúmbrala poco a poco a la luz y a las condiciones del huerto. Al trasplantar, no entierres el tallo más de lo que estaba y riega después. Si ya tiene flores, puedes retirarlas para que se concentre en crecer.

Las fechas de las guías para exteriores dependen de las heladas y de cada clima. No se aplican tal cual a un huerto interior.',30,'publicada','Oregon State University Extension','https://extension.oregonstate.edu/catalog/ec-1227-grow-your-own-peppers',1,now(),now(),NULL,NULL);
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('26fb7ca5-cd6e-5e36-8687-790308a24f8b'::uuid,'sustrato-perlita','¿Para qué sirve la perlita y cómo reviso el sustrato?','La perlita ayuda a conservar la aireación: mantiene espacios en la mezcla para que entren aire y agua y para que las raíces respiren.

Revisa si el agua drena con facilidad. Si notas compactación, malos olores o acumulación de sales, revisa la mezcla antes de volver a regar. Con el tiempo la mezcla se degrada y pierde esos espacios, así que conviene renovarla cuando deje de drenar bien.

Marcar la revisión hecha declara que ya la realizaste. El sistema no inspecciona el sustrato.',40,'publicada','University of Maryland Extension','https://extension.umd.edu/resource/growing-vegetables-containers-and-salad-tables',1,now(),now(),NULL,NULL);
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('4a0a2210-b48d-52a8-9058-a6c23d3f2cbc'::uuid,'riego-revision','¿Cuándo debo revisar el riego de mis plantas?','Etapa de crecimiento. Revisa antes de regar, no por un horario fijo: toca el sustrato un poco por debajo de la superficie. La velocidad con que se seca cambia con el tamaño de la planta, la luz, la temperatura y el recipiente.

Que una planta se marchite no prueba que le falte agua: el exceso de riego también la marchita. Un sustrato siempre empapado deja a las raíces sin aire y puede dañarlas. Evita que quede agua estancada.

La lectura de humedad, cuando existe, es un dato más. Confírmala revisando la planta y el sustrato.',50,'publicada','University of Maryland Extension','https://extension.umd.edu/resource/growing-vegetables-containers-and-salad-tables',1,now(),now(),NULL,NULL);
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('0cb10161-67a5-5b32-b6e7-2858e80f0e6e'::uuid,'deposito-recarga','¿Qué significa rellenar el depósito y registrar la recarga?','Rellenar es añadir agua limpia al depósito con tus propias manos. Después, «Ya rellené el depósito» guarda la fecha de ese cuidado.

Registrar un cuidado declara una acción que ya realizaste físicamente. No significa que el sistema la haya ejecutado o comprobado.

El flotador detecta nivel bajo. No mide los litros restantes ni confirma que el depósito esté lleno, así que comprueba el nivel a simple vista al rellenarlo.',60,'publicada','','',1,now(),now(),NULL,NULL);
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('492a0e27-a4ad-5bff-bc1a-d693e5a6cb6a'::uuid,'mangueras-goteros','¿Cómo reviso las mangueras y los goteros?','Mira que las mangueras no estén dobladas, aplastadas ni sueltas, y que no haya fugas en las uniones. Comprueba que los cables y las conexiones estén secos.

Observa si cada gotero entrega agua de forma parecida a los demás. Un gotero que no gotea puede estar obstruido o tener la manguera doblada.

Si encuentras una fuga o algo no parece seguro, usa el paro físico del equipo y solicita soporte técnico. «Registrar inspección» declara que hiciste la revisión; el sistema no la comprueba.',70,'publicada','','',1,now(),now(),NULL,NULL);
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('75729f99-13f0-5f6d-95e8-acd12f6d7268'::uuid,'cosecha-registro','¿Cómo identifico y registro una cosecha?','Etapa de cosecha. Fíjate en el fruto y no en una fecha: firme, de tamaño completo y con el color final de su variedad. El tiempo y la cantidad de frutos varían de una planta a otra.

Corta con utensilios limpios y deja un poco de tallo unido al fruto, sin tirar para no romper las ramas. Usa guantes: el habanero irrita la piel y los ojos. Retirar los frutos maduros con regularidad favorece que la planta siga produciendo.

Después, «Registrar cosecha» guarda la fecha de lo que ya hiciste. El sistema no detecta la cosecha ni la comprueba.',80,'publicada','Oregon State University Extension','https://extension.oregonstate.edu/catalog/ec-1227-grow-your-own-peppers',1,now(),now(),NULL,NULL);
INSERT INTO public.guia_cuidado
 (id,clave,pregunta,respuesta,orden,estado,fuente_nombre,fuente_url,version,creado_en,actualizado_en,creado_por_id,actualizado_por_id)
 VALUES ('e4848719-fa76-5bbe-8267-8c140f0db5ac'::uuid,'sin-lecturas','¿Qué hago si no hay lecturas o el dispositivo está desconectado?','Sin lecturas válidas no puede deducirse el estado de la planta: «sin datos» no significa que esté bien ni que le falte agua. Una lectura antigua tampoco describe lo que ocurre ahora.

Mientras tanto, revisa directamente las plantas, el sustrato y el depósito. Comprueba que el equipo tenga corriente y que tu red Wi-Fi funcione.

Si el problema continúa, repórtalo en Soporte técnico.',90,'publicada','','',1,now(),now(),NULL,NULL);


-- =====================================================================================================
-- 16. PRIVILEGIOS DE LOS ROLES
--     Lo que no aparece aquí, ese rol NO lo puede hacer aunque lo intente.
-- =====================================================================================================
DO $$ BEGIN
 EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
 EXECUTE format('GRANT CONNECT ON DATABASE %I TO chilito_pkg_runtime, chilito_pkg_iot', current_database());
END $$;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO chilito_pkg_runtime, chilito_pkg_iot;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;

-- ---------------------------------------------------------------------------------------------- RUNTIME
-- Lectura: la página lee casi todo; Django decide qué muestra a cada cuenta.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chilito_pkg_runtime;

-- Django, sesiones, cuotas, correos y segundo factor (datos de trabajo de allauth).
GRANT INSERT, UPDATE, DELETE ON django_session, cuentas_cuotas_acceso, account_emailaddress,
 account_emailconfirmation TO chilito_pkg_runtime;
GRANT INSERT, DELETE ON mfa_authenticator TO chilito_pkg_runtime;
GRANT UPDATE (data, last_used_at, user_id, type, created_at) ON mfa_authenticator TO chilito_pkg_runtime;

-- Cuentas: registro y perfil. NO puede tocar is_active, is_staff, is_superuser ni anonimizada_en.
GRANT INSERT ON cuentas_usuario TO chilito_pkg_runtime;
GRANT UPDATE (email, password, last_login, first_name, last_name, alias, bienvenida_atendida_en,
 anonimizacion_solicitada_en) ON cuentas_usuario TO chilito_pkg_runtime;
-- Capacidades: el trigger exige un super administrador como actor.
GRANT INSERT, DELETE ON cuentas_usuario_user_permissions TO chilito_pkg_runtime;

-- Huertos, plantas y vinculación.
GRANT INSERT ON huerto TO chilito_pkg_runtime;
GRANT UPDATE (nombre, estado, archivado_en) ON huerto TO chilito_pkg_runtime;
GRANT UPDATE (nombre, fecha_siembra, etapa, etapa_desde) ON huerto_planta TO chilito_pkg_runtime;
GRANT INSERT ON dispositivo TO chilito_pkg_runtime;
GRANT UPDATE (estado, huerto_id, vinculado_en, credencial_hash, retirado_en) ON dispositivo TO chilito_pkg_runtime;
GRANT INSERT ON codigo_vinculacion TO chilito_pkg_runtime;
GRANT UPDATE (estado, cerrado_en, dispositivo_id) ON codigo_vinculacion TO chilito_pkg_runtime;

-- Comandos (también puede marcarlos enviados si Django publica en MQTT), cuidados y guías.
GRANT INSERT ON comando, cuidado, cuidado_revision, guia_cuidado TO chilito_pkg_runtime;
GRANT UPDATE (estado, enviado_en, resuelto_en, detalle_error) ON comando TO chilito_pkg_runtime;
GRANT UPDATE (pregunta, respuesta, orden, estado, fuente_nombre, fuente_url, version, actualizado_en,
 actualizado_por_id) ON guia_cuidado TO chilito_pkg_runtime;

-- Soporte.
GRANT INSERT ON soporte_caso, soporte_sesion TO chilito_pkg_runtime;
GRANT UPDATE (estado, atendido_por_id, tomado_en, resultado, nota_resolucion, cerrado_en,
 autorizacion_revocada_en) ON soporte_caso TO chilito_pkg_runtime;
GRANT UPDATE (cerrada_en, motivo_cierre) ON soporte_sesion TO chilito_pkg_runtime;

-- Comunicación y ventas.
GRANT INSERT ON notificacion, consulta_producto, venta TO chilito_pkg_runtime;
GRANT UPDATE (leida_en, resuelta_en) ON notificacion TO chilito_pkg_runtime;
GRANT UPDATE (estado, atendida_por_id, atendida_en) ON consulta_producto TO chilito_pkg_runtime;
GRANT UPDATE (estado, intentos, ultimo_intento_en, aceptado_en) ON correo_pendiente TO chilito_pkg_runtime;
GRANT UPDATE (importe_recibido_mxn, referencia_pago, modalidad_entrega, entrega_prevista_en, entregada_en, nota,
 estado, cancelada_en) ON venta TO chilito_pkg_runtime;

-- Legal y privacidad.
GRANT INSERT, DELETE ON documento_legal TO chilito_pkg_runtime;
GRANT UPDATE (version, titulo, contenido, contenido_sha256, estado, actualizado_en, publicado_por_id,
 publicado_en) ON documento_legal TO chilito_pkg_runtime;
GRANT INSERT ON privacidad_sujeto, privacidad_decision, privacidad_preferencia, conteo_navegacion TO chilito_pkg_runtime;
GRANT UPDATE (usuario_id) ON privacidad_sujeto TO chilito_pkg_runtime;
GRANT UPDATE (decision_id, actualizada_en) ON privacidad_preferencia TO chilito_pkg_runtime;
GRANT UPDATE (visitas) ON conteo_navegacion TO chilito_pkg_runtime;

-- Auditoría e idempotencia: solo insertar.
GRANT INSERT ON auditoria, web_idempotencia TO chilito_pkg_runtime;

-- ---------------------------------------------------------------------------------------------- IOT / IA
-- Lee lo necesario de su huerto y equipo; escribe telemetría, actuaciones, eventos, resultados de comandos
-- y autodiagnósticos, avisos al dueño y resúmenes de IA. No ve cuentas, legal, soporte ni ventas.
GRANT SELECT ON huerto, huerto_planta, dispositivo, comando, autodiagnostico, autodiagnostico_revision,
 medicion, medicion_planta, resumen_hora_huerto, resumen_hora_planta, actuacion, dispositivo_evento,
 cuidado, cuidado_revision, ia_resumen TO chilito_pkg_iot;
GRANT INSERT ON medicion, medicion_planta, actuacion, dispositivo_evento, autodiagnostico_revision,
 notificacion, ia_resumen TO chilito_pkg_iot;
GRANT INSERT, UPDATE ON resumen_hora_huerto, resumen_hora_planta TO chilito_pkg_iot;
GRANT UPDATE (conexion, ultima_conexion_en, firmware_version) ON dispositivo TO chilito_pkg_iot;
GRANT UPDATE (estado, enviado_en, resuelto_en, detalle_error) ON comando TO chilito_pkg_iot;
GRANT UPDATE (estado, resultado_general, completado_en) ON autodiagnostico TO chilito_pkg_iot;

-- ---------------------------------------------------------------------------------------------- COMUNES
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO chilito_pkg_runtime, chilito_pkg_iot;
-- Funciones de apoyo (las usan los triggers con los permisos de quien escribe).
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO chilito_pkg_runtime, chilito_pkg_iot;
-- …excepto las de administración y tareas, que son solo del propietario.
REVOKE EXECUTE ON FUNCTION chilito_cambiar_capacidad(text,text,boolean,text), chilito_conceder_capacidad(text,text,text),
 chilito_retirar_capacidad(text,text,text), chilito_designar_super_admin(text,text), chilito_retirar_super_admin(text,text),
 chilito_publicar_documento_legal(text,text,text,text), chilito_anonimizar_cuenta(bigint),
 chilito_mantenimiento_periodico() FROM chilito_pkg_runtime, chilito_pkg_iot;
-- La página no resume ni vincula por su cuenta fuera de su función; el servicio IoT no vincula.
REVOKE EXECUTE ON FUNCTION chilito_vincular_dispositivo(text,text), chilito_desvincular_dispositivo(bigint) FROM chilito_pkg_iot;

-- Lo que el propietario cree en el futuro tampoco quedará abierto a todos.
ALTER DEFAULT PRIVILEGES FOR ROLE chilito_pkg_owner IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE chilito_pkg_owner IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

COMMIT;

-- Comprobación rápida (opcional): 46 tablas y 5 vistas.
-- SELECT count(*) FILTER (WHERE table_type='BASE TABLE') AS tablas, count(*) FILTER (WHERE table_type='VIEW') AS vistas
-- FROM information_schema.tables WHERE table_schema='public';
