"""Stage A: real server validation, only isolated accounts and in-memory mail."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import get_default_password_validators
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.test import TestCase, Client
from allauth.account.adapter import get_adapter
from tests import test_access_integration as previous

class PasswordGuidanceTests(TestCase):
    setUp = previous.AccessIntegrationTests.setUp
    user = previous.AccessIntegrationTests.user
    post = previous.AccessIntegrationTests.post
    login = previous.AccessIntegrationTests.login
    reset_key = previous.AccessIntegrationTests.reset_key

    def test_public_policy_matches_server_validators_and_adapter(self):
        policy = self.client.get("/api/acceso/configuracion").json()["password"]
        self.assertEqual((policy["minLength"], policy["maxLength"]), (15, 256))
        minimum = next(v for v in get_default_password_validators() if hasattr(v, "min_length"))
        self.assertEqual(minimum.min_length, policy["minLength"])
        with self.assertRaises(ValidationError):
            get_adapter().clean_password("\U0001f680" * (policy["maxLength"] + 1))

    def test_code_points_at_boundaries_and_combining_marks_are_preserved(self):
        samples = ["\U0001f680" * n for n in (15, 16, 256)]
        samples += ["a\u0301" * 7 + "\U0001f680", " " + "\U0001f680" * 13 + " "]
        for value in samples:
            with self.subTest(length=len(value)):
                self.assertTrue(get_adapter().clean_password(value) == value,
                                "Adapter must preserve all characters without normalization")

    def test_adapter_rejects_short_excess_numeric_common_and_similar(self):
        user = get_user_model()(email="sustratoyhabanerofamiliar@example.invalid")
        for value in ["\U0001f680" * 14, "\U0001f680" * 257,
                      "123456789012345", "password", "sustratoyhabanerofamiliar"]:
            with self.subTest(length=len(value)):
                with self.assertRaises(ValidationError):
                    get_adapter().clean_password(value, user=user)

    def test_direct_change_rejects_invalid_values_without_javascript(self):
        user = self.user()
        self.login(user)
        for value in ["\U0001f680" * 14, "\U0001f680" * 257, "123456789012345"]:
            response = self.post("account/password/change",
                {"current_password":previous.PASSWORD, "new_password":value})
            self.assertEqual(response.status_code, 400)
            user.refresh_from_db()
            self.assertTrue(user.check_password(previous.PASSWORD), "Invalid input must not change password")

    def test_direct_change_accepts_256_astral_code_points(self):
        user = self.user()
        self.login(user)
        value = "\U0001f680" * 256
        response = self.post("account/password/change",
            {"current_password":previous.PASSWORD, "new_password":value})
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(value), "Full Unicode password must be retained")
        self.assertFalse(user.check_password(value[:-1]))

    def test_spaces_are_not_trimmed_in_change_or_login(self):
        user = self.user()
        self.login(user)
        value = " " + "\U0001f680" * 13 + " "
        response = self.post("account/password/change",
            {"current_password":previous.PASSWORD, "new_password":value})
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(value))
        other = Client(enforce_csrf_checks=True)
        other.get("/api/acceso/configuracion")
        self.assertEqual(self.post("auth/login", {"email":user.email, "password":value.strip()}, client=other).status_code, 400)
        self.assertEqual(self.post("auth/login", {"email":user.email, "password":value}, client=other).status_code, 200)

    def test_direct_recovery_rejects_short_and_excess_then_accepts_unicode(self):
        user = self.user()
        key = self.reset_key(user)
        for value in ["\U0001f680" * 14, "\U0001f680" * 257]:
            response = self.post("auth/password/reset", {"key":key, "password":value})
            self.assertEqual(response.status_code, 400)
            user.refresh_from_db()
            self.assertTrue(user.check_password(previous.PASSWORD))
        value = " " + "a\u0301" * 6 + "\U0001f680" + " "
        self.assertEqual(self.post("auth/password/reset", {"key":key, "password":value}).status_code, 401)
        user.refresh_from_db()
        self.assertTrue(user.check_password(value), "Recovery must preserve decomposed Unicode")
