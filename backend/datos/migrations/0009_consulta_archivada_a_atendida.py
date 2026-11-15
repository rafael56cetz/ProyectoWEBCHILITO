"""Una consulta archivada puede marcarse como atendida (se archivó antes de responderla).

Solo cambia la función del disparador: el contenido de la consulta sigue inmutable,
no se borra y nunca vuelve a «nueva». Sin cambios de privilegios.
"""
from django.db import migrations

FUNCION = """
CREATE OR REPLACE FUNCTION public.chilito_consulta_atencion() RETURNS trigger
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
"""

ANTERIOR = """
CREATE OR REPLACE FUNCTION public.chilito_consulta_atencion() RETURNS trigger
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
"""


class Migration(migrations.Migration):
    dependencies = [('datos', '0008_soporte_resuelto_y_buzon')]
    operations = [migrations.RunSQL(FUNCION, ANTERIOR)]
