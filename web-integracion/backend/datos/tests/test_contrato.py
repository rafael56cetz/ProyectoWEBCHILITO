from django.test import SimpleTestCase
from django.db.migrations.loader import MigrationLoader
from huerto.models import Huerto,Zona,Aviso
from datos.models import RevisionConocimiento,ValidacionVersion

class MigrationContractWithoutDatabaseTests(SimpleTestCase):
    def test_significant_text_regex_uses_one_backslash(self):
        for model in [Huerto,Zona,Aviso]:
            for constraint in model._meta.constraints:
                for child in getattr(constraint.condition,"children",[]):
                    if isinstance(child,tuple) and child[0].endswith('__regex'):
                        self.assertEqual(child[1],r'\S')
    def test_all_new_migration_dependencies_are_resolvable(self):
        loader=MigrationLoader(None)
        loader.graph.validate_consistency()
        state=loader.project_state()
        for model in ['mantenimiento','casosoporte','permisosoporte','sesiontecnica','solicitud','auditoria']:
            self.assertIsNotNone(state.apps.get_model('datos',model))
    def test_large_limits_use_length_not_postgresql_regex_repetition(self):
        for model in [RevisionConocimiento,ValidacionVersion]:
            for constraint in model._meta.constraints:
                self.assertNotIn('{20,10000}',str(constraint.condition))
                self.assertNotIn('{0,2000}',str(constraint.condition))
