"""Primera versión de documentos y la finalidad elegida por el propietario.

Son borradores: permiten que banner y consentimientos guarden decisiones reales.
Publicar el texto final crea una versión nueva, que vuelve a pedir la decisión.
Va en SQL para quedar también en el script de instalación.
"""
from django.db import migrations


FORWARD = """
INSERT INTO public.privacidad_documentoversion(id,tipo,version,contenido_ref,contenido_sha256,registrado_en) VALUES
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e01','aviso_privacidad','0.1-borrador',
 'privacidad/documentos/aviso_privacidad-0.1-borrador.md',
 '9a55eaadc15d7fca8724a2136c872b14056c8d7faa6a4c4b105261d8197742bd',now()),
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e02','terminos','0.1-borrador',
 'privacidad/documentos/terminos-0.1-borrador.md',
 'e4887c9723ab81eff3771264c4734647f299ceeaef5cbc23fa5e15a62e209b08',now()),
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e03','politica_cookies','0.1-borrador',
 'privacidad/documentos/politica_cookies-0.1-borrador.md',
 'b529f06fc64c3f62f4f891af2fad9f6ff3f868f9cabecc5b36a22ae2b037efd9',now());
INSERT INTO public.privacidad_finalidadopcional(id,codigo,descripcion,creada_en) VALUES
('3f0c1a52-6d1e-4b7a-9c11-0a1b2c3d4e04','estadisticas_internas_navegacion',
 'Estadísticas internas voluntarias de navegación',now());
"""


class Migration(migrations.Migration):
    dependencies = [("privacidad", "0004_perfil_navegadores_estadisticas")]
    # Sin reversa de datos: estas tablas son historial y sus triggers impiden borrar.
    operations = [migrations.RunSQL(FORWARD, migrations.RunSQL.noop)]
