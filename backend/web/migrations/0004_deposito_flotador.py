"""Depósito con flotador: la base detecta el nivel bajo y las recargas, y limita el registro manual.

· Al llegar una medición, se compara el flotador con la lectura anterior del huerto:
  con agua → nivel bajo: evento «deposito_bajo» y aviso al dueño «Tu depósito necesita agua»;
  nivel bajo → con agua: evento «deposito_recargado» y un cuidado rellenar_deposito con origen «equipo»
  (salvo que haya una recarga vigente en los 30 minutos anteriores: es la misma).
· Recarga manual con equipo: solo si hubo una lectura en nivel bajo después de la última recarga vigente.
  Sin equipo (o sin lecturas del flotador todavía): como máximo una cada 12 horas.
· Las correcciones y anulaciones de cuidados no cambian.

El estado de Django (campo Cuidado.origen y registrado_por opcional) lo declara datos.0002, que no ejecuta SQL.
Al revertir se restaura la regla de la 0002; si ya existen recargas del equipo o eventos del depósito, la reversión
falla a propósito (son historial inmutable). El texto de la guía se queda."""
from django.db import migrations

ESQUEMA = r"""
ALTER TABLE cuidado ADD COLUMN origen varchar(7) NOT NULL DEFAULT 'persona';
ALTER TABLE cuidado ADD CONSTRAINT cuidado_origen_valido CHECK (origen IN ('persona','equipo'));
ALTER TABLE cuidado ALTER COLUMN registrado_por_id DROP NOT NULL;
ALTER TABLE cuidado ADD CONSTRAINT cuidado_autor_por_origen CHECK (registrado_por_id IS NOT NULL OR origen='equipo');
ALTER TABLE cuidado ADD CONSTRAINT cuidado_equipo_solo_deposito CHECK (origen='persona' OR tipo='rellenar_deposito');
ALTER TABLE dispositivo_evento DROP CONSTRAINT disp_evento_tipo_valido;
ALTER TABLE dispositivo_evento ADD CONSTRAINT disp_evento_tipo_valido CHECK (tipo IN ('alta','vinculado','desvinculado','conectado','desconectado',
   'error','reinicio','credencial_rotada','firmware_actualizado','retirado','deposito_bajo','deposito_recargado'));
"""

QUITAR_ESQUEMA = r"""
ALTER TABLE dispositivo_evento DROP CONSTRAINT disp_evento_tipo_valido;
ALTER TABLE dispositivo_evento ADD CONSTRAINT disp_evento_tipo_valido CHECK (tipo IN ('alta','vinculado','desvinculado','conectado','desconectado',
   'error','reinicio','credencial_rotada','firmware_actualizado','retirado'));
ALTER TABLE cuidado DROP CONSTRAINT cuidado_equipo_solo_deposito;
ALTER TABLE cuidado DROP CONSTRAINT cuidado_autor_por_origen;
ALTER TABLE cuidado ALTER COLUMN registrado_por_id SET NOT NULL;
ALTER TABLE cuidado DROP CONSTRAINT cuidado_origen_valido;
ALTER TABLE cuidado DROP COLUMN origen;
"""

FUNCIONES = r"""
-- Recargas vigentes de un huerto: aplica la última revisión (una corrección cambia el tipo; una anulación la quita).
CREATE FUNCTION public.chilito_recargas_vigentes(h bigint)
RETURNS TABLE(id uuid, realizado_en timestamptz, origen varchar)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT c.id, c.realizado_en, c.origen
 FROM cuidado c
 LEFT JOIN LATERAL (SELECT r.tipo, r.tipo_corregido FROM cuidado_revision r WHERE r.cuidado_id=c.id ORDER BY r.numero DESC LIMIT 1) r ON true
 WHERE c.huerto_id=h AND r.tipo IS DISTINCT FROM 'anulacion'
   AND (CASE WHEN r.tipo='correccion' THEN r.tipo_corregido ELSE c.tipo END)='rellenar_deposito'
$$;

-- Fecha y hora en Mérida para los mensajes.
CREATE FUNCTION public.chilito_hora_merida(t timestamptz) RETURNS text
LANGUAGE sql STABLE SET search_path = pg_catalog, public AS $$
 SELECT to_char(t AT TIME ZONE 'America/Merida', 'DD/MM/YYYY "a las" HH24:MI')
$$;

-- El flotador cambió: con agua → nivel bajo (evento y aviso) o nivel bajo → con agua (evento y recarga del equipo).
CREATE FUNCTION public.chilito_deposito_flotador() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE anterior boolean; dueno bigint; nombre_huerto text;
BEGIN
 -- Una medición atrasada (ya hay otra más reciente con flotador) no cambia el estado.
 IF EXISTS(SELECT 1 FROM medicion m WHERE m.huerto_id=NEW.huerto_id AND m.medida_en > NEW.medida_en AND m.deposito_con_agua IS NOT NULL) THEN
  RETURN NULL;
 END IF;
 SELECT m.deposito_con_agua INTO anterior FROM medicion m
  WHERE m.huerto_id=NEW.huerto_id AND m.id<>NEW.id AND m.medida_en < NEW.medida_en AND m.deposito_con_agua IS NOT NULL
  ORDER BY m.medida_en DESC LIMIT 1;
 IF NOT NEW.deposito_con_agua AND anterior IS DISTINCT FROM false THEN
  -- Sin lectura anterior también cuenta: el dueño de un equipo recién vinculado recibe el aviso.
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, ocurrido_en) VALUES (NEW.dispositivo_id, NEW.huerto_id, 'deposito_bajo', NEW.medida_en);
  SELECT h.propietario_id, h.nombre INTO dueno, nombre_huerto FROM huerto h WHERE h.id=NEW.huerto_id AND h.estado='activo';
  IF dueno IS NOT NULL THEN
   INSERT INTO notificacion(destinatario_id, origen, severidad, titulo, texto, huerto_id, enlace)
   VALUES (dueno, 'dispositivo', 'advertencia', 'Tu depósito necesita agua',
           'El flotador de «' || nombre_huerto || '» marcó nivel bajo. Rellénalo con agua limpia: tu equipo registrará la recarga cuando vuelva a detectar agua.',
           NEW.huerto_id, '#huerto');
  END IF;
 ELSIF NEW.deposito_con_agua AND anterior IS NOT DISTINCT FROM false THEN
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, ocurrido_en) VALUES (NEW.dispositivo_id, NEW.huerto_id, 'deposito_recargado', NEW.medida_en);
  UPDATE notificacion SET resuelta_en=now()
   WHERE huerto_id=NEW.huerto_id AND origen='dispositivo' AND titulo='Tu depósito necesita agua' AND resuelta_en IS NULL;
  -- Si la persona registró la recarga en los 30 minutos anteriores, es la misma: no se duplica.
  IF NOT EXISTS(SELECT 1 FROM chilito_recargas_vigentes(NEW.huerto_id) r
                WHERE r.realizado_en BETWEEN NEW.medida_en - interval '30 minutes' AND NEW.medida_en) THEN
   INSERT INTO cuidado(huerto_id, tipo, origen, realizado_en)
   VALUES (NEW.huerto_id, 'rellenar_deposito', 'equipo', greatest(NEW.medida_en, now() - interval '7 days'));
  END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER deposito_flotador AFTER INSERT ON medicion FOR EACH ROW
 WHEN (NEW.deposito_con_agua IS NOT NULL) EXECUTE FUNCTION chilito_deposito_flotador();

-- Recarga manual: con equipo y lecturas del flotador, solo después de un nivel bajo; si no, una cada 12 horas.
CREATE FUNCTION public.chilito_recarga_manual(h bigint, realizado timestamptz) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE ultima timestamptz; proxima timestamptz;
BEGIN
 PERFORM 1 FROM huerto WHERE id=h FOR UPDATE;   -- dos registros simultáneos esperan su turno
 SELECT max(r.realizado_en) INTO ultima FROM chilito_recargas_vigentes(h) r;
 IF chilito_equipo_de_huerto(h) IS NOT NULL
    AND EXISTS(SELECT 1 FROM medicion m WHERE m.huerto_id=h AND m.deposito_con_agua IS NOT NULL) THEN
  -- Basta una lectura en nivel bajo posterior a la última recarga. Si la última lectura sigue en nivel bajo pero ya
  -- hay una recarga registrada después, es la misma recarga: tampoco se repite.
  IF NOT EXISTS(SELECT 1 FROM medicion m WHERE m.huerto_id=h AND m.deposito_con_agua=false
                AND (ultima IS NULL OR m.medida_en > ultima)) THEN
   IF ultima IS NULL THEN
    RAISE EXCEPTION 'Tu depósito tiene agua: podrás registrar una recarga cuando el flotador marque nivel bajo' USING ERRCODE='23514';
   END IF;
   IF (SELECT m.deposito_con_agua FROM medicion m WHERE m.huerto_id=h AND m.deposito_con_agua IS NOT NULL
       ORDER BY m.medida_en DESC LIMIT 1) THEN
    RAISE EXCEPTION 'Tu depósito tiene agua desde tu última recarga (%): no hace falta registrar otra', chilito_hora_merida(ultima)
     USING ERRCODE='23514';
   END IF;
   RAISE EXCEPTION 'Ya registraste esta recarga (%): tu equipo la confirmará cuando el flotador detecte agua', chilito_hora_merida(ultima)
    USING ERRCODE='23514';
  END IF;
 ELSE
  SELECT max(r.realizado_en) + interval '12 hours' INTO proxima FROM chilito_recargas_vigentes(h) r
   WHERE r.realizado_en > realizado - interval '12 hours' AND r.realizado_en < realizado + interval '12 hours';
  IF proxima IS NOT NULL THEN
   RAISE EXCEPTION 'Ya registraste una recarga hace menos de 12 horas: podrás registrar otra a partir del %', chilito_hora_merida(proxima)
    USING ERRCODE='23514';
  END IF;
 END IF;
END $$;

-- Igual que en la 0002, más el origen «equipo» y las reglas de la recarga manual.
CREATE OR REPLACE FUNCTION public.chilito_cuidado_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE ultimo integer; anulado boolean;
BEGIN
 IF TG_TABLE_NAME='cuidado' THEN
  IF chilito_dueno_huerto(NEW.huerto_id) IS NULL THEN RAISE EXCEPTION 'El huerto no está activo' USING ERRCODE='23514'; END IF;
  IF NEW.origen='equipo' THEN
   -- Solo la escribe el trigger del flotador: nadie la registra a mano.
   IF pg_trigger_depth() < 2 OR NEW.registrado_por_id IS NOT NULL OR NEW.tipo<>'rellenar_deposito' THEN
    RAISE EXCEPTION 'Las recargas del equipo solo las registra el flotador' USING ERRCODE='23514';
   END IF;
   NEW.registrado_en := now();
   RETURN NEW;
  END IF;
  IF NOT (chilito_dueno_huerto(NEW.huerto_id) = NEW.registrado_por_id
          OR chilito_tiene_capacidad(NEW.registrado_por_id,'gestionar_mantenimientos')) THEN
   RAISE EXCEPTION 'Solo el dueño del huerto o un admin de mantenimientos registra cuidados' USING ERRCODE='23514';
  END IF;
  IF session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.registrado_por_id THEN
   RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
  END IF;
  IF NEW.tipo='rellenar_deposito' THEN PERFORM chilito_recarga_manual(NEW.huerto_id, NEW.realizado_en); END IF;
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

-- Igual que las demás funciones de apoyo (0002): la usan los triggers con los permisos de quien escribe.
GRANT EXECUTE ON FUNCTION public.chilito_recargas_vigentes(bigint), public.chilito_hora_merida(timestamptz),
 public.chilito_deposito_flotador(), public.chilito_recarga_manual(bigint, timestamptz) TO chilito_pkg_runtime, chilito_pkg_iot;
"""

# La versión de la 0002, tal cual.
QUITAR_FUNCIONES = r"""
CREATE OR REPLACE FUNCTION public.chilito_cuidado_reglas() RETURNS trigger
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
DROP TRIGGER deposito_flotador ON medicion;
DROP FUNCTION public.chilito_deposito_flotador();
DROP FUNCTION public.chilito_recarga_manual(bigint, timestamptz);
DROP FUNCTION public.chilito_hora_merida(timestamptz);
DROP FUNCTION public.chilito_recargas_vigentes(bigint);
"""

# Solo si nadie la ha editado (sigue en la versión 1 de la carga inicial). El trigger de guías exige un admin
# con «gestionar_guias», que en una migración no existe: se suspende solo durante este UPDATE.
GUIA = r"""
ALTER TABLE guia_cuidado DISABLE TRIGGER guia_reglas;
UPDATE guia_cuidado SET version=version+1, actualizado_en=now(), respuesta=
'Rellenar es añadir agua limpia al depósito con tus propias manos.

Si tu huerto tiene equipo, el flotador avisa cuando el agua llega a nivel bajo y te llega el aviso «Tu depósito necesita agua». Cuando lo rellenas y el flotador vuelve a detectar agua, tu equipo registra la recarga por ti: en tu historial aparece como «Detectada por tu equipo».

Si prefieres anotarla tú, usa «Rellené el depósito» después de que el flotador haya marcado nivel bajo. Mientras tu depósito tenga agua desde la última recarga, el botón queda desactivado. Si tu huerto no tiene equipo, puedes registrar una recarga cada 12 horas como máximo.

Registrar un cuidado declara una acción que ya realizaste físicamente. No significa que el sistema la haya ejecutado o comprobado.

El flotador solo detecta nivel bajo. No mide los litros restantes ni confirma que el depósito esté lleno, así que comprueba el nivel a simple vista al rellenarlo.'
WHERE clave='deposito-recarga' AND version=1 AND actualizado_por_id IS NULL;
ALTER TABLE guia_cuidado ENABLE TRIGGER guia_reglas;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0003_linea_de_vida'),
        ('datos', '0002_cuidado_origen'),
    ]

    operations = [
        migrations.RunSQL(sql=ESQUEMA, reverse_sql=QUITAR_ESQUEMA),
        migrations.RunSQL(sql=FUNCIONES, reverse_sql=QUITAR_FUNCIONES),
        migrations.RunSQL(sql=GUIA, reverse_sql=migrations.RunSQL.noop),
    ]
