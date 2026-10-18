"""A narrow browser-only surface around allauth. No credential algorithms here."""
import json
from datetime import datetime, timezone
from django.conf import settings
from allauth.account.internal.flows.email_verification_by_code import EmailVerificationProcess
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from allauth.account.models import EmailAddress
from allauth.headless.constants import Client
from huerto.services import visible_gardens
from cuentas.email import MailUnavailable, delivery_available, delivery_problem
from cuentas.inputs import PASSWORD_INPUTS
from cuentas.registration import local_registration_allowed
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DatabaseError
from allauth.headless.account import views as auth

def error(status, code):
    return JsonResponse({"status": status, "code": code}, status=status)

def csrf_failure(request, reason=""):
    return error(403, "csrf-failed")

@never_cache
@ensure_csrf_cookie
@require_GET
def bootstrap(request):
    return JsonResponse({
        "registrationAllowed": local_registration_allowed(request),
        "legal": {"termsVersion": None, "privacyVersion": None, "approved": False},
        "password": {"minLength": 15, "maxLength": 256,
                     "requirements": ["Usa al menos 15 caracteres.", "Evita contraseñas comunes, solo números o similares a tu correo."]},
        "code": {"length": 6, "pattern": "^[0-9]{6}$", "inputMode": "numeric",
                 "expiresAfterSeconds": 600, "resendAfterSeconds": 60}
    })

@never_cache
@require_GET
def profile(request):
    if not request.user.is_authenticated or not request.user.is_active:
        return error(401, "unauthenticated")
    verified = EmailAddress.objects.filter(user=request.user, email__iexact=request.user.email, verified=True).exists()
    if not verified:
        return error(403, "verification-required")
    return JsonResponse({"status": "ready", "email": request.user.email, "verified": True,
                         "gardenAssigned": visible_gardens(request.user).filter(clave="principal").exists()})

@never_cache
@require_POST
def registration(request):
    if not local_registration_allowed(request):
        return error(403, "registration-disabled")
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return error(400, "invalid-input")
        if data.get("termsAccepted") is not True:
            return error(400, "terms-required")
        email = data.get("email")
        if not isinstance(email, str) or not isinstance(data.get("password"), str):
            return error(400, "invalid-input")
        validate_email(email.strip())
    except (ValueError, UnicodeError, ValidationError):
        return error(400, "invalid-input")
    problem = delivery_problem(email)
    if problem:
        # Local recipient authorization is independent of whether an account exists.
        return error(403 if problem == "email-not-authorized" else 503, problem)
    # Library owns account creation, enumeration, limits, code and session.
    # SMTP failure can leave an unverified account; login can retry delivery.
    try:
        return browser_endpoint(auth.SignupView, ["POST"])(request)
    except DatabaseError:
        return error(503, "service-unavailable")

def browser_endpoint(view_class, methods, *, reset_mail=False, verified_only=False):
    options = {"client": Client.BROWSER}
    input_class = getattr(view_class, "input_class", None)
    if isinstance(input_class, dict):
        options["input_class"] = {method: PASSWORD_INPUTS.get(value, value) for method, value in input_class.items()}
    elif isinstance(input_class, type) and input_class in PASSWORD_INPUTS:
        options["input_class"] = PASSWORD_INPUTS[input_class]
    library_view = view_class.as_api_view(**options)
    @never_cache
    @require_http_methods(methods)
    @wraps(library_view)
    def view(request, *args, **kwargs):
        if verified_only:
            if not request.user.is_authenticated:
                return error(401, "unauthenticated")
            if not EmailAddress.objects.filter(user=request.user, email__iexact=request.user.email, verified=True).exists():
                return error(403, "verification-required")
        # Preflight is independent of account existence: missing delivery never reports success.
        if reset_mail:
            try:
                email = json.loads(request.body).get("email", "")
                if not isinstance(email, str):
                    return error(400, "invalid-input")
            except (ValueError, UnicodeError, AttributeError):
                return error(400, "invalid-input")
            if not delivery_available(email):
                return error(503, "mail-unavailable")
        try:
            response = library_view(request, *args, **kwargs)
        except MailUnavailable:
            return error(503, "mail-unavailable")
        return response
    return view

@never_cache
@require_GET
def verification_context(request):
    process = EmailVerificationProcess.resume(request)
    if not process:
        return error(409, "verification-expired")
    # Metadata only; GET never attempts a code or exposes it.
    expires = process.state["at"] + settings.ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT
    return JsonResponse({"status": "verification-required", "email": process.email,
                         "expiresAt": datetime.fromtimestamp(expires, timezone.utc).isoformat()})
