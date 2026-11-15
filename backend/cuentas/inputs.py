"""Conserva el texto exacto de las contraseñas y mantiene los validadores de entrada de allauth instalados."""
from django import forms
from allauth.headless.account.inputs import (ChangePasswordInput, LoginInput, RequestPasswordResetInput,
                                             ResetPasswordInput, SignupInput)
from cuentas.services import correo_para_acceso, correo_registrado

class ExactPasswordMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password", "current_password", "new_password"):
            if name in self.fields:
                self.fields[name].strip = False

class ExactLoginInput(ExactPasswordMixin, LoginInput):
    def clean_email(self):
        email = self.cleaned_data.get("email")
        return correo_para_acceso(email) if email else email

class ExactResetPasswordInput(ExactPasswordMixin, ResetPasswordInput):
    pass

class EquivalentEmailResetInput(RequestPasswordResetInput):
    def clean_email(self):
        email = self.cleaned_data["email"]
        self.cleaned_data["email"] = correo_para_acceso(email)
        return super().clean_email()

class ExactChangePasswordInput(ExactPasswordMixin, ChangePasswordInput):
    pass


class ExactLocalSignupInput(ExactPasswordMixin, SignupInput):
    termsAccepted = forms.BooleanField(required=True)
    privacyRead = forms.BooleanField(required=True)

    def validate_unique_email(self, value):
        # Conserva el correo escrito: el proceso de verificación lo devuelve al navegador,
        # y mostrar el registrado revelaría la cuenta. Toma la misma ruta neutral de allauth.
        value = super().validate_unique_email(value)
        if not self.account_already_exists and correo_registrado(value):
            self.account_already_exists = True
        return value

    def clean_password(self):
        # Preserve allauth/Django validators, adding the account context for similarity.
        from django.contrib.auth import get_user_model
        from allauth.account.adapter import get_adapter
        user = get_user_model()(email=self.cleaned_data.get("email", ""))
        return get_adapter().clean_password(self.cleaned_data["password"], user=user)

    def save(self, request):
        from django.core.exceptions import PermissionDenied
        from django.db import transaction
        from cuentas.models import ConfirmacionRegistroLocal
        from cuentas.registration import local_registration_allowed
        from privacidad.services import registrar_actos_de_registro
        casillas = (self.cleaned_data.get("termsAccepted"), self.cleaned_data.get("privacyRead"))
        if not local_registration_allowed(request) or casillas != (True, True):
            raise PermissionDenied
        # Save the technical confirmation with the account, before attempting SMTP.
        with transaction.atomic():
            user = super().save(request)
            ConfirmacionRegistroLocal.objects.create(usuario=user)
            registrar_actos_de_registro(user)
        return user

PASSWORD_INPUTS = {
    SignupInput: ExactLocalSignupInput,
    LoginInput: ExactLoginInput,
    RequestPasswordResetInput: EquivalentEmailResetInput,
    ResetPasswordInput: ExactResetPasswordInput,
    ChangePasswordInput: ExactChangePasswordInput,
}
