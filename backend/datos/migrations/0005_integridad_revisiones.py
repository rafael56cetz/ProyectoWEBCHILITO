"""Integridad de revisiones. Añade funciones y triggers propios; no modifica ni
sustituye los de 0002, que siguen protegiendo mantenimiento y auditoría."""
from django.db import migrations


FORWARD = r"""
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
CREATE TRIGGER historial_revisionmantenimiento BEFORE UPDATE OR DELETE ON public.datos_revisionmantenimiento
 FOR EACH ROW EXECUTE FUNCTION public.chilito_historial_inmutable();

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

REVOKE ALL ON FUNCTION public.chilito_revision_mantenimiento(),public.chilito_auditoria_revision(),
 public.chilito_asignacion_estable() FROM PUBLIC;
"""

REVERSE = """
DROP TRIGGER chilito_asignacion_estable ON public.datos_asignacionmantenimiento;
DROP TRIGGER relacion_auditoria_revision ON public.datos_auditoria;
DROP TRIGGER historial_revisionmantenimiento ON public.datos_revisionmantenimiento;
DROP TRIGGER relacion_revisionmantenimiento ON public.datos_revisionmantenimiento;
DROP FUNCTION public.chilito_asignacion_estable();
DROP FUNCTION public.chilito_auditoria_revision();
DROP FUNCTION public.chilito_revision_mantenimiento();
"""


class Migration(migrations.Migration):
    dependencies = [("datos", "0004_revisiones_y_asignacion_mantenimiento")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
