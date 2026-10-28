"""Explicit delivery profiles, with no dependency on old private credentials.
File/locmem are test mailboxes. SMTP is opt-in, restricted and never a fallback.
"""
import os
import smtplib
from pathlib import Path
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.filebased import EmailBackend as FileBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class MailUnavailable(Exception):
    pass


def smtp_configuration():
    if getattr(settings, 'ELCHILITO_SMTP_ENABLED', False) is not True:
        raise MailUnavailable
    sender = settings.EMAIL_HOST_USER
    password = settings.EMAIL_HOST_PASSWORD
    mode = getattr(settings, 'ELCHILITO_SMTP_RECIPIENT_MODE', 'restricted')
    recipients = {value.strip().lower() for value in getattr(settings, 'ELCHILITO_SMTP_ALLOWED_RECIPIENTS', ())}
    if mode not in {'restricted', 'any-valid'}:
        raise MailUnavailable
    if (not sender or not password or not settings.EMAIL_HOST or (mode == 'restricted' and not recipients)
            or not settings.EMAIL_USE_TLS or settings.EMAIL_USE_SSL):
        raise MailUnavailable
    try:
        validate_email(sender)
        for recipient in recipients:
            validate_email(recipient)
    except ValidationError:
        raise MailUnavailable from None
    return recipients if mode == 'restricted' else None


def permitted_recipient(email, recipients):
    if not isinstance(email, str):
        return False
    try:
        validate_email(email.strip())
    except ValidationError:
        return False
    return recipients is None or email.strip().lower() in recipients


def delivery_problem(email=None):
    backend = settings.EMAIL_BACKEND
    if backend in {'django.core.mail.backends.locmem.EmailBackend',
                   'cuentas.email.ProtectedFileEmailBackend',
                   'django.core.mail.backends.filebased.EmailBackend'}:
        return None
    if backend != 'cuentas.email.AuthorizedSMTPBackend':
        return 'mail-unavailable'
    try:
        recipients = smtp_configuration()
    except MailUnavailable:
        return 'mail-unavailable'
    if email is not None and not permitted_recipient(email, recipients):
        return 'email-not-authorized'
    return None


def delivery_available(email=None):
    return delivery_problem(email) is None


class AuthorizedSMTPBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        recipients = smtp_configuration()
        messages = list(email_messages)
        for message in messages:
            if not message.recipients() or any(not permitted_recipient(address, recipients) for address in message.recipients()):
                raise MailUnavailable
        try:
            with SMTPBackend(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT,
                             username=settings.EMAIL_HOST_USER, password=settings.EMAIL_HOST_PASSWORD,
                             use_tls=True, use_ssl=False, timeout=settings.EMAIL_TIMEOUT,
                             fail_silently=False) as connection:
                sent = connection.send_messages(messages)
            if sent != len(messages):
                raise MailUnavailable
            return sent
        except (smtplib.SMTPException, OSError):
            raise MailUnavailable from None


class ProtectedFileEmailBackend(FileBackend):
    """Local test inbox: restrictive permissions, outside served frontend files."""
    def __init__(self, *args, **kwargs):
        path = Path(settings.EMAIL_FILE_PATH).expanduser()
        try:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(path, 0o700)
            super().__init__(*args, **kwargs)
        except OSError:
            raise MailUnavailable from None

    def open(self):
        try:
            created = super().open()
            if self.stream is not None:
                os.fchmod(self.stream.fileno(), 0o600)
            return created
        except OSError:
            raise MailUnavailable from None

    def send_messages(self, messages):
        try:
            return super().send_messages(messages)
        except OSError:
            raise MailUnavailable from None


class DisabledEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise MailUnavailable
