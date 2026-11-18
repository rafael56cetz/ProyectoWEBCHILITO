"""Recarga por confirmar: el flotador detecta la recarga, pero la registra el dueño.

· Nivel bajo → con agua: ya no se crea el cuidado. Se guarda una «recarga detectada» pendiente en deposito_deteccion
  (máximo una pendiente por huerto) y el dueño recibe el aviso «Detectamos que rellenaste tu depósito … ¿Lo confirmas?».
  Si la persona registró la recarga en los 30 minutos anteriores, es la misma: no se pide confirmación.
· Confirmar = registrar la recarga con una detección pendiente (el botón «Confirmar recarga» o el registro manual):
  el cuidado rellenar_deposito toma realizado_en = detectada_en, origen 'equipo' y registrado_por = quien confirma;
  la detección pasa a «confirmada». No se duplica: con una pendiente no se aplican las reglas de la recarga manual.
· «No fue una recarga»: el dueño la marca «descartada» (solo el dueño, con actor). No crea cuidado.
· Un nuevo nivel bajo con una detección aún pendiente la deja «sin_confirmar».
· Los cuidados con origen 'equipo' y sin autor que creó la 0004 se quedan como están.

El estado de Django (modelo DepositoDeteccion) lo declara datos.0003, que no ejecuta SQL. Al revertir se restauran las
funciones de la 0004; si ya hay detecciones, la reversión falla a propósito (son historial). El texto de la guía se queda."""
import importlib
import re

from django.db import migrations

ANTERIOR = importlib.import_module('web.migrations.0004_deposito_flotador')


def _funcion_0004(nombre):
    """La definición de la 0004, tal cual, como CREATE OR REPLACE (para revertir)."""
    encontrada = re.search(rf'CREATE (?:OR REPLACE )?FUNCTION public\.{nombre}\(.*?\nEND \$\$;\n', ANTERIOR.FUNCIONES, re.S)
    return re.sub(r'^CREATE (?:OR REPLACE )?FUNCTION', 'CREATE OR REPLACE FUNCTION', encontrada.group(0))


TABLA = r"""
CREATE TABLE deposito_deteccion (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 huerto_id bigint NOT NULL REFERENCES huerto(id) DEFERRABLE INITIALLY DEFERRED,
 detectada_en timestamptz NOT NULL,
 estado varchar(13) NOT NULL DEFAULT 'pendiente',
 cuidado_id uuid REFERENCES cuidado(id) DEFERRABLE INITIALLY DEFERRED,
 decidida_por_id bigint REFERENCES cuentas_usuario(id) DEFERRABLE INITIALLY DEFERRED,
 decidida_en timestamptz,
 CONSTRAINT deteccion_estado_valido CHECK (estado IN ('pendiente','confirmada','descartada','sin_confirmar')),
 -- Solo la confirmada tiene cuidado; confirmada y descartada dicen quién decidió; sin_confirmar no la decidió nadie.
 CONSTRAINT deteccion_coherente CHECK (
     (estado='pendiente'     AND cuidado_id IS NULL     AND decidida_por_id IS NULL     AND decidida_en IS NULL)
  OR (estado='confirmada'    AND cuidado_id IS NOT NULL AND decidida_por_id IS NOT NULL AND decidida_en IS NOT NULL)
  OR (estado='descartada'    AND cuidado_id IS NULL     AND decidida_por_id IS NOT NULL AND decidida_en IS NOT NULL)
  OR (estado='sin_confirmar' AND cuidado_id IS NULL     AND decidida_por_id IS NULL     AND decidida_en IS NOT NULL))
);
CREATE UNIQUE INDEX deteccion_una_pendiente ON deposito_deteccion(huerto_id) WHERE estado='pendiente';
CREATE UNIQUE INDEX deteccion_un_cuidado ON deposito_deteccion(cuidado_id) WHERE cuidado_id IS NOT NULL;
CREATE INDEX deteccion_huerto_fecha_idx ON deposito_deteccion(huerto_id, detectada_en DESC);
REVOKE ALL ON deposito_deteccion FROM PUBLIC;
-- La aplicación lee y descarta (UPDATE de la decisión); la crea y la cierra solo la base (triggers).
GRANT SELECT ON deposito_deteccion TO chilito_pkg_runtime;
GRANT UPDATE (estado, decidida_por_id, decidida_en) ON deposito_deteccion TO chilito_pkg_runtime;
"""

QUITAR_TABLA = r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM deposito_deteccion) THEN
  RAISE EXCEPTION 'Hay recargas detectadas: son historial y la reversión no las borra' USING ERRCODE='23514';
 END IF;
END $$;
DROP TABLE deposito_deteccion;
"""

FUNCIONES = r"""
-- Reglas de la detección: la crea el flotador, solo se decide una vez y el dueño es quien la descarta.
CREATE FUNCTION public.chilito_deteccion_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'Historial inmutable (deposito_deteccion): no se permite borrar' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' THEN
  IF pg_trigger_depth() < 2 OR NEW.estado<>'pendiente' THEN
   RAISE EXCEPTION 'Las recargas detectadas solo las registra el flotador' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF OLD.estado<>'pendiente' THEN
  RAISE EXCEPTION 'Esta recarga detectada ya se resolvió' USING ERRCODE='23514';
 END IF;
 IF NEW.id<>OLD.id OR NEW.huerto_id<>OLD.huerto_id OR NEW.detectada_en<>OLD.detectada_en THEN
  RAISE EXCEPTION 'De una recarga detectada solo cambia la decisión' USING ERRCODE='23514';
 END IF;
 IF NEW.estado='descartada' THEN
  IF NEW.decidida_por_id IS DISTINCT FROM chilito_dueno_huerto(NEW.huerto_id) THEN
   RAISE EXCEPTION 'Solo el dueño del huerto confirma o descarta sus recargas detectadas' USING ERRCODE='23514';
  END IF;
  IF session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.decidida_por_id THEN
   RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
  END IF;
 ELSIF pg_trigger_depth() < 2 THEN
  -- confirmada: al registrar la recarga (trigger de cuidado); sin_confirmar: al llegar otro nivel bajo (flotador).
  RAISE EXCEPTION 'Una recarga detectada se confirma registrando la recarga' USING ERRCODE='23514';
 END IF;
 NEW.decidida_en := now();
 -- El aviso «¿Lo confirmas?» ya no hace falta. Desde la aplicación solo lo resuelve su destinatario.
 UPDATE notificacion SET resuelta_en=now()
  WHERE huerto_id=NEW.huerto_id AND origen='dispositivo' AND titulo='Confirma la recarga de tu depósito' AND resuelta_en IS NULL
    AND (session_user<>'chilito_pkg_runtime' OR destinatario_id=chilito_actor());
 RETURN NEW;
END $$;
CREATE TRIGGER deteccion_reglas BEFORE INSERT OR UPDATE OR DELETE ON deposito_deteccion FOR EACH ROW
 EXECUTE FUNCTION chilito_deteccion_reglas();

-- El cuidado que confirma una detección la cierra como «confirmada» y queda enlazado a ella.
CREATE FUNCTION public.chilito_deteccion_confirmada() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 UPDATE deposito_deteccion SET estado='confirmada', cuidado_id=NEW.id, decidida_por_id=NEW.registrado_por_id
  WHERE huerto_id=NEW.huerto_id AND estado='pendiente';
 IF NOT FOUND THEN
  RAISE EXCEPTION 'No hay una recarga detectada que confirmar' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER deteccion_confirmada AFTER INSERT ON cuidado FOR EACH ROW
 WHEN (NEW.origen='equipo' AND NEW.registrado_por_id IS NOT NULL) EXECUTE FUNCTION chilito_deteccion_confirmada();

-- El flotador cambió. Con agua → nivel bajo: evento y aviso; una detección pendiente queda «sin_confirmar».
-- Nivel bajo → con agua: evento y una detección pendiente con su aviso (ya no se crea el cuidado).
CREATE OR REPLACE FUNCTION public.chilito_deposito_flotador() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE anterior boolean; dueno bigint; nombre_huerto text; nueva uuid;
BEGIN
 -- Una medición atrasada (ya hay otra más reciente con flotador) no cambia el estado.
 IF EXISTS(SELECT 1 FROM medicion m WHERE m.huerto_id=NEW.huerto_id AND m.medida_en > NEW.medida_en AND m.deposito_con_agua IS NOT NULL) THEN
  RETURN NULL;
 END IF;
 SELECT m.deposito_con_agua INTO anterior FROM medicion m
  WHERE m.huerto_id=NEW.huerto_id AND m.id<>NEW.id AND m.medida_en < NEW.medida_en AND m.deposito_con_agua IS NOT NULL
  ORDER BY m.medida_en DESC LIMIT 1;
 SELECT h.propietario_id, h.nombre INTO dueno, nombre_huerto FROM huerto h WHERE h.id=NEW.huerto_id AND h.estado='activo';
 IF NOT NEW.deposito_con_agua AND anterior IS DISTINCT FROM false THEN
  -- Sin lectura anterior también cuenta: el dueño de un equipo recién vinculado recibe el aviso.
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, ocurrido_en) VALUES (NEW.dispositivo_id, NEW.huerto_id, 'deposito_bajo', NEW.medida_en);
  UPDATE deposito_deteccion SET estado='sin_confirmar' WHERE huerto_id=NEW.huerto_id AND estado='pendiente';
  IF dueno IS NOT NULL THEN
   INSERT INTO notificacion(destinatario_id, origen, severidad, titulo, texto, huerto_id, enlace)
   VALUES (dueno, 'dispositivo', 'advertencia', 'Tu depósito necesita agua',
           'El flotador de «' || nombre_huerto || '» marcó nivel bajo. Rellénalo con agua limpia: cuando tu equipo vuelva a detectar agua, te pediremos que confirmes la recarga.',
           NEW.huerto_id, '#huerto');
  END IF;
 ELSIF NEW.deposito_con_agua AND anterior IS NOT DISTINCT FROM false THEN
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, ocurrido_en) VALUES (NEW.dispositivo_id, NEW.huerto_id, 'deposito_recargado', NEW.medida_en);
  UPDATE notificacion SET resuelta_en=now()
   WHERE huerto_id=NEW.huerto_id AND origen='dispositivo' AND titulo='Tu depósito necesita agua' AND resuelta_en IS NULL;
  -- Si la persona registró la recarga en los 30 minutos anteriores, es la misma: no se pide confirmación.
  IF dueno IS NOT NULL AND NOT EXISTS(SELECT 1 FROM chilito_recargas_vigentes(NEW.huerto_id) r
                WHERE r.realizado_en BETWEEN NEW.medida_en - interval '30 minutes' AND NEW.medida_en) THEN
   INSERT INTO deposito_deteccion(huerto_id, detectada_en) VALUES (NEW.huerto_id, NEW.medida_en)
    ON CONFLICT (huerto_id) WHERE estado='pendiente' DO NOTHING
    RETURNING id INTO nueva;
   IF nueva IS NOT NULL THEN
    INSERT INTO notificacion(destinatario_id, origen, severidad, titulo, texto, huerto_id, enlace)
    VALUES (dueno, 'dispositivo', 'informacion', 'Confirma la recarga de tu depósito',
            'Detectamos que rellenaste tu depósito el ' || chilito_hora_merida(NEW.medida_en) || '. ¿Lo confirmas?',
            NEW.huerto_id, '#huerto');
   END IF;
  END IF;
 END IF;
 RETURN NULL;
END $$;

-- Recarga manual con equipo: solo después de un nivel bajo; si no, una cada 12 horas (igual que la 0004, otro texto).
CREATE OR REPLACE FUNCTION public.chilito_recarga_manual(h bigint, realizado timestamptz) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE ultima timestamptz; proxima timestamptz;
BEGIN
 PERFORM 1 FROM huerto WHERE id=h FOR UPDATE;   -- dos registros simultáneos esperan su turno
 SELECT max(r.realizado_en) INTO ultima FROM chilito_recargas_vigentes(h) r;
 IF chilito_equipo_de_huerto(h) IS NOT NULL
    AND EXISTS(SELECT 1 FROM medicion m WHERE m.huerto_id=h AND m.deposito_con_agua IS NOT NULL) THEN
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
   RAISE EXCEPTION 'Ya registraste esta recarga (%): no hace falta registrar otra', chilito_hora_merida(ultima)
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

-- Igual que en la 0004, salvo la recarga: con una detección pendiente, registrarla es confirmarla.
CREATE OR REPLACE FUNCTION public.chilito_cuidado_reglas() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE ultimo integer; anulado boolean; detectada timestamptz;
BEGIN
 IF TG_TABLE_NAME='cuidado' THEN
  IF chilito_dueno_huerto(NEW.huerto_id) IS NULL THEN RAISE EXCEPTION 'El huerto no está activo' USING ERRCODE='23514'; END IF;
  IF NEW.origen='equipo' THEN
   -- Nadie la escribe así: una recarga del equipo nace al confirmar una detección (abajo).
   RAISE EXCEPTION 'Las recargas del equipo solo se registran al confirmar una recarga detectada' USING ERRCODE='23514';
  END IF;
  IF NOT (chilito_dueno_huerto(NEW.huerto_id) = NEW.registrado_por_id
          OR chilito_tiene_capacidad(NEW.registrado_por_id,'gestionar_mantenimientos')) THEN
   RAISE EXCEPTION 'Solo el dueño del huerto o un admin de mantenimientos registra cuidados' USING ERRCODE='23514';
  END IF;
  IF session_user='chilito_pkg_runtime' AND chilito_actor() IS DISTINCT FROM NEW.registrado_por_id THEN
   RAISE EXCEPTION 'La operación debe hacerla la propia cuenta' USING ERRCODE='23514';
  END IF;
  NEW.registrado_en := now();
  IF NEW.tipo='rellenar_deposito' THEN
   PERFORM 1 FROM huerto WHERE id=NEW.huerto_id FOR UPDATE;   -- confirmar y descartar a la vez esperan su turno
   SELECT d.detectada_en INTO detectada FROM deposito_deteccion d
    WHERE d.huerto_id=NEW.huerto_id AND d.estado='pendiente' FOR UPDATE;
   IF FOUND THEN
    -- La recarga es la detectada: su hora (dentro de los 7 días que admite un cuidado) y origen «equipo».
    -- El trigger deteccion_confirmada la marca confirmada por quien la registra.
    NEW.origen := 'equipo';
    NEW.realizado_en := greatest(least(detectada, NEW.registrado_en), NEW.registrado_en - interval '7 days');
   ELSE
    PERFORM chilito_recarga_manual(NEW.huerto_id, NEW.realizado_en);
   END IF;
  END IF;
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

GRANT EXECUTE ON FUNCTION public.chilito_deteccion_reglas(), public.chilito_deteccion_confirmada() TO chilito_pkg_runtime, chilito_pkg_iot;
"""

QUITAR_FUNCIONES = r"""
DROP TRIGGER deteccion_confirmada ON cuidado;
DROP TRIGGER deteccion_reglas ON deposito_deteccion;
DROP FUNCTION public.chilito_deteccion_confirmada();
DROP FUNCTION public.chilito_deteccion_reglas();
""" + _funcion_0004('chilito_deposito_flotador') + _funcion_0004('chilito_recarga_manual') + _funcion_0004('chilito_cuidado_reglas')

# Solo si nadie la editó después de la 0004 (sigue con su texto y sin autor). Igual que en la 0004, el trigger de
# guías exige un admin con «gestionar_guias», que en una migración no existe: se suspende solo durante este UPDATE.
TEXTO_GUIA = """Rellenar es añadir agua limpia al depósito con tus propias manos.

Si tu huerto tiene equipo, el flotador avisa cuando el agua llega a nivel bajo y te llega el aviso «Tu depósito necesita agua». Cuando lo rellenas y el flotador vuelve a detectar agua, te preguntamos si fue una recarga: en Mi huerto verás «Detectamos una recarga» con los botones «Confirmar recarga» y «No fue una recarga».

Solo las recargas que confirmas quedan en tu historial, como «Detectada por tu equipo · confirmada por ti», y solo ellas cuentan para calcular cuánto dura tu depósito. Si el flotador vuelve a marcar nivel bajo antes de que respondas, la detección queda sin confirmar y no se registra ninguna recarga. Mover el depósito puede hacer que el flotador rebote y parezca una recarga: en ese caso, elige «No fue una recarga».

Si prefieres anotarla tú, usa «Rellené el depósito» después de que el flotador haya marcado nivel bajo. Si tu equipo ya detectó la recarga, eso la confirma sin duplicarla. Mientras tu depósito tenga agua desde la última recarga, el botón queda desactivado. Si tu huerto no tiene equipo, puedes registrar una recarga cada 12 horas como máximo.

Registrar un cuidado declara una acción que ya realizaste físicamente. No significa que el sistema la haya ejecutado o comprobado.

El flotador solo detecta nivel bajo. No mide los litros restantes ni confirma que el depósito esté lleno, así que comprueba el nivel a simple vista al rellenarlo."""


def _texto_0004():
    return re.search(r"respuesta=\n'(.*?)'\nWHERE", ANTERIOR.GUIA, re.S).group(1)


def actualizar_guia(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('ALTER TABLE guia_cuidado DISABLE TRIGGER guia_reglas')
        cursor.execute("UPDATE guia_cuidado SET version=version+1, actualizado_en=now(), respuesta=%s "
                       "WHERE clave='deposito-recarga' AND respuesta=%s AND actualizado_por_id IS NULL", [TEXTO_GUIA, _texto_0004()])
        cursor.execute('ALTER TABLE guia_cuidado ENABLE TRIGGER guia_reglas')


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0004_deposito_flotador'),
        ('datos', '0003_deposito_deteccion'),
    ]

    operations = [
        migrations.RunSQL(sql=TABLA, reverse_sql=QUITAR_TABLA),
        migrations.RunSQL(sql=FUNCIONES, reverse_sql=QUITAR_FUNCIONES),
        migrations.RunPython(actualizar_guia, migrations.RunPython.noop),
    ]
