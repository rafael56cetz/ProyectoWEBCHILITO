from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test.runner import DiscoverRunner

class IsolatedDatabaseRunner(DiscoverRunner):
    """Use a pre-migrated isolated DB; never grant CREATEDB/TRUNCATE to the app."""
    def setup_databases(self, **kwargs):
        if self.parallel > 1:
            raise ImproperlyConfigured("Estas pruebas se ejecutan sin clones paralelos.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(),current_user")
            name, role = cursor.fetchone()
            cursor.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user")
            privileged = any(cursor.fetchone())
        if (name, role) != ("el_chilito_test", "el_chilito_test_app") or privileged:
            raise ImproperlyConfigured("Las pruebas requieren la base y rol aislados sin privilegios administrativos.")
        return []
    def teardown_databases(self, old_config, **kwargs):
        pass  # TestCase rolls back each test. No flush/drop or production connection.
