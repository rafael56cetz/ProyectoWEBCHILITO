from django.db import migrations

FORWARD = """
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
CREATE FUNCTION chilito_proteger_lectura_aviso() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.aviso_id IS DISTINCT FROM OLD.aviso_id OR NEW.usuario_id IS DISTINCT FROM OLD.usuario_id THEN
    RAISE EXCEPTION 'No se puede reasignar una lectura de aviso' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER chilito_lectura_aviso_estable BEFORE UPDATE ON huerto_avisoleido
FOR EACH ROW EXECUTE FUNCTION chilito_proteger_lectura_aviso();
"""
REVERSE = """
DROP TRIGGER chilito_lectura_aviso_estable ON huerto_avisoleido;
DROP FUNCTION chilito_proteger_lectura_aviso();
DROP TRIGGER chilito_aviso_estable ON huerto_aviso;
DROP FUNCTION chilito_proteger_aviso();
"""
class Migration(migrations.Migration):
    dependencies = [("huerto", "0003_avisos")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
