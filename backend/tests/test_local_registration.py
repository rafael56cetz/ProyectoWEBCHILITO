"""Stage B: authorized local signup, isolated PostgreSQL and in-memory email only."""
import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from io import StringIO
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.core.checks import run_checks, Tags
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification_by_code import EMAIL_VERIFICATION_CODE_SESSION_KEY as CODE_KEY
from cuentas.models import ConfirmacionRegistroLocal
from cuentas.email import MailUnavailable
from huerto.models import Membresia
from huerto.services import provision_garden, assign_membership
from tests import test_access_integration as previous

@override_settings(ELCHILITO_LOCAL_REGISTRATION_ENABLED=True, ALLOWED_HOSTS=["127.0.0.1"])
class LocalRegistrationTests(TestCase):
    post = previous.AccessIntegrationTests.post
    code = previous.AccessIntegrationTests.code

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1:8766")
        self.client.get("/api/acceso/configuracion")

    def signup(self, **changes):
        data={"email":"local-owner@example.invalid", "password":previous.PASSWORD, "termsAccepted":True}
        data.update(changes)
        return self.post("auth/signup", data)

    def verify(self):
        return self.post("auth/email/verify", {"key":self.code()})

    def test_configuration_allows_local_signup_without_approving_legal(self):
        body=self.client.get("/api/acceso/configuracion").json()
        self.assertTrue(body["registrationAllowed"])
        self.assertEqual(body["legal"], {"approved":False,"termsVersion":None,"privacyVersion":None})

    def test_disabled_flag_denies_signup_even_with_acceptance(self):
        with override_settings(ELCHILITO_LOCAL_REGISTRATION_ENABLED=False):
            self.assertEqual(self.signup().status_code,403)
        self.assertFalse(get_user_model().objects.exists())

    def test_public_profiles_hosts_proxy_and_cors_cannot_activate_exception(self):
        variants=[{"SETTINGS_MODULE":"config.settings.public"},{"ELCHILITO_LOCAL_PRESENTATION":False},
                  {"ALLOWED_HOSTS":["*"]},{"USE_X_FORWARDED_HOST":True},
                  {"SECURE_PROXY_SSL_HEADER":("HTTP_X_FORWARDED_PROTO","https")},
                  {"CORS_ALLOW_ALL_ORIGINS":True}]
        for variant in variants:
            with self.subTest(case=list(variant)[0]),override_settings(**variant):
                self.assertFalse(self.client.get("/api/acceso/configuracion").json()["registrationAllowed"])
                self.assertEqual(self.signup().status_code,403)
                self.assertTrue(any(error.id=="cuentas.E001" for error in run_checks(tags=[Tags.security])))

    def test_remote_peer_cannot_use_a_forged_local_host(self):
        remote=Client(enforce_csrf_checks=True,HTTP_HOST="127.0.0.1:8766",REMOTE_ADDR="192.0.2.5")
        self.assertFalse(remote.get("/api/acceso/configuracion").json()["registrationAllowed"])
        response=self.post("auth/signup",{"email":"remote@example.invalid","password":previous.PASSWORD,"termsAccepted":True},client=remote)
        self.assertEqual(response.status_code,403)
        self.assertFalse(get_user_model().objects.exists())

    def test_checkbox_requires_literal_boolean_true(self):
        for acceptance in [False,None,"true",1,{},[]]:
            with self.subTest(kind=type(acceptance).__name__):
                response=self.signup(termsAccepted=acceptance)
                self.assertEqual(response.status_code,400)
                self.assertEqual(response.json()["code"],"terms-required")
        response=self.post("auth/signup",{"email":"local@example.invalid","password":previous.PASSWORD})
        self.assertEqual(response.status_code,400)
        self.assertFalse(get_user_model().objects.exists())
        self.assertEqual(len(mail.outbox),0)

    def test_csrf_and_foreign_origin_remain_blocked(self):
        client=Client(HTTP_HOST="127.0.0.1:8766",enforce_csrf_checks=True)
        self.assertEqual(client.post(previous.P+"auth/signup",{},content_type="application/json").status_code,403)
        response=self.client.post(previous.P+"auth/signup",{},content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,HTTP_ORIGIN="https://foreign.example.invalid")
        self.assertEqual(response.status_code,403)
        self.assertFalse(get_user_model().objects.exists())

    def test_signup_exact_password_code_session_and_no_automatic_membership(self):
        password=" "+"\U0001f680"*13+" "
        response=self.signup(password=password)
        self.assertEqual(response.status_code,401)
        self.assertFalse(response.json()["meta"]["is_authenticated"])
        self.assertTrue(any(flow["id"]=="verify_email" and flow.get("is_pending") for flow in response.json()["data"]["flows"]))
        user=get_user_model().objects.get()
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff or user.is_superuser)
        confirmation=ConfirmacionRegistroLocal.objects.get(usuario=user)
        self.assertTrue(confirmation.casilla_marcada and confirmation.documentos_pendientes)
        self.assertIsNotNone(confirmation.confirmado_en)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(len(mail.outbox),1)
        self.assertTrue(self.code() not in response.content.decode(),"Code must remain out of API responses")
        self.assertEqual(self.verify().status_code,200)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.assertFalse(Membresia.objects.exists())
        self.assertFalse(self.client.get("/api/cuenta").json()["gardenAssigned"])
        self.assertEqual(self.client.get("/api/huertos/actual").status_code,403)

    def test_server_rejects_invalid_passwords_even_without_frontend(self):
        values=["\U0001f680"*14,"\U0001f680"*257,"123456789012345","password"]
        for value in values:
            with self.subTest(length=len(value)):
                response=self.signup(password=value)
                self.assertEqual(response.status_code,400)
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(ConfirmacionRegistroLocal.objects.exists())

    def test_similarity_validator_uses_signup_email(self):
        response=self.signup(email="sustratoyhabanerofamiliar@example.invalid",password="sustratoyhabanerofamiliar")
        self.assertEqual(response.status_code,400)
        self.assertFalse(get_user_model().objects.exists())

    def test_incorrect_signup_code_does_not_verify(self):
        self.signup()
        wrong=str((int(self.code())+1)%1000000).zfill(6)
        for _ in range(3):
            self.assertEqual(self.post("auth/email/verify",{"key":wrong}).status_code,400)
        self.assertFalse(EmailAddress.objects.get().verified)
        self.assertEqual(self.client.get("/api/acceso/verificacion").status_code,409)

    def test_expired_signup_code_does_not_verify(self):
        self.signup()
        code=self.code()
        session=self.client.session
        state=session[CODE_KEY];state["at"]=time.time()-601
        session[CODE_KEY]=state;session.save()
        self.assertEqual(self.post("auth/email/verify",{"key":code}).status_code,409)
        self.assertFalse(EmailAddress.objects.get().verified)

    def test_resend_waits_and_invalidates_previous_code(self):
        self.signup()
        old=self.code()
        self.assertEqual(self.post("auth/email/verify/resend",{}).status_code,429)
        cache.clear()  # Isolated test only, never a UI shortcut.
        new=str((int(old)+1)%1000000).zfill(6)
        with patch("allauth.account.adapter.DefaultAccountAdapter.generate_email_verification_code",return_value=new):
            self.assertEqual(self.post("auth/email/verify/resend",{}).status_code,200)
        self.assertEqual(self.post("auth/email/verify",{"key":old}).status_code,400)
        self.assertEqual(self.post("auth/email/verify",{"key":new}).status_code,200)

    def test_duplicate_email_keeps_one_account_and_generic_pending_response(self):
        user=get_user_model().objects.create_user("local-owner@example.invalid",previous.PASSWORD)
        EmailAddress.objects.create(user=user,email=user.email,primary=True,verified=True)
        response=self.signup()
        self.assertEqual(response.status_code,401)
        self.assertFalse(response.json()["meta"]["is_authenticated"])
        self.assertEqual(get_user_model().objects.count(),1)
        self.assertFalse(ConfirmacionRegistroLocal.objects.exists())
        self.assertEqual(len(mail.outbox),1)

    def test_unconfigured_delivery_creates_no_account(self):
        with patch("cuentas.api.delivery_problem",return_value="mail-unavailable"):
            response=self.signup()
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()["code"],"mail-unavailable")
        self.assertFalse(get_user_model().objects.exists())
        self.assertEqual(len(mail.outbox),0)

    def test_unauthorized_recipient_is_distinct_from_smtp_failure(self):
        with patch("cuentas.api.delivery_problem",return_value="email-not-authorized"):
            response=self.signup()
        self.assertEqual(response.status_code,403)
        self.assertEqual(response.json(),{"status":403,"code":"email-not-authorized"})
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(ConfirmacionRegistroLocal.objects.exists())
        self.assertEqual(len(mail.outbox),0)

    def test_recipient_diagnostic_does_not_disclose_account_existence(self):
        user=get_user_model().objects.create_user("local-owner@example.invalid",previous.PASSWORD)
        EmailAddress.objects.create(user=user,email=user.email,primary=True,verified=True)
        with patch("cuentas.api.delivery_problem",return_value="email-not-authorized"):
            response=self.signup()
        self.assertEqual(response.json(),{"status":403,"code":"email-not-authorized"})
        self.assertEqual(get_user_model().objects.count(),1)
        self.assertEqual(len(mail.outbox),0)

    @override_settings(EMAIL_BACKEND="cuentas.email.AuthorizedSMTPBackend")
    def test_delivery_reason_distinguishes_configuration_and_recipient(self):
        from cuentas.email import delivery_problem,delivery_available
        with patch("cuentas.email.mail_configuration",side_effect=MailUnavailable):
            self.assertEqual(delivery_problem("allowed@example.invalid"),"mail-unavailable")
            self.assertFalse(delivery_available())
        configuration=("sender@example.invalid",{"allowed@example.invalid"},"unused-test-secret")
        with patch("cuentas.email.mail_configuration",return_value=configuration):
            self.assertIsNone(delivery_problem(" ALLOWED@example.invalid "))
            self.assertTrue(delivery_available("allowed@example.invalid"))
            self.assertEqual(delivery_problem("other@example.invalid"),"email-not-authorized")
            self.assertFalse(delivery_available("other@example.invalid"))

    def test_smtp_failure_leaves_only_unverified_account_and_login_can_retry(self):
        with patch("allauth.account.adapter.DefaultAccountAdapter.send_mail",side_effect=MailUnavailable):
            response=self.signup()
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()["code"],"mail-unavailable")
        self.assertFalse(EmailAddress.objects.get().verified)
        self.assertEqual(ConfirmacionRegistroLocal.objects.count(),1)
        self.assertFalse(Membresia.objects.exists())
        self.assertEqual(self.client.get("/api/cuenta").status_code,401)
        cache.clear()
        login=self.post("auth/login",{"email":"local-owner@example.invalid","password":previous.PASSWORD})
        self.assertEqual(login.status_code,401)
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(self.verify().status_code,200)

    @override_settings(ACCOUNT_RATE_LIMITS={"signup":"2/m/ip"})
    def test_library_signup_rate_limit_still_applies(self):
        self.assertEqual(self.signup(email="first@example.invalid").status_code,401)
        self.assertEqual(self.signup(email="second@example.invalid").status_code,401)
        self.assertEqual(self.signup(email="third@example.invalid").status_code,429)
        self.assertEqual(get_user_model().objects.count(),2)

    def test_technical_confirmation_cannot_claim_approved_documents(self):
        self.signup()
        with self.assertRaises(IntegrityError),transaction.atomic():
            ConfirmacionRegistroLocal.objects.update(documentos_pendientes=False)

    def test_membership_requires_separate_explicit_assignment(self):
        self.signup();self.verify()
        user=get_user_model().objects.get()
        garden=provision_garden()
        self.assertEqual(self.client.get("/api/huertos/actual").status_code,403)
        call_command("asignar_huerto",email=user.email,huerto=garden.pk,stdout=StringIO())
        self.assertEqual(self.client.get("/api/huertos/actual").status_code,200)

    def test_browser_cannot_approve_documents_or_invent_effective_versions(self):
        response=self.signup(approved=True,termsVersion="untrusted-client",privacyVersion="untrusted-client")
        self.assertEqual(response.status_code,401)
        self.assertTrue(ConfirmacionRegistroLocal.objects.get().documentos_pendientes)
        legal=self.client.get("/api/acceso/configuracion").json()["legal"]
        self.assertEqual(legal,{"approved":False,"termsVersion":None,"privacyVersion":None})

    @override_settings(EMAIL_BACKEND="cuentas.email.AuthorizedSMTPBackend")
    def test_unlisted_address_signup_resend_login_and_reset_use_same_mail_policy(self):
        from tests.test_email_policy import local_mail_settings
        policy=local_mail_settings()
        policy.ELCHILITO_LOCAL_REGISTRATION_ENABLED=True
        configuration=("sender@example.invalid",{"previous@example.invalid"},"unused-test-secret")
        with patch("cuentas.registration.settings",policy), \
             patch("cuentas.email.mail_configuration",return_value=configuration), \
             patch("cuentas.email.SMTPBackend") as smtp:
            transport=smtp.return_value.__enter__.return_value
            transport.send_messages.side_effect=lambda messages: len(messages)
            response=self.signup(email="new@school.example")
            self.assertEqual(response.status_code,401)
            user=get_user_model().objects.get(email="new@school.example")
            self.assertFalse(EmailAddress.objects.get(user=user).verified)
            self.assertEqual(self.client.get("/api/cuenta").status_code,401)
            self.assertEqual(transport.send_messages.call_count,1)
            self.assertEqual(self.post("auth/email/verify/resend",{}).status_code,429)
            cache.clear()  # Isolated tests only.
            self.assertEqual(self.post("auth/email/verify/resend",{}).status_code,200)
            self.assertEqual(transport.send_messages.call_count,2)
            self.assertEqual(self.verify().status_code,200)
            self.assertTrue(EmailAddress.objects.get(user=user).verified)
            self.assertFalse(Membresia.objects.exists())
            self.post("auth/session",{},method="delete")
            login=self.post("auth/login",{"email":user.email,"password":previous.PASSWORD})
            self.assertEqual(login.status_code,200)
            self.assertEqual(transport.send_messages.call_count,2)
            self.post("auth/session",{},method="delete")
            self.assertEqual(self.post("auth/password/request",{"email":user.email}).status_code,200)
            self.assertEqual(transport.send_messages.call_count,3)
            self.assertEqual(self.signup(email="not-an-email").status_code,400)
            self.assertEqual(transport.send_messages.call_count,3)
