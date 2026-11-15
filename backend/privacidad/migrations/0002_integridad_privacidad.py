"""Controles preparados para PostgreSQL; requieren validación real antes de uso.

No conceden permisos ni crean decisiones, finalidades, documentos o personas.
La autorización del usuario final y la transacción completa corresponden a Django.
"""
from django.db import migrations


FORWARD = r"""
CREATE FUNCTION public.chilito_privacidad_historial_inmutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 RAISE EXCEPTION 'El historial de privacidad no se modifica ni elimina mediante operaciones ordinarias'
  USING ERRCODE='23514';
END $$;

CREATE FUNCTION public.chilito_privacidad_sujeto_estable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.creado_en IS DISTINCT FROM OLD.creado_en
    OR (OLD.usuario_id IS NOT NULL AND NEW.usuario_id IS DISTINCT FROM OLD.usuario_id) THEN
  RAISE EXCEPTION 'No se reasigna un sujeto ni se desvincula una cuenta ya asociada'
   USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.chilito_privacidad_relaciones() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE
 tipo_documento varchar(16);
 d public.privacidad_decisionprivacidad%ROWTYPE;
 titular bigint;
BEGIN
 IF TG_TABLE_NAME='privacidad_decisionprivacidad' THEN
  SELECT tipo INTO tipo_documento FROM public.privacidad_documentoversion WHERE id=NEW.documento_id;
  IF (NEW.acto='aceptacion_terminos' AND tipo_documento IS DISTINCT FROM 'terminos')
     OR (NEW.acto IN ('lectura_aviso','consentimiento') AND tipo_documento IS DISTINCT FROM 'aviso_privacidad') THEN
   RAISE EXCEPTION 'El acto no corresponde al tipo de documento'
    USING ERRCODE='23514';
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
     OR d.finalidad_id IS DISTINCT FROM NEW.finalidad_id OR d.acto IS DISTINCT FROM 'consentimiento' THEN
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
    IF d.acto IS DISTINCT FROM 'consentimiento' OR d.decision IS DISTINCT FROM FALSE THEN
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

CREATE TRIGGER privacidad_sujeto_vinculo_estable BEFORE UPDATE
 ON public.privacidad_sujetoprivacidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_sujeto_estable();

CREATE TRIGGER privacidad_decision_documento BEFORE INSERT
 ON public.privacidad_decisionprivacidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_relaciones();

CREATE TRIGGER privacidad_preferencia_coherente BEFORE INSERT OR UPDATE
 ON public.privacidad_preferenciafinalidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_relaciones();

CREATE TRIGGER privacidad_evento_coherente BEFORE INSERT
 ON public.privacidad_eventoprivacidad FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_relaciones();
"""

HISTORIALES = ("documentoversion", "finalidadopcional", "decisionprivacidad", "eventoprivacidad")
for tabla in HISTORIALES:
    FORWARD += f"""
CREATE TRIGGER privacidad_{tabla}_inmutable BEFORE UPDATE OR DELETE
 ON public.privacidad_{tabla} FOR EACH ROW
 EXECUTE FUNCTION public.chilito_privacidad_historial_inmutable();
"""

FORWARD += """
REVOKE ALL ON FUNCTION public.chilito_privacidad_historial_inmutable(),
 public.chilito_privacidad_sujeto_estable(), public.chilito_privacidad_relaciones() FROM PUBLIC;
"""

REVERSE = """
DROP TRIGGER privacidad_sujeto_vinculo_estable ON public.privacidad_sujetoprivacidad;
DROP TRIGGER privacidad_decision_documento ON public.privacidad_decisionprivacidad;
DROP TRIGGER privacidad_preferencia_coherente ON public.privacidad_preferenciafinalidad;
DROP TRIGGER privacidad_evento_coherente ON public.privacidad_eventoprivacidad;
"""
for tabla in HISTORIALES:
    REVERSE += f"DROP TRIGGER privacidad_{tabla}_inmutable ON public.privacidad_{tabla};\n"
REVERSE += """
DROP FUNCTION public.chilito_privacidad_relaciones();
DROP FUNCTION public.chilito_privacidad_sujeto_estable();
DROP FUNCTION public.chilito_privacidad_historial_inmutable();
"""


class Migration(migrations.Migration):
    dependencies = [("privacidad", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
