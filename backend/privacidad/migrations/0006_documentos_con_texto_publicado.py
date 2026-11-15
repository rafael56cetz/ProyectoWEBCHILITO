"""Versión 0.2: el texto que muestra la página legal, con constancia de lo que se vio."""
from django.db import migrations


FORWARD = """
INSERT INTO public.privacidad_documentoversion(id,tipo,version,contenido_ref,contenido_sha256,registrado_en) VALUES
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e05','aviso_privacidad','0.2-borrador',
 'privacidad/documentos/aviso_privacidad-0.2-borrador.md',
 'c1b1a3e626e43344b685e9c671d48c223126abd330985642702f6f48549e1c02',now()),
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e06','terminos','0.2-borrador',
 'privacidad/documentos/terminos-0.2-borrador.md',
 '565e817bab5f7fa8f65127db1d7c00033b6ce100757ac8a63c6b72d188ee5ce5',now());
"""


class Migration(migrations.Migration):
    dependencies = [("privacidad", "0005_catalogo_inicial")]
    # Sin reversa de datos: estas tablas son historial y sus triggers impiden borrar.
    operations = [migrations.RunSQL(FORWARD, migrations.RunSQL.noop)]
