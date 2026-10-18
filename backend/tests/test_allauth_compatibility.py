from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings, Client
from allauth.account.models import EmailAddress
from huerto.models import Membresia

@override_settings(ROOT_URLCONF="tests.headless_urls")
class AllauthCompatibilityTests(TestCase):
    def test_browser_session_has_no_app_token(self):
        response = self.client.get("/_allauth/browser/v1/auth/session")
        self.assertEqual(response.status_code, 401)
        body = response.json()
        self.assertFalse(body["meta"]["is_authenticated"])
        self.assertNotIn("session_token", body.get("meta", {}))

    def test_registration_closed_even_at_library_endpoint(self):
        response = self.client.post("/_allauth/browser/v1/auth/signup", {
            "email": "closed@example.invalid",
            "password": "Frase extensa para cuenta de prueba 73!"
        }, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_verified_password_login_compatible_without_membership_grant(self):
        user = get_user_model().objects.create_user(
            "login@example.invalid", "Frase extensa para cuenta de prueba 73!")
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        response = self.client.post("/_allauth/browser/v1/auth/login", {
            "email": user.email, "password": "Frase extensa para cuenta de prueba 73!"
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["meta"]["is_authenticated"])
        self.assertTrue(response.cookies["sessionid"]["httponly"])
        self.assertFalse(Membresia.objects.filter(usuario=user).exists())

    def test_browser_login_rejects_missing_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post("/_allauth/browser/v1/auth/login", {
            "email": "noone@example.invalid", "password": "No es una cuenta real"
        }, content_type="application/json")
        self.assertEqual(response.status_code, 403)
