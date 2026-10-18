"""Stage 2 contracts against the isolated PostgreSQL DB. Mail stays in test memory."""
import re
import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification_by_code import EMAIL_VERIFICATION_CODE_SESSION_KEY
from cuentas.email import AuthorizedSMTPBackend, MailUnavailable
from huerto.models import Membresia
from huerto.services import provision_garden, assign_membership

P = "/_allauth/browser/v1/"
PASSWORD = "Frase extensa exclusiva para pruebas aisladas 73!"
NEW_PASSWORD = "Otra frase extensa exclusiva para pruebas 81!"

class AccessIntegrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.get("/api/acceso/configuracion")

    def user(self, email="cuenta@example.invalid", verified=True):
        user = get_user_model().objects.create_user(email, PASSWORD)
        EmailAddress.objects.create(user=user, email=email, verified=verified, primary=True)
        return user

    def post(self, suffix, data, client=None, method="post"):
        client = client or self.client
        token = client.cookies.get("csrftoken")
        return getattr(client, method)(P+suffix, data, content_type="application/json",
                                      HTTP_X_CSRFTOKEN=token.value if token else "")

    def login(self, user=None, client=None):
        user = user or self.user()
        return self.post("auth/login", {"email":user.email,"password":PASSWORD},client=client)

    def pending(self):
        user = self.user(verified=False)
        response = self.login(user)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(mail.outbox),1)
        return user

    def code(self):
        return self.client.session[EMAIL_VERIFICATION_CODE_SESSION_KEY]["code"]

    def reset_key(self, user):
        response = self.post("auth/password/request", {"email":user.email})
        self.assertEqual(response.status_code,200)
        match = re.search(r"http://127\.0\.0\.1:8766/index\.html#restablecer\?token=([^\s]+)",mail.outbox[-1].body)
        self.assertTrue(match is not None, "Expected canonical local reset link")
        return match.group(1)

    def test_bootstrap_closed_and_csrf_cookie_no_session_token(self):
        response = self.client.get("/api/acceso/configuracion")
        self.assertFalse(response.json()["registrationAllowed"])
        self.assertFalse(response.json()["legal"]["approved"])
        self.assertIsNone(response.json()["legal"]["termsVersion"])
        self.assertTrue(response.cookies["csrftoken"].value)
        self.assertTrue("no-store" in response["Cache-Control"])

    def test_registration_closed_even_with_acceptance_and_direct_request(self):
        for acceptance in [False,True]:
            response=self.post("auth/signup",{"email":"new@example.invalid","password":PASSWORD,"termsAccepted":acceptance})
            self.assertEqual(response.status_code,403)
            self.assertEqual(response.json()["code"],"registration-disabled")
        self.assertFalse(get_user_model().objects.exists())
        self.assertEqual(len(mail.outbox),0)

    def test_mutations_require_csrf_including_login_signup_and_logout(self):
        client=Client(enforce_csrf_checks=True)
        for path,method in [("auth/login","post"),("auth/signup","post"),("auth/session","delete"),("auth/password/request","post")]:
            response=getattr(client,method)(P+path,{},content_type="application/json")
            self.assertEqual(response.status_code,403)
            self.assertEqual(response.json()["code"],"csrf-failed")

    def test_foreign_origin_rejected_even_with_token(self):
        response=self.client.post(P+"auth/login",{},content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,HTTP_ORIGIN="https://other.example.invalid")
        self.assertEqual(response.status_code,403)

    def test_login_requires_correct_credentials_and_no_email_each_login(self):
        user=self.user()
        bad=self.post("auth/login",{"email":user.email,"password":"incorrecta"})
        self.assertEqual(bad.status_code,400)
        self.assertEqual(self.login(user).status_code,200)
        self.assertEqual(len(mail.outbox),0)

    def test_session_restores_in_another_client_and_logout_revokes_it(self):
        user=self.user()
        self.login(user)
        second=Client()
        second.cookies=self.client.cookies.copy()
        self.assertEqual(second.get("/api/cuenta").status_code,200)
        self.assertTrue(self.client.cookies["sessionid"]["httponly"])
        self.assertEqual(self.client.cookies["sessionid"]["samesite"],"Lax")
        self.assertEqual(self.post("auth/session",{},method="delete").status_code,401)
        self.assertEqual(second.get("/api/cuenta").status_code,401)

    def test_profile_uses_session_identity_ignores_requested_user(self):
        own=self.user()
        other=self.user("otra@example.invalid")
        self.login(own)
        body=self.client.get("/api/cuenta?user="+str(other.pk)).json()
        self.assertEqual(body["email"],own.email)
        self.assertTrue(body["verified"])
        self.assertFalse(body["gardenAssigned"])
        self.assertFalse(Membresia.objects.exists())

    def test_profile_denies_missing_session_or_revoked_verification(self):
        self.assertEqual(self.client.get("/api/cuenta").status_code,401)
        user=self.user()
        self.login(user)
        EmailAddress.objects.filter(user=user).update(verified=False)
        self.assertEqual(self.client.get("/api/cuenta").status_code,403)
        self.assertEqual(self.post("account/password/change",{"current_password":PASSWORD,"new_password":NEW_PASSWORD}).status_code,403)

    def test_profile_membership_is_explicit(self):
        user=self.user()
        garden=provision_garden()
        assign_membership(user,garden)
        self.login(user)
        self.assertTrue(self.client.get("/api/cuenta").json()["gardenAssigned"])

    def test_code_metadata_does_not_consume_attempts_or_expose_code(self):
        self.pending()
        code=self.code()
        for _ in range(4):
            response=self.client.get("/api/acceso/verificacion")
            self.assertEqual(response.status_code,200)
            self.assertTrue(code not in response.content.decode(),"Code must not be exposed")
        state=self.client.session[EMAIL_VERIFICATION_CODE_SESSION_KEY]
        self.assertEqual(state["failed_attempts"],0)

    def test_verification_confirms_email_session_but_never_membership(self):
        user=self.pending()
        code=self.code()
        self.assertTrue(re.fullmatch("[0-9]{6}",code) is not None)
        response=self.post("auth/email/verify",{"key":code})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()["meta"]["is_authenticated"])
        self.assertTrue(code not in response.content.decode(),"Code must not be exposed")
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.assertFalse(Membresia.objects.filter(usuario=user).exists())
        self.assertEqual(self.post("auth/email/verify",{"key":code}).status_code,409)

    def test_wrong_code_exhausts_three_attempts_without_verifying(self):
        user=self.pending()
        for _ in range(3):
            self.assertEqual(self.post("auth/email/verify",{"key":"xxxxxx"}).status_code,400)
        self.assertEqual(self.client.get("/api/acceso/verificacion").status_code,409)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)

    def test_expired_code_rejected_by_server(self):
        user=self.pending()
        code=self.code()
        session=self.client.session
        state=session[EMAIL_VERIFICATION_CODE_SESSION_KEY]
        state["at"]=time.time()-601
        session[EMAIL_VERIFICATION_CODE_SESSION_KEY]=state
        session.save()
        self.assertEqual(self.post("auth/email/verify",{"key":code}).status_code,409)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)

    def test_resend_limited_and_bounded_by_process(self):
        self.pending()
        self.assertEqual(self.post("auth/email/verify/resend",{}).status_code,429)
        cache.clear()  # Only test isolation; do not reset quotas in the application.
        self.assertEqual(self.post("auth/email/verify/resend",{}).status_code,200)
        self.assertEqual(len(mail.outbox),2)
        session=self.client.session
        state=session[EMAIL_VERIFICATION_CODE_SESSION_KEY]
        state["resend_count"]=5
        session[EMAIL_VERIFICATION_CODE_SESSION_KEY]=state
        session.save()
        cache.clear()
        self.assertEqual(self.post("auth/email/verify/resend",{}).status_code,409)

    def test_missing_mail_is_error_for_existing_and_unknown_addresses(self):
        user=self.user()
        with patch("cuentas.api.delivery_available",return_value=False):
            for email in [user.email,"unknown@example.invalid"]:
                response=self.post("auth/password/request",{"email":email})
                self.assertEqual(response.status_code,503)
                self.assertEqual(response.json()["code"],"mail-unavailable")
        self.assertEqual(len(mail.outbox),0)

    def test_smtp_failure_does_not_claim_delivery_or_expose_exception(self):
        self.user()
        with patch("allauth.account.adapter.DefaultAccountAdapter.send_mail",side_effect=MailUnavailable):
            response=self.post("auth/password/request",{"email":"cuenta@example.invalid"})
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json(),{"status":503,"code":"mail-unavailable"})

    def test_reset_link_is_local_single_use_and_does_not_log_in(self):
        user=self.user()
        token=self.reset_key(user)
        response=self.client.get(P+"auth/password/reset",HTTP_X_PASSWORD_RESET_KEY=token)
        self.assertEqual(response.status_code,200)
        self.assertTrue(token not in response.content.decode(),"Reset token must not be exposed")
        reset=self.post("auth/password/reset",{"key":token,"password":NEW_PASSWORD})
        self.assertEqual(reset.status_code,401)
        self.assertFalse(reset.json()["meta"]["is_authenticated"])
        user.refresh_from_db()
        self.assertTrue(user.check_password(NEW_PASSWORD))
        self.assertEqual(self.post("auth/password/reset",{"key":token,"password":PASSWORD}).status_code,400)
        self.assertEqual(self.client.get("/api/cuenta").status_code,401)

    def test_expired_reset_link_rejected(self):
        user=self.user()
        token=self.reset_key(user)
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            self.assertEqual(self.client.get(P+"auth/password/reset",HTTP_X_PASSWORD_RESET_KEY=token).status_code,400)

    def test_unknown_reset_uses_neutral_response(self):
        response=self.post("auth/password/request",{"email":"unknown@example.invalid"})
        self.assertEqual(response.status_code,200)
        self.assertFalse(get_user_model().objects.exists())

    def test_change_password_checks_current_and_invalidates_other_session(self):
        user=self.user()
        self.login(user)
        second=Client()
        second.cookies=self.client.cookies.copy()
        bad=self.post("account/password/change",{"current_password":"incorrecta","new_password":NEW_PASSWORD})
        self.assertEqual(bad.status_code,400)
        weak=self.post("account/password/change",{"current_password":PASSWORD,"new_password":"123"})
        self.assertEqual(weak.status_code,400)
        changed=self.post("account/password/change",{"current_password":PASSWORD,"new_password":NEW_PASSWORD})
        self.assertEqual(changed.status_code,200)
        self.assertEqual(self.client.get("/api/cuenta").status_code,200)
        self.assertEqual(second.get("/api/cuenta").status_code,401)

    def test_login_failures_are_rate_limited(self):
        user=self.user()
        responses=[self.post("auth/login",{"email":user.email,"password":"incorrecta"}) for _ in range(7)]
        limited=any(response.status_code==429 or any(error.get("code")=="too_many_login_attempts" for error in response.json().get("errors",[])) for response in responses)
        self.assertTrue(limited,"Expected server-side login rate limit")

    def test_only_browser_auth_surface_is_exposed(self):
        for path in ["/_allauth/app/v1/auth/login",P+"auth/code/request",P+"account/email",
                     P+"account/phone","/desarrollo/inicio.js"]:
            self.assertEqual(self.client.get(path).status_code,404)

    def test_smtp_backend_restricts_recipients_before_connecting(self):
        from django.core.mail import EmailMessage
        with patch("cuentas.email.mail_configuration",return_value=("authorized@example.invalid",{"authorized@example.invalid"},"test-only-secret")), patch("cuentas.email.SMTPBackend") as smtp:
            with self.assertRaises(MailUnavailable):
                AuthorizedSMTPBackend().send_messages([EmailMessage("Title","Body",to=["third@example.invalid"])])
            smtp.assert_not_called()
