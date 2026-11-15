"""allauth guarda mfa_authenticator con save() completo, lo que obliga a conceder
UPDATE sobre todas sus columnas. Este trigger impide usarlo para cambiar el dueño."""
from django.db import migrations


FORWARD = """
CREATE FUNCTION public.chilito_proteger_mfa() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.user_id IS DISTINCT FROM OLD.user_id
    OR NEW.type IS DISTINCT FROM OLD.type OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
  RAISE EXCEPTION 'La identidad de un autenticador no puede reasignarse' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER chilito_mfa_estable BEFORE UPDATE ON public.mfa_authenticator
 FOR EACH ROW EXECUTE FUNCTION public.chilito_proteger_mfa();
REVOKE ALL ON FUNCTION public.chilito_proteger_mfa() FROM PUBLIC;
"""

REVERSE = """
DROP TRIGGER chilito_mfa_estable ON public.mfa_authenticator;
DROP FUNCTION public.chilito_proteger_mfa();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("cuentas", "0006_identidad_correo_ampliada"),
        ("mfa", "0003_authenticator_type_uniq"),
    ]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
