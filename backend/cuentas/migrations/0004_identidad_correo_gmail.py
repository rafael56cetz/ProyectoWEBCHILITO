"""Unicidad para puntos en gmail.com; conserva el correo y no fusiona cuentas."""
from django.db import migrations, models


FUNCTION = """
CREATE FUNCTION public.chilito_identidad_correo(correo text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
 SELECT CASE WHEN lower(split_part(btrim(correo),'@',2)) = 'gmail.com'
   THEN replace(lower(split_part(btrim(correo),'@',1)),'.','') || '@gmail.com'
   ELSE lower(btrim(correo)) END
$$;
DO $$ DECLARE conflictos bigint; BEGIN
 SELECT count(*) INTO conflictos FROM (
   SELECT public.chilito_identidad_correo(email) FROM public.cuentas_usuario
   GROUP BY public.chilito_identidad_correo(email) HAVING count(*) > 1
 ) grupos;
 IF conflictos > 0 THEN
   RAISE EXCEPTION 'Existen % grupos de correos equivalentes; revisar manualmente sin fusionar cuentas', conflictos;
 END IF;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [("cuentas", "0003_confirmacion_registro_local")]
    operations = [
        migrations.RunSQL(FUNCTION, "DROP FUNCTION public.chilito_identidad_correo(text);"),
        migrations.AddConstraint(
            model_name="usuario",
            constraint=models.UniqueConstraint(
                models.Func("email", function="public.chilito_identidad_correo",
                            output_field=models.CharField()),
                name="usuario_identidad_correo_unica",
            ),
        ),
    ]
