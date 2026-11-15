"""Reglas de la base v2 que los modelos no declaran. El SQL está copiado de el_chilito_base_v2.sql.

No incluye la sección 0 ni BEGIN/COMMIT: Django ejecuta la migración en su propia transacción."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('sessions', '0001_initial'),
        ('account', '0009_emailaddress_unique_primary_email'),
        ('mfa', '0003_authenticator_type_uniq'),
        ('cuentas', '0001_initial'),
        ('huerto', '0001_initial'),
        ('datos', '0001_initial'),
        ('privacidad', '0001_initial'),
        ('web', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(sql=[
            # Funciones de apoyo (sección 1)
            (r"""
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
""", None),
            # Caché de cuotas de acceso (sección 3)
            (r"""
-- Caché de Django en la base (formato de «createcachetable»): límites de intentos y marcas temporales.
CREATE TABLE cuentas_cuotas_acceso (
 cache_key varchar(255) NOT NULL PRIMARY KEY,
 value text NOT NULL,
 expires timestamptz NOT NULL);
CREATE INDEX cuentas_cuotas_acceso_expires_c8e0ee83 ON cuentas_cuotas_acceso(expires);
""", None),
            # Valores por defecto de las columnas heredadas de AbstractUser (sección 3)
            (r"""
ALTER TABLE cuentas_usuario
 ALTER COLUMN is_superuser SET DEFAULT false, ALTER COLUMN first_name SET DEFAULT '', ALTER COLUMN last_name SET DEFAULT '',
 ALTER COLUMN is_staff SET DEFAULT false, ALTER COLUMN is_active SET DEFAULT true, ALTER COLUMN date_joined SET DEFAULT now();
""", None),
            # CHECK (secciones 3 a 11)
            (r"""
ALTER TABLE cuentas_usuario ADD CONSTRAINT usuario_alias_vacio_o_con_texto CHECK (alias = '' OR alias ~ '\S');
ALTER TABLE cuentas_usuario ADD CONSTRAINT usuario_correo_con_arroba CHECK (email ~ '^[^@\s]+@[^@\s]+$');
ALTER TABLE cuentas_usuario ADD CONSTRAINT usuario_sin_privilegios_django CHECK (NOT is_staff AND NOT is_superuser);
ALTER TABLE cuentas_usuario ADD CONSTRAINT usuario_anonimizada_inactiva CHECK (anonimizada_en IS NULL OR NOT is_active);
ALTER TABLE mfa_authenticator ADD CONSTRAINT mfa_tipo_valido CHECK (type IN ('totp','recovery_codes','webauthn'));
ALTER TABLE huerto ADD CONSTRAINT huerto_nombre_significativo CHECK (nombre ~ '\S');
ALTER TABLE huerto ADD CONSTRAINT huerto_solo_yucatan CHECK (zona_horaria = 'America/Merida');
ALTER TABLE huerto ADD CONSTRAINT huerto_estado_valido CHECK (estado IN ('activo','archivado'));
ALTER TABLE huerto ADD CONSTRAINT huerto_archivo_coherente CHECK ((estado='activo' AND archivado_en IS NULL)
                                         OR (estado='archivado' AND archivado_en IS NOT NULL AND archivado_en >= creado_en));
ALTER TABLE huerto_planta ADD CONSTRAINT planta_numero_1_3 CHECK (numero BETWEEN 1 AND 3);
ALTER TABLE huerto_planta ADD CONSTRAINT planta_nombre_significativo CHECK (nombre ~ '\S');
ALTER TABLE huerto_planta ADD CONSTRAINT planta_etapa_valida CHECK (etapa IN ('sin_sembrar','germinacion','plantula','crecimiento','floracion','fructificacion'));
ALTER TABLE huerto_planta ADD CONSTRAINT planta_etapa_fecha CHECK ((etapa='sin_sembrar' AND etapa_desde IS NULL) OR (etapa<>'sin_sembrar' AND etapa_desde IS NOT NULL));
ALTER TABLE huerto_planta ADD CONSTRAINT planta_fechas_coherentes CHECK (fecha_siembra IS NULL OR etapa_desde IS NULL OR etapa_desde >= fecha_siembra);
ALTER TABLE huerto_planta_etapa ADD CONSTRAINT planta_etapa_hist_valida CHECK (etapa IN ('sin_sembrar','germinacion','plantula','crecimiento','floracion','fructificacion'));
ALTER TABLE dispositivo ADD CONSTRAINT dispositivo_identificador_valido CHECK (identificador ~ '^[A-Za-z0-9][A-Za-z0-9-]{3,31}$');
ALTER TABLE dispositivo ADD CONSTRAINT dispositivo_credencial_resumida CHECK (length(credencial_hash) BETWEEN 32 AND 255 AND credencial_hash !~ '\s');
ALTER TABLE dispositivo ADD CONSTRAINT dispositivo_firmware_valido CHECK (firmware_version = '' OR firmware_version ~ '^[A-Za-z0-9._-]{1,32}$');
ALTER TABLE dispositivo ADD CONSTRAINT dispositivo_estado_valido CHECK (estado IN ('disponible','vinculado','retirado'));
ALTER TABLE dispositivo ADD CONSTRAINT dispositivo_conexion_valida CHECK (conexion IN ('nunca','en_linea','desconectado'));
ALTER TABLE dispositivo ADD CONSTRAINT dispositivo_vinculo_coherente CHECK (
      (estado='vinculado'  AND huerto_id IS NOT NULL AND vinculado_en IS NOT NULL AND retirado_en IS NULL)
   OR (estado='disponible' AND huerto_id IS NULL AND vinculado_en IS NULL AND retirado_en IS NULL)
   OR (estado='retirado'   AND huerto_id IS NULL AND vinculado_en IS NULL AND retirado_en IS NOT NULL));
ALTER TABLE dispositivo ADD CONSTRAINT dispositivo_conexion_coherente CHECK ((conexion='nunca') = (ultima_conexion_en IS NULL));
ALTER TABLE codigo_vinculacion ADD CONSTRAINT codigo_hash_hex CHECK (codigo_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE codigo_vinculacion ADD CONSTRAINT codigo_vigencia_10min CHECK (vence_en > generado_en AND vence_en <= generado_en + interval '10 minutes');
ALTER TABLE codigo_vinculacion ADD CONSTRAINT codigo_estado_valido CHECK (estado IN ('pendiente','utilizado','expirado','cancelado'));
ALTER TABLE codigo_vinculacion ADD CONSTRAINT codigo_cierre_coherente CHECK (
      (estado='pendiente' AND cerrado_en IS NULL AND dispositivo_id IS NULL)
   OR (estado='utilizado' AND cerrado_en IS NOT NULL AND cerrado_en <= vence_en AND dispositivo_id IS NOT NULL)
   OR (estado IN ('expirado','cancelado') AND cerrado_en IS NOT NULL AND dispositivo_id IS NULL));
ALTER TABLE dispositivo_evento ADD CONSTRAINT disp_evento_tipo_valido CHECK (tipo IN ('alta','vinculado','desvinculado','conectado','desconectado',
   'error','reinicio','credencial_rotada','firmware_actualizado','retirado'));
ALTER TABLE medicion ADD CONSTRAINT medicion_no_futura CHECK (medida_en <= recibida_en + interval '5 minutes');
ALTER TABLE medicion ADD CONSTRAINT medicion_temperatura_rango CHECK (temperatura_c BETWEEN -20 AND 70);
ALTER TABLE medicion ADD CONSTRAINT medicion_humedad_rango CHECK (humedad_aire_pct BETWEEN 0 AND 100);
ALTER TABLE medicion ADD CONSTRAINT medicion_luz_rango CHECK (luz_lux BETWEEN 0 AND 200000);
ALTER TABLE medicion_planta ADD CONSTRAINT med_planta_numero_1_3 CHECK (planta_numero BETWEEN 1 AND 3);
ALTER TABLE medicion_planta ADD CONSTRAINT med_planta_humedad_rango CHECK (humedad_sustrato_pct BETWEEN 0 AND 100);
ALTER TABLE medicion_planta ADD CONSTRAINT med_planta_adc_rango CHECK (adc_crudo BETWEEN 0 AND 4095);
ALTER TABLE resumen_hora_huerto ADD CONSTRAINT resumen_huerto_hora_exacta CHECK (hora = date_trunc('hour', hora, 'UTC'));
ALTER TABLE resumen_hora_huerto ADD CONSTRAINT resumen_huerto_muestras CHECK (muestras > 0 AND muestras_sin_agua BETWEEN 0 AND muestras);
ALTER TABLE resumen_hora_planta ADD CONSTRAINT resumen_planta_numero CHECK (planta_numero BETWEEN 1 AND 3);
ALTER TABLE resumen_hora_planta ADD CONSTRAINT resumen_planta_hora_exacta CHECK (hora = date_trunc('hour', hora, 'UTC'));
ALTER TABLE resumen_hora_planta ADD CONSTRAINT resumen_planta_muestras CHECK (muestras > 0);
ALTER TABLE comando ADD CONSTRAINT comando_tipo_valido CHECK (tipo IN ('regar','lampara_apagar','lampara_automatico','autodiagnostico',
   'reiniciar','probar_bomba','ventilador_encender','ventilador_apagar','lectura_inmediata'));
ALTER TABLE comando ADD CONSTRAINT comando_origen_valido CHECK (origen IN ('usuario','soporte'));
ALTER TABLE comando ADD CONSTRAINT comando_tipo_por_origen CHECK (origen='soporte' OR tipo IN ('regar','lampara_apagar','lampara_automatico','autodiagnostico'));
ALTER TABLE comando ADD CONSTRAINT comando_sesion_por_origen CHECK ((origen='soporte') = (sesion_id IS NOT NULL));
ALTER TABLE comando ADD CONSTRAINT comando_planta_por_tipo CHECK ((tipo IN ('regar','probar_bomba')) = (planta_numero IS NOT NULL)
                                        AND (planta_numero IS NULL OR planta_numero BETWEEN 1 AND 3));
ALTER TABLE comando ADD CONSTRAINT comando_duracion_por_tipo CHECK ((tipo IN ('regar','probar_bomba')) = (duracion_s IS NOT NULL)
                                          AND (duracion_s IS NULL OR duracion_s BETWEEN 1 AND 30));
ALTER TABLE comando ADD CONSTRAINT comando_estado_valido CHECK (estado IN ('pendiente','enviado','confirmado','fallido','expirado'));
ALTER TABLE comando ADD CONSTRAINT comando_fechas_coherentes CHECK (
      (estado='pendiente' AND enviado_en IS NULL AND resuelto_en IS NULL)
   OR (estado='enviado'   AND enviado_en IS NOT NULL AND enviado_en >= creado_en AND resuelto_en IS NULL)
   OR (estado='confirmado' AND enviado_en IS NOT NULL AND resuelto_en IS NOT NULL AND enviado_en >= creado_en AND resuelto_en >= enviado_en)
   OR (estado IN ('fallido','expirado') AND resuelto_en IS NOT NULL AND resuelto_en >= creado_en AND (enviado_en IS NULL OR resuelto_en >= enviado_en)));
ALTER TABLE comando ADD CONSTRAINT comando_error_solo_si_falla CHECK (detalle_error = '' OR estado IN ('fallido','expirado'));
ALTER TABLE actuacion ADD CONSTRAINT actuacion_actuador_valido CHECK (actuador IN ('bomba','lampara','ventilador'));
ALTER TABLE actuacion ADD CONSTRAINT actuacion_planta_si_bomba CHECK ((actuador='bomba') = (planta_numero IS NOT NULL)
                                          AND (planta_numero IS NULL OR planta_numero BETWEEN 1 AND 3));
ALTER TABLE actuacion ADD CONSTRAINT actuacion_accion_valida CHECK (accion IN ('encendido','apagado'));
ALTER TABLE actuacion ADD CONSTRAINT actuacion_duracion CHECK (duracion_s IS NULL OR (duracion_s BETWEEN 1 AND 600));
ALTER TABLE actuacion ADD CONSTRAINT actuacion_origen_valido CHECK (origen IN ('automatico','usuario','soporte'));
ALTER TABLE actuacion ADD CONSTRAINT actuacion_origen_comando CHECK ((origen='automatico') = (comando_id IS NULL));
ALTER TABLE autodiagnostico ADD CONSTRAINT autodiag_estado_valido CHECK (estado IN ('en_curso','completado','sin_respuesta'));
ALTER TABLE autodiagnostico ADD CONSTRAINT autodiag_resultado_valido CHECK (resultado_general IN ('correcto','con_fallas'));
ALTER TABLE autodiagnostico ADD CONSTRAINT autodiag_cierre_coherente CHECK (
      (estado='en_curso' AND completado_en IS NULL AND resultado_general IS NULL)
   OR (estado='completado' AND completado_en IS NOT NULL AND completado_en >= iniciado_en AND resultado_general IS NOT NULL)
   OR (estado='sin_respuesta' AND completado_en IS NOT NULL AND completado_en >= iniciado_en AND resultado_general IS NULL));
ALTER TABLE autodiagnostico_revision ADD CONSTRAINT revision_componente_valido CHECK (componente IN ('conexion','sensor_ambiente','sensor_luz',
   'sensor_sustrato_1','sensor_sustrato_2','sensor_sustrato_3','flotador',
   'bomba_1','bomba_2','bomba_3','lampara','ventilador'));
ALTER TABLE autodiagnostico_revision ADD CONSTRAINT revision_resultado_valido CHECK (resultado IN ('correcto','falla','sin_respuesta','no_instalado'));
ALTER TABLE cuidado ADD CONSTRAINT cuidado_tipo_valido CHECK (tipo IN ('rellenar_deposito','sustrato','germinacion','cosecha','inspeccion'));
ALTER TABLE cuidado ADD CONSTRAINT cuidado_planta_por_tipo CHECK (
      (tipo='rellenar_deposito' AND planta_numero IS NULL)
   OR (tipo IN ('sustrato','germinacion','cosecha') AND planta_numero IS NOT NULL AND planta_numero BETWEEN 1 AND 3)
   OR (tipo='inspeccion' AND (planta_numero IS NULL OR planta_numero BETWEEN 1 AND 3)));
ALTER TABLE cuidado ADD CONSTRAINT cuidado_chiles_solo_cosecha CHECK (chiles_cosechados IS NULL OR (tipo='cosecha' AND chiles_cosechados BETWEEN 0 AND 999));
ALTER TABLE cuidado ADD CONSTRAINT cuidado_fecha_realista CHECK (realizado_en <= registrado_en + interval '5 minutes'
                                       AND realizado_en >= registrado_en - interval '7 days');
ALTER TABLE cuidado_revision ADD CONSTRAINT revision_cuidado_numero CHECK (numero >= 1);
ALTER TABLE cuidado_revision ADD CONSTRAINT revision_cuidado_tipo CHECK (tipo IN ('correccion','anulacion'));
ALTER TABLE cuidado_revision ADD CONSTRAINT revision_cuidado_motivo CHECK (motivo ~ '\S');
ALTER TABLE cuidado_revision ADD CONSTRAINT revision_cuidado_coherente CHECK (
      (tipo='anulacion' AND tipo_corregido IS NULL AND planta_corregida IS NULL AND chiles_corregidos IS NULL)
   OR (tipo='correccion' AND (
         (tipo_corregido='rellenar_deposito' AND planta_corregida IS NULL)
      OR (tipo_corregido IN ('sustrato','germinacion','cosecha') AND planta_corregida IS NOT NULL AND planta_corregida BETWEEN 1 AND 3)
      OR (tipo_corregido='inspeccion' AND (planta_corregida IS NULL OR planta_corregida BETWEEN 1 AND 3)))
      AND (chiles_corregidos IS NULL OR (tipo_corregido='cosecha' AND chiles_corregidos BETWEEN 0 AND 999))));
ALTER TABLE guia_cuidado ADD CONSTRAINT guia_pregunta_significativa CHECK (pregunta ~ '\S');
ALTER TABLE guia_cuidado ADD CONSTRAINT guia_respuesta_significativa CHECK (respuesta ~ '\S' AND length(respuesta) <= 4000);
ALTER TABLE guia_cuidado ADD CONSTRAINT guia_clave_valida CHECK (clave ~ '^[a-z0-9]+(-[a-z0-9]+)*$');
ALTER TABLE guia_cuidado ADD CONSTRAINT guia_orden_valido CHECK (orden BETWEEN 1 AND 9999);
ALTER TABLE guia_cuidado ADD CONSTRAINT guia_estado_valido CHECK (estado IN ('borrador','publicada','retirada'));
ALTER TABLE guia_cuidado ADD CONSTRAINT guia_version_valida CHECK (version >= 1);
ALTER TABLE guia_cuidado ADD CONSTRAINT guia_fuente_valida CHECK (fuente_url = '' OR (fuente_url ~ '^https?://[^[:space:]]+$' AND fuente_nombre <> ''));
ALTER TABLE soporte_caso ADD CONSTRAINT caso_incidente_valido CHECK (incidente IN ('bomba','humedad','lampara','conexion','otro'));
ALTER TABLE soporte_caso ADD CONSTRAINT caso_consentimiento_explicito CHECK (consentimiento);
ALTER TABLE soporte_caso ADD CONSTRAINT caso_autorizacion_24h CHECK (autorizacion_vence_en > autorizada_en AND autorizacion_vence_en <= autorizada_en + interval '24 hours');
ALTER TABLE soporte_caso ADD CONSTRAINT caso_revocacion_coherente CHECK (autorizacion_revocada_en IS NULL OR autorizacion_revocada_en >= autorizada_en);
ALTER TABLE soporte_caso ADD CONSTRAINT caso_estado_valido CHECK (estado IN ('abierto','en_atencion','resuelto','cancelado'));
ALTER TABLE soporte_caso ADD CONSTRAINT caso_resultado_valido CHECK (resultado IN ('solucionado','sin_falla','sin_respuesta','otro'));
ALTER TABLE soporte_caso ADD CONSTRAINT caso_otro_con_nota CHECK (resultado IS DISTINCT FROM 'otro' OR nota_resolucion ~ '\S');
ALTER TABLE soporte_caso ADD CONSTRAINT caso_estado_coherente CHECK (
      (estado='abierto'     AND atendido_por_id IS NULL AND tomado_en IS NULL AND resultado IS NULL AND cerrado_en IS NULL)
   OR (estado='en_atencion' AND atendido_por_id IS NOT NULL AND tomado_en IS NOT NULL AND tomado_en >= creado_en AND resultado IS NULL AND cerrado_en IS NULL)
   OR (estado='resuelto'    AND atendido_por_id IS NOT NULL AND resultado IS NOT NULL AND cerrado_en IS NOT NULL AND cerrado_en >= creado_en AND autorizacion_revocada_en IS NOT NULL)
   OR (estado='cancelado'   AND resultado IS NULL AND cerrado_en IS NOT NULL AND cerrado_en >= creado_en AND autorizacion_revocada_en IS NOT NULL));
ALTER TABLE soporte_sesion ADD CONSTRAINT sesion_cierre_coherente CHECK ((cerrada_en IS NULL AND motivo_cierre='')
   OR (cerrada_en IS NOT NULL AND cerrada_en >= iniciada_en AND motivo_cierre IN ('manual','revocada','caso_cerrado','vencida','cierre_sesion')));
ALTER TABLE notificacion ADD CONSTRAINT notif_origen_valido CHECK (origen IN ('dispositivo','ia','legal','soporte','vinculacion','sistema'));
ALTER TABLE notificacion ADD CONSTRAINT notif_severidad_valida CHECK (severidad IN ('informacion','advertencia','critico'));
ALTER TABLE notificacion ADD CONSTRAINT notif_titulo_significativo CHECK (titulo ~ '\S');
ALTER TABLE notificacion ADD CONSTRAINT notif_enlace_interno CHECK (enlace = '' OR enlace ~ '^#[A-Za-z0-9/_-]{1,119}$');
ALTER TABLE notificacion ADD CONSTRAINT notif_fechas CHECK ((leida_en IS NULL OR leida_en >= creada_en) AND (resuelta_en IS NULL OR resuelta_en >= creada_en));
ALTER TABLE ia_resumen ADD CONSTRAINT ia_contenido_significativo CHECK (contenido ~ '\S');
ALTER TABLE ia_resumen ADD CONSTRAINT ia_modelo_significativo CHECK (modelo ~ '\S');
ALTER TABLE ia_resumen ADD CONSTRAINT ia_datos_previos CHECK (datos_hasta <= generado_en + interval '5 minutes');
ALTER TABLE consulta_producto ADD CONSTRAINT consulta_correo_significativo CHECK (correo ~ '\S');
ALTER TABLE consulta_producto ADD CONSTRAINT consulta_mensaje_significativo CHECK (mensaje ~ '\S');
ALTER TABLE consulta_producto ADD CONSTRAINT consulta_huella_valida CHECK (huella ~ '^[0-9a-f]{64}$');
ALTER TABLE consulta_producto ADD CONSTRAINT consulta_estado_valido CHECK (estado IN ('nueva','atendida','archivada'));
ALTER TABLE consulta_producto ADD CONSTRAINT consulta_atencion_coherente CHECK (
      (estado='nueva' AND atendida_en IS NULL AND atendida_por_id IS NULL AND anonimizada_en IS NULL)
   OR (estado IN ('atendida','archivada') AND atendida_en IS NOT NULL AND atendida_por_id IS NOT NULL));
ALTER TABLE correo_pendiente ADD CONSTRAINT correo_tipo_valido CHECK (tipo IN ('caso_nuevo','consulta_nueva'));
ALTER TABLE correo_pendiente ADD CONSTRAINT correo_referencia_coherente CHECK ((tipo='caso_nuevo' AND caso_id IS NOT NULL AND consulta_id IS NULL)
                                            OR (tipo='consulta_nueva' AND consulta_id IS NOT NULL AND caso_id IS NULL));
ALTER TABLE correo_pendiente ADD CONSTRAINT correo_estado_valido CHECK (estado IN ('pendiente','aceptado_smtp','fallido'));
ALTER TABLE correo_pendiente ADD CONSTRAINT correo_intentos_limite CHECK (intentos BETWEEN 0 AND 5);
ALTER TABLE correo_pendiente ADD CONSTRAINT correo_aceptacion_coherente CHECK ((estado='aceptado_smtp') = (aceptado_en IS NOT NULL));
ALTER TABLE venta ADD CONSTRAINT venta_nombre_significativo CHECK (comprador_nombre ~ '\S');
ALTER TABLE venta ADD CONSTRAINT venta_correo_valido CHECK (comprador_correo ~ '^[^@\s]+@[^@\s]+$');
ALTER TABLE venta ADD CONSTRAINT venta_municipio_significativo CHECK (municipio ~ '\S');
ALTER TABLE venta ADD CONSTRAINT venta_precio_valido CHECK (precio_mxn > 0 AND precio_mxn <= 99999999.99);
ALTER TABLE venta ADD CONSTRAINT venta_importe_valido CHECK (importe_recibido_mxn >= 0 AND importe_recibido_mxn <= precio_mxn);
ALTER TABLE venta ADD CONSTRAINT venta_referencia_una_linea CHECK (referencia_pago !~ '[\r\n]');
ALTER TABLE venta ADD CONSTRAINT venta_modalidad_valida CHECK (modalidad_entrega IN ('domicilio','recogida'));
ALTER TABLE venta ADD CONSTRAINT venta_entrega_coherente CHECK ((entregada_en IS NULL OR entregada_en >= vendida_en)
                                        AND (entrega_prevista_en IS NULL OR entrega_prevista_en >= vendida_en));
ALTER TABLE venta ADD CONSTRAINT venta_estado_valido CHECK ((estado='vigente' AND cancelada_en IS NULL) OR (estado='cancelada' AND cancelada_en IS NOT NULL));
ALTER TABLE documento_legal ADD CONSTRAINT legal_tipo_valido CHECK (tipo IN ('terminos','aviso_privacidad','politica_cookies'));
ALTER TABLE documento_legal ADD CONSTRAINT legal_version_formato CHECK (version ~ '^[0-9]{1,3}\.[0-9]{1,3}(\.[0-9]{1,3})?$');
ALTER TABLE documento_legal ADD CONSTRAINT legal_titulo_significativo CHECK (titulo ~ '\S');
ALTER TABLE documento_legal ADD CONSTRAINT legal_contenido_significativo CHECK (contenido ~ '\S' AND length(contenido) <= 200000);
ALTER TABLE documento_legal ADD CONSTRAINT legal_hash_hex CHECK (contenido_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE documento_legal ADD CONSTRAINT legal_estado_valido CHECK (estado IN ('borrador','publicada'));
ALTER TABLE documento_legal ADD CONSTRAINT legal_publicacion_coherente CHECK ((estado='borrador') = (publicado_en IS NULL));
ALTER TABLE privacidad_finalidad ADD CONSTRAINT priv_finalidad_codigo_valido CHECK (codigo ~ '^[a-z][a-z0-9_]{0,63}$');
ALTER TABLE privacidad_finalidad ADD CONSTRAINT priv_finalidad_descripcion CHECK (descripcion ~ '\S');
ALTER TABLE privacidad_sujeto ADD CONSTRAINT priv_sujeto_ambito_valido CHECK (ambito IN ('cuenta','navegador'));
ALTER TABLE privacidad_sujeto ADD CONSTRAINT priv_sujeto_cuenta_con_usuario CHECK (ambito <> 'cuenta' OR usuario_id IS NOT NULL);
ALTER TABLE privacidad_decision ADD CONSTRAINT priv_decision_acto_valido CHECK (acto IN ('aceptacion_terminos','lectura_aviso','cookies'));
ALTER TABLE privacidad_decision ADD CONSTRAINT priv_decision_coherente CHECK (
      (acto IN ('aceptacion_terminos','lectura_aviso') AND decision AND finalidad_id IS NULL AND usuario_id IS NOT NULL)
   OR (acto='cookies' AND finalidad_id IS NOT NULL));
ALTER TABLE privacidad_decision ADD CONSTRAINT priv_decision_ip_recortada CHECK (ip_recortada = '' OR ip_recortada ~ '^([0-9]{1,3}\.){3}0$' OR ip_recortada ~ '^[0-9a-f:]+::$');
ALTER TABLE conteo_navegacion ADD CONSTRAINT conteo_visitas_positivas CHECK (visitas >= 0);
ALTER TABLE conteo_navegacion ADD CONSTRAINT conteo_seccion_valida CHECK (seccion IN ('inicio','proyecto','prototipo','funcionamiento','huerto',
   'panel_tecnico','mantenimiento','soporte','avisos','cuenta','privacidad'));
ALTER TABLE capacidad_historial ADD CONSTRAINT cap_hist_accion_valida CHECK (accion IN ('concedida','retirada'));
ALTER TABLE auditoria ADD CONSTRAINT auditoria_accion_formato CHECK (accion ~ '^[a-z]+(_[a-z]+)*$');
ALTER TABLE auditoria ADD CONSTRAINT auditoria_resultado_valido CHECK (resultado IN ('exito','rechazado'));
ALTER TABLE auditoria ADD CONSTRAINT auditoria_detalle_objeto CHECK (jsonb_typeof(detalle)='object' AND length(detalle::text) <= 2000);
ALTER TABLE auditoria ADD CONSTRAINT auditoria_ip_recortada CHECK (ip_recortada = '' OR ip_recortada ~ '^([0-9]{1,3}\.){3}0$' OR ip_recortada ~ '^[0-9a-f:]+::$');
""", None),
            # Borrar una medición borra sus lecturas por planta (el modelo no puede declararlo en la base)
            (r"""
DO $$
DECLARE nombre text;
BEGIN
 SELECT conname INTO nombre FROM pg_constraint
  WHERE conrelid = 'medicion_planta'::regclass AND contype = 'f' AND confrelid = 'medicion'::regclass;
 EXECUTE format('ALTER TABLE medicion_planta DROP CONSTRAINT %I', nombre);
 ALTER TABLE medicion_planta ADD CONSTRAINT medicion_planta_medicion_id_fkey FOREIGN KEY (medicion_id)
  REFERENCES medicion(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
END $$;
""", None),
            # Índices parciales, descendentes, por expresión y BRIN (secciones 3 a 11)
            (r"""
CREATE UNIQUE INDEX usuario_identidad_correo_unica ON cuentas_usuario (chilito_identidad_correo(email));
CREATE INDEX usuario_anonimizacion_pendiente_idx ON cuentas_usuario(anonimizacion_solicitada_en)
 WHERE anonimizacion_solicitada_en IS NOT NULL AND anonimizada_en IS NULL;
CREATE INDEX huerto_propietario_idx ON huerto(propietario_id) WHERE estado='activo';
CREATE INDEX planta_etapa_hist_idx ON huerto_planta_etapa(planta_id, registrada_en DESC);
CREATE UNIQUE INDEX codigo_pendiente_por_huerto ON codigo_vinculacion(huerto_id) WHERE estado='pendiente';
CREATE INDEX codigo_vencidos_idx ON codigo_vinculacion(vence_en) WHERE estado='pendiente';
CREATE INDEX disp_evento_dispositivo_idx ON dispositivo_evento(dispositivo_id, ocurrido_en DESC);
CREATE INDEX disp_evento_huerto_idx ON dispositivo_evento(huerto_id, ocurrido_en DESC) WHERE huerto_id IS NOT NULL;
CREATE INDEX medicion_huerto_fecha_idx ON medicion(huerto_id, medida_en DESC);
CREATE INDEX medicion_fecha_brin ON medicion USING brin(medida_en);
CREATE UNIQUE INDEX comando_uno_en_curso ON comando(dispositivo_id, tipo, coalesce(planta_numero,0))
 WHERE estado IN ('pendiente','enviado');
CREATE INDEX comando_huerto_fecha_idx ON comando(huerto_id, creado_en DESC);
CREATE INDEX comando_en_curso_idx ON comando(creado_en) WHERE estado IN ('pendiente','enviado');
CREATE INDEX actuacion_huerto_fecha_idx ON actuacion(huerto_id, ocurrido_en DESC);
CREATE INDEX actuacion_lampara_idx ON actuacion(huerto_id, ocurrido_en DESC) WHERE actuador='lampara';
CREATE INDEX autodiag_huerto_idx ON autodiagnostico(huerto_id, iniciado_en DESC);
CREATE INDEX cuidado_huerto_fecha_idx ON cuidado(huerto_id, realizado_en DESC);
CREATE UNIQUE INDEX revision_cuidado_una_anulacion ON cuidado_revision(cuidado_id) WHERE tipo='anulacion';
CREATE INDEX guia_estado_orden_idx ON guia_cuidado(estado, orden);
CREATE UNIQUE INDEX caso_uno_activo_por_huerto ON soporte_caso(huerto_id) WHERE estado IN ('abierto','en_atencion');
CREATE INDEX caso_bandeja_idx ON soporte_caso(estado, creado_en DESC);
CREATE INDEX caso_solicitante_idx ON soporte_caso(solicitante_id, creado_en DESC);
CREATE UNIQUE INDEX sesion_una_abierta_por_admin ON soporte_sesion(administrador_id) WHERE cerrada_en IS NULL;
CREATE UNIQUE INDEX sesion_una_abierta_por_caso ON soporte_sesion(caso_id) WHERE cerrada_en IS NULL;
CREATE INDEX notif_bandeja_idx ON notificacion(destinatario_id, creada_en DESC);
CREATE INDEX notif_no_leidas_idx ON notificacion(destinatario_id) WHERE leida_en IS NULL;
CREATE INDEX ia_huerto_fecha_idx ON ia_resumen(huerto_id, generado_en DESC);
CREATE INDEX consulta_estado_fecha_idx ON consulta_producto(estado, recibida_en DESC);
CREATE INDEX consulta_huella_idx ON consulta_producto(huella, recibida_en DESC);
CREATE UNIQUE INDEX correo_un_aviso_por_caso ON correo_pendiente(caso_id) WHERE caso_id IS NOT NULL;
CREATE UNIQUE INDEX correo_un_aviso_por_consulta ON correo_pendiente(consulta_id) WHERE consulta_id IS NOT NULL;
CREATE INDEX correo_pendientes_idx ON correo_pendiente(estado, creado_en) WHERE estado <> 'aceptado_smtp';
CREATE UNIQUE INDEX venta_vigente_por_equipo ON venta(dispositivo_id) WHERE estado='vigente';
CREATE INDEX venta_fecha_idx ON venta(vendida_en DESC);
CREATE INDEX legal_vigente_idx ON documento_legal(tipo, publicado_en DESC) WHERE estado='publicada';
CREATE UNIQUE INDEX priv_sujeto_cuenta_unica ON privacidad_sujeto(usuario_id) WHERE ambito='cuenta';
CREATE INDEX priv_sujeto_usuario_idx ON privacidad_sujeto(usuario_id) WHERE usuario_id IS NOT NULL;
CREATE INDEX priv_decision_bitacora_idx ON privacidad_decision(registrada_en DESC);
CREATE INDEX priv_decision_sujeto_idx ON privacidad_decision(sujeto_id, acto, registrada_en DESC);
CREATE INDEX priv_decision_usuario_idx ON privacidad_decision(usuario_id, registrada_en DESC) WHERE usuario_id IS NOT NULL;
CREATE INDEX cap_hist_usuario_idx ON capacidad_historial(usuario_id, realizada_en DESC);
CREATE INDEX cap_hist_fecha_idx ON capacidad_historial(realizada_en DESC);
CREATE INDEX auditoria_actor_idx ON auditoria(actor_id, creada_en DESC);
CREATE INDEX auditoria_entidad_idx ON auditoria(entidad, entidad_id);
CREATE INDEX auditoria_huerto_idx ON auditoria(huerto_id, creada_en DESC) WHERE huerto_id IS NOT NULL;
CREATE INDEX auditoria_fecha_idx ON auditoria(creada_en DESC);
CREATE INDEX web_idempotencia_fecha_idx ON web_idempotencia(creada_en);
""", None),
            # Reglas, funciones y triggers (secciones 12 y 13)
            (r"""
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
""", None),
            # Vistas (sección 14)
            (r"""
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
""", None),
            # Datos iniciales (sección 15)
            (r"""
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
""", None),
            # Privilegios (sección 16)
            (r"""
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
""", None),
        ]),
    ]
