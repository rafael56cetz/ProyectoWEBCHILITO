from django.db import migrations

FORWARD = """
CREATE FUNCTION chilito_proteger_relacion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME='huerto_zona' THEN
    IF NEW.huerto_id IS DISTINCT FROM OLD.huerto_id OR NEW.numero IS DISTINCT FROM OLD.numero THEN
      RAISE EXCEPTION 'La identidad de zona no puede reasignarse' USING ERRCODE='23514';
    END IF;
  ELSIF TG_TABLE_NAME='huerto_membresia' THEN
    IF NEW.huerto_id IS DISTINCT FROM OLD.huerto_id OR NEW.usuario_id IS DISTINCT FROM OLD.usuario_id THEN
      RAISE EXCEPTION 'La identidad de membresia no puede reasignarse' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER chilito_zona_estable BEFORE UPDATE ON huerto_zona
FOR EACH ROW EXECUTE FUNCTION chilito_proteger_relacion();
CREATE TRIGGER chilito_membresia_estable BEFORE UPDATE ON huerto_membresia
FOR EACH ROW EXECUTE FUNCTION chilito_proteger_relacion();
"""
REVERSE = """
DROP TRIGGER chilito_membresia_estable ON huerto_membresia;
DROP TRIGGER chilito_zona_estable ON huerto_zona;
DROP FUNCTION chilito_proteger_relacion();
"""

class Migration(migrations.Migration):
    dependencies = [("huerto", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
