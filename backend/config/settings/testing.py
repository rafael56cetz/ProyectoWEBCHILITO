import os
os.environ["ELCHILITO_DB_SCOPE"] = "test"
os.environ["ELCHILITO_DB_ROLE"] = "app"
from .local import *  # noqa: F403,E402
TEST_RUNNER = "config.test_runner.IsolatedDatabaseRunner"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]

# Opt-in only for the isolated registration browser harness; ordinary tests stay closed.
ELCHILITO_LOCAL_REGISTRATION_ENABLED = os.environ.get("ELCHILITO_TEST_LOCAL_REGISTRATION") == "1"
