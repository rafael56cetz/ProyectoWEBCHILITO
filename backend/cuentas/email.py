"""Local, explicitly authorized SMTP delivery; never a console fallback."""
import json
import smtplib
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.core.validators import validate_email
from config.private import PRIVATE_ROOT, secret
from cuentas.registration import local_email_recipients_allowed

class MailUnavailable(Exception):
    """Public errors must never include SMTP responses, recipients or tokens."""

def mail_configuration():
    try:
        data = json.loads((PRIVATE_ROOT / "correo_local.json").read_text(encoding="utf-8-sig"))
        sender = data["sender"].strip().lower()
        recipients = {address.strip().lower() for address in data.get("authorized_recipients", [])}
        validate_email(sender)
        if not sender.endswith("@gmail.com") or (not recipients and not local_email_recipients_allowed()):
            raise ValueError
        for address in recipients:
            validate_email(address)
        password = secret("ELCHILITO_SMTP_PASSWORD", "gmail_app_password.txt").replace(" ", "")
        if len(password) != 16:
            raise ValueError
        return sender, recipients, password
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, ImproperlyConfigured, ValidationError):
        raise MailUnavailable from None

def recipient_allowed(address, recipients):
    if not isinstance(address, str):
        return False
    normalized = address.strip().lower()
    try:
        validate_email(normalized)
    except ValidationError:
        return False
    return normalized in recipients or local_email_recipients_allowed()

def delivery_problem(email=None):
    # Test-only backend is selected by settings.testing, never by a query parameter.
    if settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend":
        return None
    try:
        _, recipients, _ = mail_configuration()
    except MailUnavailable:
        return "mail-unavailable"
    if email is not None and not recipient_allowed(email, recipients):
        return "email-not-authorized"
    return None

def delivery_available(email=None):
    return delivery_problem(email) is None

class AuthorizedSMTPBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sender, recipients, password = mail_configuration()
        messages = list(email_messages)
        for message in messages:
            if not message.recipients() or any(not recipient_allowed(address, recipients) for address in message.recipients()):
                raise MailUnavailable
            message.from_email = sender
        try:
            with SMTPBackend(host="smtp.gmail.com", port=587, username=sender,
                             password=password, use_tls=True, use_ssl=False,
                             timeout=10, fail_silently=False) as connection:
                sent = connection.send_messages(messages)
            if sent != len(messages):
                raise MailUnavailable
            return sent
        except (smtplib.SMTPException, OSError):
            raise MailUnavailable from None

class DisabledEmailBackend(BaseEmailBackend):
    """Retained for explicit closed-environment checks."""
    def send_messages(self, email_messages):
        raise MailUnavailable
