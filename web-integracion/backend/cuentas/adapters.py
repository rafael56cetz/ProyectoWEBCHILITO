from allauth.account.adapter import DefaultAccountAdapter

class ClosedRegistrationAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        from cuentas.registration import local_registration_allowed
        return local_registration_allowed(request)


    def clean_password(self, password, user=None):
        from django.core.exceptions import ValidationError
        if len(password) > 256:
            raise ValidationError("Usa como máximo 256 caracteres.", code="password_too_long")
        return super().clean_password(password, user=user)
