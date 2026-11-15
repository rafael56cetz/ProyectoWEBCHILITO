"""Transporte del navegador sobre Django/allauth y los servicios de datos.

No implementa algoritmos de contraseña ni de token; no se registran cuerpos de petición."""
import base64
import logging
from datetime import datetime, timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, RequestDataTooBig
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from allauth.account.internal.flows.email_verification_by_code import EmailVerificationProcess
from allauth.headless.constants import Client
from allauth.headless.account import views as auth
from allauth.headless.mfa import views as mfa
from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.mfa.totp.internal.auth import SECRET_SESSION_KEY
from cuentas.email import MailUnavailable, delivery_available, delivery_problem
from cuentas.inputs import PASSWORD_INPUTS
from cuentas.registration import local_registration_allowed
from datos import services
from web.respuestas import error, leer_json, respuesta_de_base


logger = logging.getLogger(__name__)


def csrf_failure(request, reason=''):
    return error(403, 'csrf-failed')


@never_cache
@ensure_csrf_cookie
@require_GET
def bootstrap(request):
    return JsonResponse({
        'registrationAllowed': local_registration_allowed(request),
        'supportContact': settings.CHILITO_CONTACTO_SOPORTE,
        'legal': {'termsVersion': None, 'privacyVersion': None, 'approved': False},
        'password': {'minLength': 15, 'maxLength': 256,
                     'requirements': ['Usa al menos 15 caracteres.',
                                      'Evita contraseñas comunes, solo números o similares a tu correo.']},
        'code': {'length': 6, 'pattern': '^[0-9]{6}$', 'inputMode': 'numeric',
                 'expiresAfterSeconds': 600, 'resendAfterSeconds': 60,
                 'maxAttempts': 3, 'maxResends': 5},
    })


@never_cache
@require_GET
def profile(request):
    if not request.user.is_authenticated:
        return error(401, 'unauthenticated')
    try:
        contract = services.session_contract(request.user)
        assigned = services.has_garden(request.user)
        pendientes = services.aceptaciones_pendientes(request.user)
    except (PermissionDenied, ObjectDoesNotExist):
        return error(403, 'verification-required')
    except DatabaseError as fallo:
        logger.exception('perfil-no-disponible')
        return respuesta_de_base(fallo) or error(503, 'service-unavailable')
    return JsonResponse({**contract, 'status': 'ready', 'session': contract,
                         'email': contract['profile']['email'], 'verified': True,
                         'gardenAssigned': assigned, 'pendingLegal': pendientes})


_FIELDS = {
    auth.SignupView: {'email', 'password', 'termsAccepted', 'privacyRead'},
    auth.LoginView: {'email', 'password'},
    auth.SessionView: set(),
    auth.VerifyEmailView: {'key'},
    auth.ResendEmailVerificationCodeView: set(),
    auth.RequestPasswordResetView: {'email'},
    auth.ResetPasswordView: {'key', 'password'},
    auth.ChangePasswordView: {'current_password', 'new_password'},
    auth.ConfirmLoginCodeView: {'code'},
    auth.ReauthenticateView: {'password'},
    mfa.AuthenticateView: {'code'},
    mfa.ReauthenticateView: {'code'},
    mfa.AuthenticatorsView: set(),
    mfa.ManageTOTPView: {'code'},
    mfa.ManageRecoveryCodesView: set(),
    mfa.ManageWebAuthnView: {'name', 'credential', 'id', 'authenticators'},
    mfa.AuthenticateWebAuthnView: {'credential'},
    mfa.ReauthenticateWebAuthnView: {'credential'},
}
# Únicos campos que no son texto. allauth valida su contenido.
_NO_TEXTO = {'termsAccepted': bool, 'privacyRead': bool, 'credential': dict, 'id': int, 'authenticators': list}
_CASILLAS = {'termsAccepted', 'privacyRead'}


def _payload(request, allowed):
    data = leer_json(request, allowed, vacio=not allowed or request.method == 'DELETE')
    for name, value in data.items():
        if name in _NO_TEXTO:
            if not isinstance(value, _NO_TEXTO[name]) or (name in _CASILLAS and value is not True):
                raise ValueError
        elif not isinstance(value, str):
            raise ValueError
        elif len(value) > (256 if 'password' in name else 320):
            raise ValueError
    return data


def browser_endpoint(view_class, methods, *, reset_mail=False, verified_only=False):
    options = {'client': Client.BROWSER}
    input_class = getattr(view_class, 'input_class', None)
    if isinstance(input_class, dict):
        options['input_class'] = {method: PASSWORD_INPUTS.get(value, value) for method, value in input_class.items()}
    elif isinstance(input_class, type) and input_class in PASSWORD_INPUTS:
        options['input_class'] = PASSWORD_INPUTS[input_class]
    library_view = view_class.as_api_view(**options)

    @never_cache
    @csrf_protect
    @require_http_methods(methods)
    def view(request, *args, **kwargs):
        if request.method not in ('GET', 'HEAD'):
            try:
                data = _payload(request, _FIELDS[view_class])
            except RequestDataTooBig:
                return error(413, 'request-too-large')
            except (ValueError, UnicodeError, RecursionError):
                return error(400, 'invalid-input')
        else:
            data = {}
        if verified_only:
            if not request.user.is_authenticated:
                return error(401, 'unauthenticated')
            try:
                services.identity(request.user)
            except PermissionDenied:
                return error(403, 'verification-required')
        if reset_mail and not delivery_available(data.get('email')):
            return error(503, 'mail-unavailable')
        try:
            return library_view(request, *args, **kwargs)
        except MailUnavailable:
            return error(503, 'mail-unavailable')
        except (KeyError, TypeError, ValueError, AttributeError) as fallo:
            # fido2 no valida la forma de la credencial antes de leerla.
            if 'credential' not in _FIELDS[view_class]:
                raise fallo
            return error(400, 'invalid-input')
        except DatabaseError as fallo:
            logger.exception('acceso-no-disponible')
            return respuesta_de_base(fallo) or error(503, 'service-unavailable')
    return view


@never_cache
@csrf_protect
@require_POST
def registration(request):
    if not local_registration_allowed(request):
        return error(403, 'registration-disabled')
    try:
        data = _payload(request, _FIELDS[auth.SignupView])
    except RequestDataTooBig:
        return error(413, 'request-too-large')
    except (ValueError, UnicodeError, RecursionError):
        return error(400, 'invalid-input')
    if data.get('termsAccepted') is not True:
        return error(400, 'terms-required')
    if data.get('privacyRead') is not True:
        return error(400, 'privacy-required')
    # Invalid email/type/password are checked by the installed allauth input; the
    # preflight depends on delivery configuration, never whether the account exists.
    if delivery_problem(data.get('email')):
        return error(503, 'mail-unavailable')
    return browser_endpoint(auth.SignupView, ['POST'])(request)


@never_cache
@require_GET
def verification_context(request):
    try:
        process = EmailVerificationProcess.resume(request)
        if not process:
            return error(409, 'verification-expired')
        expires = process.state['at'] + settings.ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT
        return JsonResponse({'status': 'verification-required', 'email': process.email,
                             'expiresAt': datetime.fromtimestamp(expires, timezone.utc).isoformat()})
    except DatabaseError as fallo:
        return respuesta_de_base(fallo) or error(503, 'service-unavailable')


@never_cache
@require_GET
def totp_qr(request):
    """QR del secreto pendiente en la sesión. Nunca recibe el secreto del cliente."""
    if not request.user.is_authenticated:
        return error(401, 'unauthenticated')
    secret = request.session.get(SECRET_SESSION_KEY)
    if not secret:
        return error(409, 'no-pending-setup')
    adapter = get_mfa_adapter()
    svg = adapter.build_totp_svg(adapter.build_totp_url(request.user, secret))
    return JsonResponse({'status': 'ready', 'image': 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()})
