"""Ciclos de planta y recomendaciones al dueño.

· planta_ciclo (la crea huerto.0002): cada planta tiene siempre un ciclo abierto. Las plantas existentes reciben el
  ciclo 1, que empieza en su primera etapa o, si no tiene, en la creación del huerto; las nuevas lo reciben al nacer.
  Los ciclos no se borran y un ciclo cerrado no cambia.
· chilito_terminar_ciclo(planta, motivo, nota): solo el dueño (actor obligatorio). Cierra el ciclo abierto con su motivo,
  abre el siguiente y deja la planta en «sin_sembrar» sin fecha de siembra (el nombre se conserva). No borra nada: la
  línea de vida (huerto_planta_etapa) queda ligada a su ciclo por referencia (ciclo_id, que fija la base al insertar;
  las etapas existentes son del ciclo 1) y los cuidados se reparten por fecha (lo anterior al fin de un ciclo es de
  ese ciclo). Un cuidado de planta no puede fecharse antes del ciclo abierto.
· Recomendaciones (notificación al dueño, una sola vez por ciclo y situación, en planta_recomendacion):
    germinacion_larga  más de 21 días en germinación;
    sustrato_saturado  sustrato ≥ 90 % durante 12 h o más;
    seca_con_riegos    «Seca» (< 35 %) los 3 últimos días aunque la bomba la regó al menos 2 veces.
  Las de humedad se revisan con cada lectura del equipo (trigger en medicion_planta); todas, con
  chilito_recomendaciones_planta (la aplicación al abrir Mi huerto) y chilito_revisar_recomendaciones (tarea periódica).
· Dos guías nuevas publicadas: cuándo termina el ciclo del habanero y señales de que la planta está muriendo.

Al revertir se quitan funciones, triggers y la tabla de recomendaciones; si ya hay ciclos cerrados, la reversión falla a
propósito (son historial). Las guías se quedan."""
from django.db import migrations

MOTIVOS = "('cosecha_terminada','planta_murio','no_germino','pudricion_plaga','otro')"

CICLOS = r"""
ALTER TABLE planta_ciclo ADD CONSTRAINT ciclo_numero_valido CHECK (numero >= 1);
ALTER TABLE planta_ciclo ADD CONSTRAINT ciclo_motivo_valido CHECK (motivo IS NULL OR motivo IN """ + MOTIVOS + r""");
-- Abierto: sin fin, motivo, nota ni autor. Cerrado: fin y motivo; nota de hasta 500 sin caracteres de control (salvo el salto de línea).
ALTER TABLE planta_ciclo ADD CONSTRAINT ciclo_cierre_coherente CHECK (
     (fin IS NULL AND motivo IS NULL AND nota = '' AND cerrado_por_id IS NULL)
  OR (fin IS NOT NULL AND motivo IS NOT NULL AND fin >= inicio));
ALTER TABLE planta_ciclo ADD CONSTRAINT ciclo_nota_valida CHECK (length(nota) <= 500 AND nota !~ '[\x01-\x09\x0b-\x1f\x7f]');
CREATE UNIQUE INDEX ciclo_uno_abierto ON planta_ciclo(planta_id) WHERE fin IS NULL;
REVOKE ALL ON planta_ciclo FROM PUBLIC;
GRANT SELECT ON planta_ciclo TO chilito_pkg_runtime;

-- Los ciclos no se borran; uno abierto solo se cierra (fin, motivo, nota y autor) y uno cerrado ya no cambia.
-- Al crear: el número sigue al último de la planta.
CREATE FUNCTION public.chilito_ciclo_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Los ciclos de planta no se borran' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.numero IS DISTINCT FROM (SELECT coalesce(max(numero), 0) + 1 FROM planta_ciclo WHERE planta_id=NEW.planta_id) THEN
   RAISE EXCEPTION 'El ciclo debe seguir al último de la planta' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 IF OLD.fin IS NOT NULL THEN RAISE EXCEPTION 'Un ciclo terminado no cambia' USING ERRCODE='23514'; END IF;
 IF NEW.id<>OLD.id OR NEW.planta_id<>OLD.planta_id OR NEW.numero<>OLD.numero OR NEW.inicio<>OLD.inicio OR NEW.fin IS NULL THEN
  RAISE EXCEPTION 'Un ciclo abierto solo se cierra' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER ciclo_reglas BEFORE INSERT OR UPDATE OR DELETE ON planta_ciclo FOR EACH ROW EXECUTE FUNCTION chilito_ciclo_reglas();

-- Cada planta nace con su ciclo 1 (crear_plantas).
CREATE FUNCTION public.chilito_planta_ciclo_inicial() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 INSERT INTO planta_ciclo(planta_id, numero, inicio) VALUES (NEW.id, 1, now());
 RETURN NULL;
END $$;
CREATE TRIGGER planta_ciclo_inicial AFTER INSERT ON huerto_planta FOR EACH ROW EXECUTE FUNCTION chilito_planta_ciclo_inicial();

-- Terminar el ciclo: solo el dueño, con actor. Devuelve el id del ciclo nuevo.
CREATE FUNCTION public.chilito_terminar_ciclo(p_planta bigint, p_motivo text, p_nota text DEFAULT '') RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE pl huerto_planta%ROWTYPE; dueno bigint; a bigint := chilito_actor(); cerrado planta_ciclo%ROWTYPE; nuevo bigint;
BEGIN
 SELECT * INTO pl FROM huerto_planta WHERE id=p_planta FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'La planta no existe' USING ERRCODE='23514'; END IF;
 dueno := chilito_dueno_huerto(pl.huerto_id);
 IF dueno IS NULL THEN RAISE EXCEPTION 'El huerto está archivado' USING ERRCODE='23514'; END IF;
 IF a IS NULL THEN
  RAISE EXCEPTION 'Falta el actor: la aplicación debe fijar chilito.actor_id en la transacción' USING ERRCODE='23514';
 END IF;
 IF a IS DISTINCT FROM dueno THEN RAISE EXCEPTION 'Solo el dueño termina el ciclo de su planta' USING ERRCODE='23514'; END IF;
 IF p_motivo IS NULL OR p_motivo NOT IN """ + MOTIVOS + r""" THEN
  RAISE EXCEPTION 'Motivo de fin de ciclo no válido' USING ERRCODE='23514';
 END IF;
 UPDATE planta_ciclo SET fin=now(), motivo=p_motivo, nota=btrim(coalesce(p_nota, '')), cerrado_por_id=a
  WHERE planta_id=p_planta AND fin IS NULL RETURNING * INTO cerrado;
 IF NOT FOUND THEN RAISE EXCEPTION 'La planta no tiene un ciclo abierto' USING ERRCODE='23514'; END IF;
 INSERT INTO planta_ciclo(planta_id, numero, inicio) VALUES (p_planta, cerrado.numero + 1, now()) RETURNING id INTO nuevo;
 -- La planta vuelve a empezar; la línea de vida del ciclo nuevo arranca en «sin_sembrar».
 IF pl.etapa = 'sin_sembrar' THEN
  UPDATE huerto_planta SET fecha_siembra=NULL WHERE id=p_planta;
  INSERT INTO huerto_planta_etapa(planta_id, etapa, desde, registrada_por_id) VALUES (p_planta, 'sin_sembrar', chilito_hoy(), a);
 ELSE
  UPDATE huerto_planta SET etapa='sin_sembrar', etapa_desde=NULL, fecha_siembra=NULL WHERE id=p_planta;
 END IF;
 RETURN nuevo;
END $$;

-- Un cuidado de una planta no se fecha antes de su ciclo abierto (salvo en el ciclo 1, que abarca lo anterior).
CREATE FUNCTION public.chilito_cuidado_ciclo() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE c planta_ciclo%ROWTYPE;
BEGIN
 IF NEW.planta_numero IS NULL THEN RETURN NEW; END IF;
 SELECT k.* INTO c FROM planta_ciclo k JOIN huerto_planta p ON p.id=k.planta_id
  WHERE p.huerto_id=NEW.huerto_id AND p.numero=NEW.planta_numero AND k.fin IS NULL;
 IF FOUND AND c.numero > 1 AND NEW.realizado_en < c.inicio THEN
  RAISE EXCEPTION 'La fecha del cuidado es anterior al ciclo actual de la planta' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER cuidado_validar_ciclo BEFORE INSERT ON cuidado FOR EACH ROW EXECUTE FUNCTION chilito_cuidado_ciclo();

GRANT EXECUTE ON FUNCTION public.chilito_terminar_ciclo(bigint, text, text) TO chilito_pkg_runtime;
GRANT EXECUTE ON FUNCTION public.chilito_planta_ciclo_inicial(), public.chilito_cuidado_ciclo(), public.chilito_ciclo_reglas()
 TO chilito_pkg_runtime, chilito_pkg_iot;
"""

# Ciclo 1 de las plantas existentes: desde su primera etapa (medianoche de Mérida) o desde la creación del huerto.
INICIO_CICLO_1 = r"""coalesce((SELECT min(e.desde) FROM huerto_planta_etapa e WHERE e.planta_id=p.id)::timestamp AT TIME ZONE 'America/Merida',
         h.creado_en)"""
CICLO_1 = r"""
INSERT INTO planta_ciclo(planta_id, numero, inicio)
SELECT p.id, 1, """ + INICIO_CICLO_1 + r"""
FROM huerto_planta p JOIN huerto h ON h.id=p.huerto_id
WHERE NOT EXISTS (SELECT 1 FROM planta_ciclo c WHERE c.planta_id=p.id)
ORDER BY p.id;
"""

# Línea de vida por referencia: las etapas existentes son del ciclo 1; las nuevas toman el ciclo abierto al insertarse.
# (El historial es inmutable: solo aquí, en la migración, se suspende su trigger para rellenar la columna.)
ETAPAS = r"""
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE huerto_planta_etapa DISABLE TRIGGER inmutable;
UPDATE huerto_planta_etapa e SET ciclo_id=c.id FROM planta_ciclo c WHERE c.planta_id=e.planta_id AND c.numero=1 AND e.ciclo_id IS NULL;
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE huerto_planta_etapa ENABLE TRIGGER inmutable;
ALTER TABLE huerto_planta_etapa ALTER COLUMN ciclo_id SET NOT NULL;
CREATE INDEX etapa_ciclo_idx ON huerto_planta_etapa(ciclo_id);
CREATE FUNCTION public.chilito_etapa_ciclo() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 NEW.ciclo_id := (SELECT id FROM planta_ciclo WHERE planta_id=NEW.planta_id AND fin IS NULL);
 IF NEW.ciclo_id IS NULL THEN RAISE EXCEPTION 'La planta no tiene un ciclo abierto' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER etapa_ciclo BEFORE INSERT ON huerto_planta_etapa FOR EACH ROW EXECUTE FUNCTION chilito_etapa_ciclo();
GRANT EXECUTE ON FUNCTION public.chilito_etapa_ciclo() TO chilito_pkg_runtime, chilito_pkg_iot;
SET CONSTRAINTS ALL DEFERRED;
"""

QUITAR_ETAPAS = r"""
DROP TRIGGER etapa_ciclo ON huerto_planta_etapa;
DROP FUNCTION public.chilito_etapa_ciclo();
DROP INDEX etapa_ciclo_idx;
ALTER TABLE huerto_planta_etapa ALTER COLUMN ciclo_id DROP NOT NULL;
"""

QUITAR_CICLOS = r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM planta_ciclo WHERE fin IS NOT NULL) THEN
  RAISE EXCEPTION 'Hay ciclos terminados: son historial y la reversión no los borra' USING ERRCODE='23514';
 END IF;
END $$;
DROP TRIGGER cuidado_validar_ciclo ON cuidado;
DROP FUNCTION public.chilito_cuidado_ciclo();
DROP FUNCTION public.chilito_terminar_ciclo(bigint, text, text);
DROP TRIGGER planta_ciclo_inicial ON huerto_planta;
DROP FUNCTION public.chilito_planta_ciclo_inicial();
DROP TRIGGER ciclo_reglas ON planta_ciclo;
DROP FUNCTION public.chilito_ciclo_reglas();
DELETE FROM planta_ciclo;
DROP INDEX ciclo_uno_abierto;
ALTER TABLE planta_ciclo DROP CONSTRAINT ciclo_nota_valida, DROP CONSTRAINT ciclo_cierre_coherente,
 DROP CONSTRAINT ciclo_motivo_valido, DROP CONSTRAINT ciclo_numero_valido;
"""

RECOMENDACIONES = r"""
-- Una recomendación por ciclo y situación (la tabla la crea huerto.0002 con su llave (ciclo, situación)): lo que impide repetirla.
ALTER TABLE planta_recomendacion ALTER COLUMN creada_en SET DEFAULT now();
ALTER TABLE planta_recomendacion ADD CONSTRAINT recomendacion_situacion_valida
 CHECK (situacion IN ('germinacion_larga','sustrato_saturado','seca_con_riegos'));
REVOKE ALL ON planta_recomendacion FROM PUBLIC;
GRANT SELECT ON planta_recomendacion TO chilito_pkg_runtime;
CREATE TRIGGER inmutable BEFORE UPDATE OR DELETE ON planta_recomendacion FOR EACH ROW EXECUTE FUNCTION chilito_inmutable();

-- Avisa una sola vez por ciclo y situación. Origen «dispositivo» si la revisa una lectura del equipo; si no, «sistema».
CREATE FUNCTION public.chilito_recomendar(p_ciclo bigint, p_situacion text, p_huerto bigint, p_dueno bigint,
                                          p_severidad text, p_titulo text, p_texto text, p_enlace text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE nueva boolean;
BEGIN
 INSERT INTO planta_recomendacion(ciclo_id, situacion) VALUES (p_ciclo, p_situacion) ON CONFLICT DO NOTHING RETURNING true INTO nueva;
 IF nueva THEN
  INSERT INTO notificacion(destinatario_id, origen, severidad, titulo, texto, huerto_id, enlace)
  VALUES (p_dueno, CASE WHEN session_user='chilito_pkg_iot' THEN 'dispositivo' ELSE 'sistema' END, p_severidad,
          left(p_titulo, 120), p_texto, p_huerto, p_enlace);
 END IF;
 RETURN coalesce(nueva, false);
END $$;

-- Revisa las tres situaciones de una planta en su ciclo abierto, al momento `p_momento` (por omisión, ahora).
CREATE FUNCTION public.chilito_recomendaciones_planta(p_planta bigint, p_momento timestamptz DEFAULT now()) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE pl huerto_planta%ROWTYPE; dueno bigint; ciclo bigint; enlace text; n integer := 0;
        ultima numeric; ultima_baja timestamptz; racha_desde timestamptz; dia date; dias_secos integer; riegos integer;
BEGIN
 SELECT * INTO pl FROM huerto_planta WHERE id=p_planta;
 IF NOT FOUND OR pl.etapa='sin_sembrar' THEN RETURN 0; END IF;
 dueno := chilito_dueno_huerto(pl.huerto_id);
 IF dueno IS NULL THEN RETURN 0; END IF;
 SELECT id INTO ciclo FROM planta_ciclo WHERE planta_id=p_planta AND fin IS NULL;
 IF ciclo IS NULL THEN RETURN 0; END IF;
 enlace := '#huerto/plantas/' || pl.numero;

 -- 1. Más de 21 días en germinación.
 IF pl.etapa='germinacion' AND pl.etapa_desde IS NOT NULL AND (p_momento AT TIME ZONE 'America/Merida')::date - pl.etapa_desde > 21 THEN
  IF chilito_recomendar(ciclo, 'germinacion_larga', pl.huerto_id, dueno, 'advertencia', pl.nombre || ' lleva más de 21 días en germinación',
       'Tu semilla aún no germina. Si no brota pronto, considera volver a sembrar.', enlace) THEN n := n + 1; END IF;
 END IF;

 -- 2. Sustrato ≥ 90 % durante 12 h o más: la última lectura alta y ninguna baja en la racha que empezó hace 12 h o más.
 SELECT mp.humedad_sustrato_pct INTO ultima FROM medicion m JOIN medicion_planta mp ON mp.medicion_id=m.id
  WHERE m.huerto_id=pl.huerto_id AND mp.planta_numero=pl.numero AND m.medida_en <= p_momento ORDER BY m.medida_en DESC LIMIT 1;
 IF ultima >= 90 THEN
  SELECT max(m.medida_en) INTO ultima_baja FROM medicion m JOIN medicion_planta mp ON mp.medicion_id=m.id
   WHERE m.huerto_id=pl.huerto_id AND mp.planta_numero=pl.numero AND m.medida_en <= p_momento
     AND m.medida_en > p_momento - interval '3 days' AND mp.humedad_sustrato_pct < 90;
  SELECT min(m.medida_en) INTO racha_desde FROM medicion m JOIN medicion_planta mp ON mp.medicion_id=m.id
   WHERE m.huerto_id=pl.huerto_id AND mp.planta_numero=pl.numero AND m.medida_en <= p_momento
     AND m.medida_en > coalesce(ultima_baja, p_momento - interval '3 days');
  IF racha_desde <= p_momento - interval '12 hours' THEN
   IF chilito_recomendar(ciclo, 'sustrato_saturado', pl.huerto_id, dueno, 'advertencia', 'Riesgo de pudrición de raíz en ' || pl.nombre,
        'El sustrato lleva 12 horas o más con 90 % de humedad o más. Deja de regar hasta que la superficie se seque y revisa que el agua escurra: el exceso de agua puede pudrir las raíces.',
        enlace) THEN n := n + 1; END IF;
  END IF;
 END IF;

 -- 3. «Seca» (< 35 % todo el día) los 3 últimos días de Mérida, con lecturas cada día y al menos 2 riegos de la bomba.
 dia := (p_momento AT TIME ZONE 'America/Merida')::date;
 SELECT count(*) INTO dias_secos FROM (
  SELECT (m.medida_en AT TIME ZONE 'America/Merida')::date AS d, max(mp.humedad_sustrato_pct) AS maxima
  FROM medicion m JOIN medicion_planta mp ON mp.medicion_id=m.id
  WHERE m.huerto_id=pl.huerto_id AND mp.planta_numero=pl.numero AND m.medida_en <= p_momento
    AND m.medida_en >= (dia - 2)::timestamp AT TIME ZONE 'America/Merida'
  GROUP BY 1) x WHERE x.maxima < 35;
 IF dias_secos = 3 THEN
  SELECT count(*) INTO riegos FROM actuacion
   WHERE huerto_id=pl.huerto_id AND actuador='bomba' AND accion='encendido' AND planta_numero=pl.numero
     AND ocurrido_en <= p_momento AND ocurrido_en >= (dia - 2)::timestamp AT TIME ZONE 'America/Merida';
  IF riegos >= 2 THEN
   IF chilito_recomendar(ciclo, 'seca_con_riegos', pl.huerto_id, dueno, 'advertencia', pl.nombre || ' sigue seca a pesar de los riegos',
        'Lleva 3 días seguidos marcada «Seca» aunque se ha regado. Revisa si sigue viva: tallo firme y hojas que no se desprenden al tocarlas. Si murió, termina su ciclo para volver a empezar.',
        enlace) THEN n := n + 1; END IF;
  END IF;
 END IF;
 RETURN n;
END $$;

-- Las de humedad, con cada lectura del equipo.
CREATE FUNCTION public.chilito_recomendaciones_lectura() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE m medicion%ROWTYPE; p bigint;
BEGIN
 SELECT * INTO m FROM medicion WHERE id=NEW.medicion_id;
 SELECT id INTO p FROM huerto_planta WHERE huerto_id=m.huerto_id AND numero=NEW.planta_numero;
 IF p IS NOT NULL THEN PERFORM chilito_recomendaciones_planta(p, m.medida_en); END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER recomendaciones_lectura AFTER INSERT ON medicion_planta FOR EACH ROW EXECUTE FUNCTION chilito_recomendaciones_lectura();

-- Tarea periódica (propietario): todas las plantas de los huertos activos. Devuelve cuántas recomendaciones nuevas hubo.
CREATE FUNCTION public.chilito_revisar_recomendaciones() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE p bigint; n integer := 0;
BEGIN
 FOR p IN SELECT pl.id FROM huerto_planta pl JOIN huerto h ON h.id=pl.huerto_id WHERE h.estado='activo' AND pl.etapa<>'sin_sembrar' ORDER BY pl.id LOOP
  n := n + chilito_recomendaciones_planta(p);
 END LOOP;
 RETURN n;
END $$;

GRANT EXECUTE ON FUNCTION public.chilito_recomendaciones_planta(bigint, timestamptz), public.chilito_revisar_recomendaciones() TO chilito_pkg_runtime;
GRANT EXECUTE ON FUNCTION public.chilito_recomendaciones_lectura() TO chilito_pkg_iot, chilito_pkg_runtime;
"""

QUITAR_RECOMENDACIONES = r"""
DROP TRIGGER recomendaciones_lectura ON medicion_planta;
DROP FUNCTION public.chilito_recomendaciones_lectura();
DROP FUNCTION public.chilito_revisar_recomendaciones();
DROP FUNCTION public.chilito_recomendaciones_planta(bigint, timestamptz);
DROP FUNCTION public.chilito_recomendar(bigint, text, bigint, bigint, text, text, text, text);
DROP TRIGGER inmutable ON planta_recomendacion;
DELETE FROM planta_recomendacion;   -- la reversión entera se deshace si hay ciclos terminados (QUITAR_CICLOS)
ALTER TABLE planta_recomendacion DROP CONSTRAINT recomendacion_situacion_valida;
"""

GUIA_FIN_CICLO = """El habanero es una planta perenne: en un clima cálido, como el de Yucatán, y bajo techo puede vivir y dar chiles durante varias temporadas. No muere sola al terminar una cosecha.

Después de una cosecha abundante es normal que la planta descanse unas semanas antes de volver a florecer. Mientras siga con hojas sanas y tallo firme, sigue cuidándola: puede volver a producir.

En YouGarden, el ciclo de una planta lo terminas tú, desde su ficha, con «Terminar ciclo». Hazlo cuando quieras empezar de nuevo en ese lugar: porque terminaste con ella, porque murió, porque la semilla no germinó o por pudrición o plaga. La planta vuelve a «Sin sembrar» y conserva su nombre.

Terminar un ciclo no borra nada. Su línea de vida y sus cuidados quedan en «Ciclos anteriores» para que puedas consultarlos. No se puede deshacer."""

GUIA_MURIENDO = """Algunas señales de que una planta está muriendo:

· Hojas marchitas que no se recuperan después de regar, o que se secan y se caen al tocarlas.
· Tallo blando, oscuro o hueco en la base, o raíces cafés y blandas con mal olor: suele ser pudrición por exceso de agua.
· Tallo seco y quebradizo, sin ninguna hoja verde.
· El sustrato sigue seco a pesar de los riegos, o sigue empapado durante muchas horas.
· Plagas que cubren la mayor parte de la planta.

Antes de darla por perdida, raspa con la uña un poco de la corteza del tallo: si por dentro está verde, la planta sigue viva. Corrige el riego, quita las hojas dañadas y dale unos días.

Si ya no tiene partes verdes o la raíz está podrida, termina su ciclo desde su ficha para volver a sembrar. Su historial se conserva en «Ciclos anteriores»."""


def guias(apps, schema_editor):
    """Publicadas y sin autor, como las iniciales: el trigger de guías exige un admin con «gestionar_guias», que en una
    migración no existe, así que se suspende solo durante estos INSERT. Si la clave ya existe, no se toca."""
    filas = (('ciclo-habanero-fin', '¿Cuándo termina el ciclo de mi habanero?', GUIA_FIN_CICLO, 100),
             ('planta-muriendo-senales', 'Señales de que mi planta está muriendo', GUIA_MURIENDO, 110))
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('ALTER TABLE guia_cuidado DISABLE TRIGGER guia_reglas')
        for clave, pregunta, respuesta, orden in filas:
            cursor.execute("INSERT INTO guia_cuidado (clave, pregunta, respuesta, orden, estado, version, creado_en, actualizado_en) "
                           "VALUES (%s, %s, %s, %s, 'publicada', 1, now(), now()) ON CONFLICT (clave) DO NOTHING",
                           [clave, pregunta, respuesta, orden])
        # Las llaves foráneas diferidas dejan eventos pendientes que impiden el ALTER TABLE: se comprueban ya.
        cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        cursor.execute('ALTER TABLE guia_cuidado ENABLE TRIGGER guia_reglas')
        cursor.execute('SET CONSTRAINTS ALL DEFERRED')


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0006_deposito_rellenar'),
        ('huerto', '0002_planta_ciclo'),
        ('datos', '0003_deposito_deteccion'),
    ]

    operations = [
        migrations.RunSQL(sql=CICLOS, reverse_sql=QUITAR_CICLOS),
        migrations.RunSQL(sql=CICLO_1, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=ETAPAS, reverse_sql=QUITAR_ETAPAS),
        migrations.RunSQL(sql=RECOMENDACIONES, reverse_sql=QUITAR_RECOMENDACIONES),
        migrations.RunPython(guias, migrations.RunPython.noop),
    ]
