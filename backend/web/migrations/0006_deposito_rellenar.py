"""Depósito: «Es hora de rellenar» con nivel bajo y una sola recarga por cada nivel bajo.

· Con agua → nivel bajo: el mismo aviso (título «Tu depósito necesita agua») con el texto «Tu depósito se quedó sin agua.
  Rellénalo y avísanos.» y enlace a #huerto. Uno por transición, como antes.
· «Nivel bajo actual» = las lecturas bajas posteriores a la última lectura con agua (chilito_deposito_bajo_desde).
· Recarga manual con equipo: solo con la última lectura en nivel bajo y sin otra recarga vigente en ese mismo nivel bajo
  (realizada o registrada después de que empezó). Así, si tras registrarla el flotador sigue en nivel bajo, no se duplica.
  Sin equipo (o sin lecturas del flotador), una cada 12 horas, igual que antes.
· Nivel bajo → con agua: no se pregunta «¿Ya lo rellenaste?» si la persona ya la registró en ese nivel bajo o en los 30 minutos
  anteriores (la ventana de la 0004). Si se pregunta, el aviso dice «Tu equipo detectó agua en el depósito. ¿Ya lo rellenaste?».
· Al registrar una recarga se resuelve el aviso de nivel bajo abierto del huerto (la persona ya avisó).
· Guía «deposito-recarga» actualizada si sigue con el texto de la 0005 y sin autor.

No cambia ningún modelo. Al revertir se restauran las funciones de la 0005; el texto de la guía se queda."""
import importlib
import re

from django.db import migrations

ANTERIOR = importlib.import_module('web.migrations.0005_recarga_por_confirmar')


def _funcion_0005(nombre):
    """La definición de la 0005, tal cual, como CREATE OR REPLACE (para revertir)."""
    encontrada = re.search(rf'CREATE (?:OR REPLACE )?FUNCTION public\.{nombre}\(.*?\nEND \$\$;\n', ANTERIOR.FUNCIONES, re.S)
    return re.sub(r'^CREATE (?:OR REPLACE )?FUNCTION', 'CREATE OR REPLACE FUNCTION', encontrada.group(0))


FUNCIONES = r"""
-- Inicio del nivel bajo en curso: la primera lectura baja después de la última con agua, contando solo las lecturas anteriores
-- a `antes`. NULL si la última de esas lecturas tiene agua (o no hay lecturas del flotador).
CREATE FUNCTION public.chilito_deposito_bajo_desde(h bigint, antes timestamptz) RETURNS timestamptz
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT min(m.medida_en) FROM medicion m
  WHERE m.huerto_id=h AND m.deposito_con_agua=false AND m.medida_en < antes
    AND m.medida_en > coalesce((SELECT max(w.medida_en) FROM medicion w
                                 WHERE w.huerto_id=h AND w.deposito_con_agua=true AND w.medida_en < antes), '-infinity')
$$;

-- La recarga vigente más reciente hecha desde `desde` y no después de `hasta` (NULL si no hay). La de una persona también
-- cuenta si la registró desde `desde` aunque la fechara antes; la confirmada de una detección cuenta por su hora detectada.
CREATE FUNCTION public.chilito_recarga_desde(h bigint, desde timestamptz, hasta timestamptz) RETURNS timestamptz
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
 SELECT max(r.realizado_en) FROM chilito_recargas_vigentes(h) r JOIN cuidado c ON c.id=r.id
  WHERE r.realizado_en <= hasta AND (r.realizado_en >= desde OR (r.origen='persona' AND c.registrado_en >= desde))
$$;

-- El flotador cambió. Con agua → nivel bajo: evento y aviso «Rellénalo y avísanos»; una detección pendiente queda «sin_confirmar».
-- Nivel bajo → con agua: evento y, si nadie registró la recarga en este nivel bajo, una detección pendiente con su aviso.
CREATE OR REPLACE FUNCTION public.chilito_deposito_flotador() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE anterior boolean; dueno bigint; nombre_huerto text; nueva uuid; bajo_desde timestamptz;
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
   VALUES (dueno, 'dispositivo', 'advertencia', 'Tu depósito necesita agua', 'Tu depósito se quedó sin agua. Rellénalo y avísanos.',
           NEW.huerto_id, '#huerto');
  END IF;
 ELSIF NEW.deposito_con_agua AND anterior IS NOT DISTINCT FROM false THEN
  INSERT INTO dispositivo_evento(dispositivo_id, huerto_id, tipo, ocurrido_en) VALUES (NEW.dispositivo_id, NEW.huerto_id, 'deposito_recargado', NEW.medida_en);
  UPDATE notificacion SET resuelta_en=now()
   WHERE huerto_id=NEW.huerto_id AND origen='dispositivo' AND titulo='Tu depósito necesita agua' AND resuelta_en IS NULL;
  bajo_desde := chilito_deposito_bajo_desde(NEW.huerto_id, NEW.medida_en);
  -- Si la persona ya avisó en este nivel bajo (o en los 30 minutos anteriores), es la misma recarga: no se pregunta.
  IF dueno IS NOT NULL AND chilito_recarga_desde(NEW.huerto_id, least(bajo_desde, NEW.medida_en - interval '30 minutes'), NEW.medida_en) IS NULL THEN
   INSERT INTO deposito_deteccion(huerto_id, detectada_en) VALUES (NEW.huerto_id, NEW.medida_en)
    ON CONFLICT (huerto_id) WHERE estado='pendiente' DO NOTHING
    RETURNING id INTO nueva;
   IF nueva IS NOT NULL THEN
    INSERT INTO notificacion(destinatario_id, origen, severidad, titulo, texto, huerto_id, enlace)
    VALUES (dueno, 'dispositivo', 'informacion', 'Confirma la recarga de tu depósito',
            'Tu equipo detectó agua en el depósito el ' || chilito_hora_merida(NEW.medida_en) || '. ¿Ya lo rellenaste?',
            NEW.huerto_id, '#huerto');
   END IF;
  END IF;
 END IF;
 RETURN NULL;
END $$;

-- Recarga manual con equipo: solo con nivel bajo y una vez por cada nivel bajo; sin equipo, una cada 12 horas.
CREATE OR REPLACE FUNCTION public.chilito_recarga_manual(h bigint, realizado timestamptz) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE ultima timestamptz; proxima timestamptz; bajo_desde timestamptz; registrada timestamptz;
BEGIN
 PERFORM 1 FROM huerto WHERE id=h FOR UPDATE;   -- dos registros simultáneos esperan su turno
 SELECT max(r.realizado_en) INTO ultima FROM chilito_recargas_vigentes(h) r;
 IF chilito_equipo_de_huerto(h) IS NOT NULL
    AND EXISTS(SELECT 1 FROM medicion m WHERE m.huerto_id=h AND m.deposito_con_agua IS NOT NULL) THEN
  bajo_desde := chilito_deposito_bajo_desde(h, 'infinity');
  IF bajo_desde IS NULL THEN
   IF ultima IS NULL THEN
    RAISE EXCEPTION 'Tu depósito tiene agua: podrás registrar una recarga cuando el flotador marque nivel bajo' USING ERRCODE='23514';
   END IF;
   RAISE EXCEPTION 'Tu depósito tiene agua desde tu última recarga (%): no hace falta registrar otra', chilito_hora_merida(ultima)
    USING ERRCODE='23514';
  END IF;
  registrada := chilito_recarga_desde(h, bajo_desde, 'infinity');
  IF registrada IS NOT NULL THEN
   RAISE EXCEPTION 'Ya registraste esta recarga (%): no hace falta registrar otra', chilito_hora_merida(registrada)
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

-- Registrar la recarga es «avisarnos»: el aviso de nivel bajo abierto del huerto queda resuelto.
CREATE FUNCTION public.chilito_recarga_resuelve_aviso() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
 UPDATE notificacion SET resuelta_en=now()
  WHERE huerto_id=NEW.huerto_id AND origen='dispositivo' AND titulo='Tu depósito necesita agua' AND resuelta_en IS NULL;
 RETURN NULL;
END $$;
CREATE TRIGGER recarga_resuelve_aviso AFTER INSERT ON cuidado FOR EACH ROW
 WHEN (NEW.tipo='rellenar_deposito') EXECUTE FUNCTION chilito_recarga_resuelve_aviso();

GRANT EXECUTE ON FUNCTION public.chilito_deposito_bajo_desde(bigint, timestamptz), public.chilito_recarga_desde(bigint, timestamptz, timestamptz),
 public.chilito_recarga_resuelve_aviso() TO chilito_pkg_runtime, chilito_pkg_iot;
"""

QUITAR_FUNCIONES = r"""
DROP TRIGGER recarga_resuelve_aviso ON cuidado;
DROP FUNCTION public.chilito_recarga_resuelve_aviso();
""" + _funcion_0005('chilito_deposito_flotador') + _funcion_0005('chilito_recarga_manual') + r"""
DROP FUNCTION public.chilito_recarga_desde(bigint, timestamptz, timestamptz);
DROP FUNCTION public.chilito_deposito_bajo_desde(bigint, timestamptz);
"""

TEXTO_GUIA = """Rellenar es añadir agua limpia al depósito con tus propias manos.

Si tu huerto tiene equipo, el flotador avisa cuando el agua llega a nivel bajo: te llega el aviso «Tu depósito se quedó sin agua. Rellénalo y avísanos.» y en Mi huerto verás «Es hora de rellenar tu depósito». Cuando lo rellenes, pulsa «Ya lo rellené» y confírmalo: la recarga queda registrada con esa hora.

Si tu equipo detecta agua antes de que nos avises, en Mi huerto verás «Tu equipo detectó agua en el depósito. ¿Ya lo rellenaste?». Elige «Sí, ya lo rellené» para registrarla con la hora detectada, o «No fue una recarga» si solo moviste el depósito y el flotador rebotó.

Solo cuenta una recarga por cada nivel bajo. Si la registras y tu equipo sigue marcando nivel bajo, revisa que el agua cubra el flotador; tu registro no se borra. Mientras tu depósito tenga agua, «Rellené el depósito» queda desactivado. Si tu huerto no tiene equipo, puedes registrar una recarga cada 12 horas como máximo.

Solo las recargas que registras o confirmas cuentan para calcular cuánto dura tu depósito.

Registrar un cuidado declara una acción que ya realizaste físicamente. No significa que el sistema la haya ejecutado o comprobado.

El flotador solo detecta nivel bajo. No mide los litros restantes ni confirma que el depósito esté lleno, así que comprueba el nivel a simple vista al rellenarlo."""


def actualizar_guia(apps, schema_editor):
    # Igual que en la 0005: el trigger de guías exige un admin con «gestionar_guias»; se suspende solo durante este UPDATE.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('ALTER TABLE guia_cuidado DISABLE TRIGGER guia_reglas')
        cursor.execute("UPDATE guia_cuidado SET version=version+1, actualizado_en=now(), respuesta=%s "
                       "WHERE clave='deposito-recarga' AND respuesta=%s AND actualizado_por_id IS NULL", [TEXTO_GUIA, ANTERIOR.TEXTO_GUIA])
        cursor.execute('ALTER TABLE guia_cuidado ENABLE TRIGGER guia_reglas')


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0005_recarga_por_confirmar'),
    ]

    operations = [
        migrations.RunSQL(sql=FUNCIONES, reverse_sql=QUITAR_FUNCIONES),
        migrations.RunPython(actualizar_guia, migrations.RunPython.noop),
    ]
