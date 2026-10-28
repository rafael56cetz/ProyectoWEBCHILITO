"""Keep password text exact while retaining the installed allauth input validators."""
from django import forms
from allauth.headless.account.inputs import LoginInput, ResetPasswordInput, ChangePasswordInput, SignupInput

class ExactPasswordMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password", "current_password", "new_password"):
            if name in self.fields:
                self.fields[name].strip = False

class ExactLoginInput(ExactPasswordMixin, LoginInput):
    pass

class ExactResetPasswordInput(ExactPasswordMixin, ResetPasswordInput):
    pass

class ExactChangePasswordInput(ExactPasswordMixin, ChangePasswordInput):
    pass


class ExactLocalSignupInput(ExactPasswordMixin, SignupInput):
    termsAccepted = forms.BooleanField(required=True)

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
        if not local_registration_allowed(request) or self.cleaned_data.get("termsAccepted") is not True:
            raise PermissionDenied
        # Save the technical confirmation with the account, before attempting SMTP.
        with transaction.atomic():
            user = super().save(request)
            ConfirmacionRegistroLocal.objects.create(usuario=user)
        return user

PASSWORD_INPUTS = {
    SignupInput: ExactLocalSignupInput,
    LoginInput: ExactLoginInput,
    ResetPasswordInput: ExactResetPasswordInput,
    ChangePasswordInput: ExactChangePasswordInput,
}
