"""Local restart port resolution; no Docker or database access."""
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from tools.entorno import local_connection


class LocalConnectionTests(SimpleTestCase):
    def test_uses_current_container_binding_after_port_changes(self):
        with patch('tools.entorno.run', side_effect=[b'true\n', b'127.0.0.1:32770\n']), \
             patch('tools.entorno.subprocess.run', return_value=SimpleNamespace(returncode=0)):
            self.assertEqual(local_connection('own-test-container'), {
                'CHILITO_DB_HOST': '127.0.0.1', 'CHILITO_DB_PORT': '32770'})

    def test_rejects_unowned_container_before_resolving_connection(self):
        with patch('tools.entorno.run', return_value=b'false\n') as run:
            with self.assertRaises(RuntimeError):
                local_connection('unowned-test-container')
            self.assertEqual(run.call_count, 1)

    def test_rejects_external_ambiguous_or_invalid_bindings(self):
        for binding in [b'0.0.0.0:5432', b'127.0.0.1:0', b'127.0.0.1:65536',
                        b'127.0.0.1:not-a-port', b'127.0.0.1:1234\n127.0.0.1:5678']:
            with self.subTest(binding=binding), \
                 patch('tools.entorno.run', side_effect=[b'true\n', binding]), \
                 patch('tools.entorno.subprocess.run') as probe:
                with self.assertRaises(RuntimeError):
                    local_connection('own-test-container')
                probe.assert_not_called()

    def test_unready_database_stops_without_recreating_environment(self):
        with patch('tools.entorno.run', side_effect=[b'true\n', b'127.0.0.1:32770\n']) as run, \
             patch('tools.entorno.subprocess.run', return_value=SimpleNamespace(returncode=1)) as probe, \
             patch('tools.entorno.time.sleep'):
            with self.assertRaises(RuntimeError):
                local_connection('own-test-container')
            self.assertEqual(run.call_count, 2)
            self.assertEqual(probe.call_count, 30)
            self.assertTrue(all(call.args[0][1] == 'exec' for call in probe.call_args_list))
