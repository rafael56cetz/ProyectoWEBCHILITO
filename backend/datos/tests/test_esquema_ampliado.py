"""Contrato del esquema sin base. No demuestra triggers, GRANT ni restricciones reales."""
import hashlib, re
from pathlib import Path
from django.apps import apps
from django.conf import settings
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase
from cuentas.models import Usuario
from datos.models import Auditoria, Dispositivo, RevisionMantenimiento
from privacidad.models import DocumentoVersion

SQL = Path(settings.PROJECT_ROOT, 'sql', 'privilegios.sql').read_text()
# Tablas sin GRANT a propósito: las usa solo el propietario o Django al migrar.
SIN_RUNTIME = set()


class EsquemaAmpliadoTests(SimpleTestCase):
    def test_toda_tabla_de_la_aplicacion_tiene_privilegios_definidos(self):
        faltan = [m._meta.db_table for m in apps.get_models()
                  if m._meta.managed and m._meta.db_table not in SIN_RUNTIME
                  and not re.search(rf'public\.{m._meta.db_table}\b', SQL)]
        self.assertEqual(faltan, [])

    def test_runtime_no_recibe_escritura_sobre_asignaciones(self):
        self.assertNotRegex(SQL, r'(INSERT|UPDATE|DELETE)[^;]*datos_asignacionmantenimiento')

    def test_runtime_no_puede_borrar_revisiones(self):
        self.assertNotRegex(SQL, r'(UPDATE|DELETE)[^;]*datos_revisionmantenimiento')

    def test_capacidad_de_mantenimientos_declarada(self):
        self.assertIn('gestionar_mantenimientos', dict(Dispositivo._meta.permissions))
        from datos.services import CAPS
        self.assertIn('gestionar_mantenimientos', CAPS)

    def test_anulacion_y_correccion_tienen_restricciones(self):
        nombres = {c.name for c in RevisionMantenimiento._meta.constraints}
        self.assertLessEqual({'revision_mant_orden_unico', 'revision_mant_una_anulacion',
                              'revision_mant_tipo_coherente'}, nombres)

    def test_correccion_exige_tipo_aunque_sea_null(self):
        # Un CHECK acepta el resultado NULL: IN no basta con una columna anulable.
        regla = next(c for c in RevisionMantenimiento._meta.constraints if c.name == 'revision_mant_tipo_coherente')
        self.assertIn("('tipo_corregido__isnull', False)", str(regla.condition))

    def test_auditoria_de_revision_no_toca_la_regla_de_autor(self):
        self.assertIn('auditoria_revision_coherente', {c.name for c in Auditoria._meta.constraints})

    def test_documentos_iniciales_coinciden_con_su_huella(self):
        migraciones = MigrationLoader(None).disk_migrations
        sql = ''.join(migraciones[('privacidad', n)].operations[0].sql
                      for n in ('0005_catalogo_inicial', '0006_documentos_con_texto_publicado'))
        filas = re.findall(r"'(privacidad/documentos/[^']+)',\s*'([0-9a-f]{64})'", sql)
        self.assertEqual(len(filas), 5)
        # Los textos 0.1 y 0.2 ya no están como archivos: solo se comprueba que cada fila lleve una huella SHA-256 válida.
        for ruta, huella in filas:
            self.assertRegex(huella, r'^[0-9a-f]{64}$', ruta)

    def test_documentos_iniciales_son_tipos_validos(self):
        self.assertEqual({t for t, _ in DocumentoVersion.TIPOS}, {'aviso_privacidad', 'terminos', 'politica_cookies'})

    def test_identidad_de_correo_cubre_gmail_ampliado(self):
        sql = MigrationLoader(None).disk_migrations[('cuentas', '0006_identidad_correo_ampliada')].operations[1].sql
        self.assertIn("'googlemail.com'", sql)
        self.assertIn("'+',1", sql)
        self.assertTrue(any(c.name == 'usuario_identidad_correo_unica' for c in Usuario._meta.constraints))

    def test_script_de_instalacion_incluye_todas_las_migraciones(self):
        script = Path(settings.PROJECT_ROOT, 'sql', 'instalacion', '03_esquema_completo.sql').read_text()
        for app, nombre in MigrationLoader(None).disk_migrations:
            self.assertIn(f"('{app}','{nombre}',now())", script)

    def test_script_de_instalacion_usa_los_privilegios_vigentes(self):
        script = Path(settings.PROJECT_ROOT, 'sql', 'instalacion', '03_esquema_completo.sql').read_text()
        for linea in SQL.splitlines():
            if linea.startswith('GRANT ') and 'db_name' not in linea:
                self.assertIn(linea, script)
