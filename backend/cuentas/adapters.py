import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.mfa.adapter import DefaultMFAAdapter
from cryptography.fernet import Fernet
from django.conf import settings

from cuentas.email import MailUnavailable

logger = logging.getLogger(__name__)


class ClosedRegistrationAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        from cuentas.registration import local_registration_allowed
        return local_registration_allowed(request)

    def clean_password(self, password, user=None):
        from django.core.exceptions import ValidationError
        if len(password) > 256:
            raise ValidationError("Usa como máximo 256 caracteres.", code="password_too_long")
        return super().clean_password(password, user=user)

    def is_login_by_code_required(self, login):
        from allauth.mfa.models import Authenticator
        # El registro ya verificó el correo; TOTP o WebAuthn sustituyen al código.
        if login.signup or (login.user is not None and Authenticator.objects.filter(
                user=login.user, type__in=[Authenticator.Type.TOTP, Authenticator.Type.WEBAUTHN]).exists()):
            return False
        return super().is_login_by_code_required(login)

    def set_password(self, user, password):
        # El runtime solo puede actualizar columnas concretas: allauth haría save() completo.
        user.set_password(password)
        user.save(update_fields=["password"])

    def send_notification_mail(self, *args, **kwargs):
        # El aviso llega después de guardar: su fallo no debe presentarse como error de guardado.
        try:
            super().send_notification_mail(*args, **kwargs)
        except MailUnavailable:
            logger.warning("notificacion-no-enviada")


class AdaptadorMFA(DefaultMFAAdapter):
    # allauth guarda el secreto TOTP y la semilla de recuperación en texto claro por defecto.
    def encrypt(self, text):
        return Fernet(settings.CHILITO_MFA_KEY).encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        return Fernet(settings.CHILITO_MFA_KEY).decrypt(encrypted_text.encode()).decode()
