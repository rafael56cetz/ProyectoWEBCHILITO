"""Additional final-review cases. All accounts and mail remain in isolated test transactions."""
from unittest.mock import patch
from django.core.cache import cache
from django.test import Client, TestCase
from allauth.account.models import EmailAddress
from tests import test_access_integration as previous
P, PASSWORD, NEW_PASSWORD = previous.P, previous.PASSWORD, previous.NEW_PASSWORD

# Do not inherit TestCase subclasses here: that would run and count previous cases twice.
class FinalAccessReviewTests(TestCase):
    setUp = previous.AccessIntegrationTests.setUp
    user = previous.AccessIntegrationTests.user
    post = previous.AccessIntegrationTests.post
    login = previous.AccessIntegrationTests.login
    pending = previous.AccessIntegrationTests.pending
    code = previous.AccessIntegrationTests.code
    reset_key = previous.AccessIntegrationTests.reset_key

    def test_verification_code_is_bound_to_pending_session(self):
        user=self.pending()
        code=self.code()
        other=Client(enforce_csrf_checks=True)
        other.get("/api/acceso/configuracion")
        response=self.post("auth/email/verify",{"key":code},client=other)
        self.assertEqual(response.status_code,409)
        self.assertEqual(other.get("/api/acceso/verificacion").status_code,409)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(self.post("auth/email/verify",{"key":code}).status_code,200)

    def test_resend_invalidates_previous_code(self):
        user=self.pending()
        previous=self.code()
        replacement=str((int(previous)+1)%1000000).zfill(6)
        cache.clear()
        with patch("allauth.account.adapter.DefaultAccountAdapter.generate_email_verification_code",return_value=replacement):
            self.assertEqual(self.post("auth/email/verify/resend",{}).status_code,200)
        self.assertEqual(self.post("auth/email/verify",{"key":previous}).status_code,400)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(self.post("auth/email/verify",{"key":replacement}).status_code,200)

    def test_recovery_invalidates_previous_authenticated_session(self):
        user=self.user()
        self.login(user)
        previous=Client()
        previous.cookies=self.client.cookies.copy()
        recovery=Client(enforce_csrf_checks=True)
        recovery.get("/api/acceso/configuracion")
        original=self.client
        self.client=recovery
        try:
            token=self.reset_key(user)
            response=self.post("auth/password/reset",{"key":token,"password":NEW_PASSWORD})
            self.assertEqual(response.status_code,401)
            self.assertFalse(response.json()["meta"]["is_authenticated"])
            self.assertEqual(previous.get("/api/cuenta").status_code,401)
            self.assertEqual(self.post("auth/login",{"email":user.email,"password":PASSWORD}).status_code,400)
            self.assertEqual(self.post("auth/login",{"email":user.email,"password":NEW_PASSWORD}).status_code,200)
        finally:
            self.client=original

    def test_authenticated_session_is_rotated_from_anonymous_session(self):
        user=self.user()
        # A server-side anonymous session exists before authentication.
        session=self.client.session
        session["review_marker"]="nonsecret"
        session.save()
        previous_key=session.session_key
        self.login(user)
        current_key=self.client.cookies["sessionid"].value
        self.assertTrue(previous_key!=current_key,"Session identifier must rotate on login")
        from django.contrib.sessions.models import Session
        self.assertFalse(Session.objects.filter(session_key=previous_key).exists())

    def test_private_api_and_reset_validation_are_not_cached(self):
        user=self.user()
        self.login(user)
        for path in ["/api/cuenta","/_allauth/browser/v1/auth/session","/api/huertos/actual"]:
            response=self.client.get(path)
            self.assertTrue("no-store" in response.get("Cache-Control",""))
        response=self.client.get(P+"auth/password/reset",HTTP_X_PASSWORD_RESET_KEY="invalid-review-key")
        self.assertEqual(response.status_code,400)
        self.assertTrue("no-store" in response.get("Cache-Control",""))
