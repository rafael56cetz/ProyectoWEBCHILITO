"""Local recipient policy: real transport is replaced, never sends test messages."""
import json
import smtplib
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from django.conf import settings
from django.core.mail import EmailMessage
from django.test import SimpleTestCase, override_settings
from cuentas.checks import check_local_registration
from cuentas.email import (
    AuthorizedSMTPBackend, MailUnavailable, delivery_available,
    delivery_problem, mail_configuration, recipient_allowed,
)
from cuentas.registration import configuration_problems, local_email_recipients_allowed


def local_mail_settings():
    # Policy metadata only. This replaces the module's settings reference,
    # never Django's database connection or the isolated database configuration.
    return SimpleNamespace(
        SETTINGS_MODULE="config.settings.local",
        ELCHILITO_LOCAL_PRESENTATION=True,
        ELCHILITO_LOCAL_REGISTRATION_ENABLED=False,
        ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT=True,
        ALLOWED_HOSTS=["127.0.0.1"],
        USE_X_FORWARDED_HOST=False,
        SECURE_PROXY_SSL_HEADER=None,
        CORS_ALLOW_ALL_ORIGINS=False,
        HEADLESS_FRONTEND_URLS={"account_signup":"http://127.0.0.1:8766/index.html#registro"},
        DATABASES={"default":{"NAME":"el_chilito"}},
        EMAIL_BACKEND="cuentas.email.AuthorizedSMTPBackend",
    )


@override_settings(EMAIL_BACKEND="cuentas.email.AuthorizedSMTPBackend")
class LocalEmailPolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = local_mail_settings()
        self.policy_patch = patch("cuentas.registration.settings", self.policy)
        self.policy_patch.start()
        self.addCleanup(self.policy_patch.stop)
        self.mail_patch = patch("cuentas.email.mail_configuration", return_value=(
            "sender@example.invalid", {"previous@example.invalid"}, "unused-test-secret"))
        self.mock_configuration = self.mail_patch.start()
        self.addCleanup(self.mail_patch.stop)

    def test_any_valid_recipient_passes_without_changing_a_list(self):
        for address in ["new@school.example", "another@elsewhere.invalid", " NEW@SCHOOL.EXAMPLE "]:
            with self.subTest(address=address):
                self.assertIsNone(delivery_problem(address))
                self.assertTrue(delivery_available(address))

    def test_invalid_recipients_remain_blocked_before_smtp(self):
        for address in ["", "not-an-email", "one@example.invalid\r\nBcc: two@example.invalid"]:
            with self.subTest(address=address), patch("cuentas.email.SMTPBackend") as smtp:
                self.assertFalse(recipient_allowed(address, set()))
                with self.assertRaises(MailUnavailable):
                    AuthorizedSMTPBackend().send_messages([EmailMessage("Title", "Body", to=[address])])
                smtp.assert_not_called()
        self.assertFalse(recipient_allowed(None, set()))

    def test_transport_accepts_unlisted_to_cc_bcc_with_tls(self):
        message = EmailMessage("Title", "Body", to=["new@school.example"],
                               cc=["another@elsewhere.invalid"], bcc=["third@example.invalid"])
        with patch("cuentas.email.SMTPBackend") as smtp:
            transport = smtp.return_value.__enter__.return_value
            transport.send_messages.return_value = 1
            self.assertEqual(AuthorizedSMTPBackend().send_messages([message]), 1)
            self.assertTrue(smtp.call_args.kwargs["use_tls"])
            self.assertFalse(smtp.call_args.kwargs["fail_silently"])
            self.assertEqual(message.from_email, "sender@example.invalid")
            transport.send_messages.assert_called_once_with([message])

    def test_partial_failure_does_not_report_success(self):
        with patch("cuentas.email.SMTPBackend") as smtp:
            smtp.return_value.__enter__.return_value.send_messages.return_value = 0
            with self.assertRaises(MailUnavailable):
                AuthorizedSMTPBackend().send_messages([EmailMessage("Title", "Body", to=["new@example.invalid"])])

    def test_smtp_failure_stays_sanitized(self):
        with patch("cuentas.email.SMTPBackend") as smtp:
            smtp.return_value.__enter__.return_value.send_messages.side_effect = smtplib.SMTPException("private diagnostic")
            with self.assertRaises(MailUnavailable) as failure:
                AuthorizedSMTPBackend().send_messages([EmailMessage("Title", "Body", to=["new@example.invalid"])])
            self.assertEqual(str(failure.exception), "")

    def test_missing_configuration_still_blocks_delivery(self):
        self.mock_configuration.side_effect = MailUnavailable
        self.assertEqual(delivery_problem("new@example.invalid"), "mail-unavailable")
        with patch("cuentas.email.SMTPBackend") as smtp:
            with self.assertRaises(MailUnavailable):
                AuthorizedSMTPBackend().send_messages([EmailMessage("Title", "Body", to=["new@example.invalid"])])
            smtp.assert_not_called()

    def test_disabling_local_option_restores_restricted_mode(self):
        self.policy.ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT = False
        self.assertFalse(local_email_recipients_allowed())
        self.assertIsNone(delivery_problem("previous@example.invalid"))
        self.assertEqual(delivery_problem("new@example.invalid"), "email-not-authorized")
        with patch("cuentas.email.SMTPBackend") as smtp:
            with self.assertRaises(MailUnavailable):
                AuthorizedSMTPBackend().send_messages([EmailMessage("Title", "Body", to=["new@example.invalid"])])
            smtp.assert_not_called()

    def test_option_requires_boolean_true(self):
        self.policy.ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT = "true"
        self.assertFalse(local_email_recipients_allowed())

    def test_unsafe_profiles_fail_even_when_registration_is_disabled(self):
        variants = [
            {"SETTINGS_MODULE":"config.settings.public"},
            {"SETTINGS_MODULE":"config.settings.testing"},
            {"ELCHILITO_LOCAL_PRESENTATION":False},
            {"ALLOWED_HOSTS":["*"]},
            {"USE_X_FORWARDED_HOST":True},
            {"SECURE_PROXY_SSL_HEADER":("HTTP_X_FORWARDED_PROTO", "https")},
            {"CORS_ALLOW_ALL_ORIGINS":True},
            {"HEADLESS_FRONTEND_URLS":{"account_signup":"https://public.example/#registro"}},
            {"DATABASES":{"default":{"NAME":"other"}}},
            {"EMAIL_BACKEND":"django.core.mail.backends.console.EmailBackend"},
        ]
        for variant in variants:
            candidate = deepcopy(self.policy)
            for key, value in variant.items():
                setattr(candidate, key, value)
            with self.subTest(variant=list(variant)), patch("cuentas.registration.settings", candidate):
                self.assertTrue(configuration_problems())
                self.assertFalse(local_email_recipients_allowed())
                self.assertTrue(check_local_registration(None))
                self.assertEqual(delivery_problem("new@example.invalid"), "email-not-authorized")

    def test_isolated_test_settings_do_not_enable_real_unrestricted_mail(self):
        self.assertIs(settings.ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT, False)

    def test_local_configuration_no_longer_requires_recipient_list(self):
        # Use the imported original function, not the patched module lookup.
        with TemporaryDirectory(prefix="chilito-mail-policy-") as directory:
            root = Path(directory)
            (root/"correo_local.json").write_text(json.dumps({"sender":"sender@gmail.com"}), encoding="utf-8")
            with patch("cuentas.email.PRIVATE_ROOT", root), patch("cuentas.email.secret", return_value="x"*16):
                sender, recipients, _ = mail_configuration()
                self.assertEqual(sender, "sender@gmail.com")
                self.assertEqual(recipients, set())
                self.policy.ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT = False
                with self.assertRaises(MailUnavailable):
                    mail_configuration()
