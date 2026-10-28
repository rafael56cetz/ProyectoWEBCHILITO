"""Small browser-only transport around Django/allauth and trusted data services.
No password/token algorithm is implemented here. No request bodies are logged.
"""
import json
from datetime import datetime, timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, RequestDataTooBig
from django.db import DatabaseError, transaction
from django.contrib.auth import get_user_model, SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.utils import timezone as django_timezone
from django.utils.crypto import constant_time_compare
from django.http import JsonResponse
from django.http.request import RawPostDataException
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification_by_code import EmailVerificationProcess
from allauth.headless.constants import Client
from allauth.headless.account import views as auth
from cuentas.email import MailUnavailable, delivery_available, delivery_problem
from cuentas.inputs import PASSWORD_INPUTS
from cuentas.registration import local_registration_allowed
from datos import services
from datos.models import SesionTecnica, PermisoSoporte
from huerto.models import Membresia


def error(status, code):
    return JsonResponse({'status': status, 'code': code}, status=status)


def csrf_failure(request, reason=''):
    return error(403, 'csrf-failed')


@never_cache
@ensure_csrf_cookie
@require_GET
def bootstrap(request):
    return JsonResponse({
        'registrationAllowed': local_registration_allowed(request),
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
        assigned = Membresia.objects.filter(usuario=request.user, activa=True).exists()
    except (PermissionDenied, ObjectDoesNotExist):
        return error(403, 'verification-required')
    except DatabaseError:
        return error(503, 'service-unavailable')
    return JsonResponse({**contract, 'status': 'ready', 'session': contract,
                         'email': contract['profile']['email'], 'verified': True,
                         'gardenAssigned': assigned})


_FIELDS = {
    auth.SignupView: {'email', 'password', 'termsAccepted'},
    auth.LoginView: {'email', 'password'},
    auth.SessionView: set(),
    auth.VerifyEmailView: {'key'},
    auth.ResendEmailVerificationCodeView: set(),
    auth.RequestPasswordResetView: {'email'},
    auth.ResetPasswordView: {'key', 'password'},
    auth.ChangePasswordView: {'current_password', 'new_password'},
}


def _payload(request, allowed):
    # CSRF may have consumed a form body before this view runs. Reject its
    # media type before accessing request.body, preserving a controlled response.
    if request.content_type != 'application/json':
        if not allowed and request.META.get('CONTENT_LENGTH', '') in ('', '0'):
            return {}
        raise ValueError
    try:
        raw = request.body
    except RawPostDataException:
        raise ValueError from None
    if not raw and not allowed:
        return {}
    # Reject repeated keys instead of accepting ambiguous requests.
    def pairs(items):
        data = {}
        for key, value in items:
            if key in data:
                raise ValueError
            data[key] = value
        return data
    data = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError
    for name, value in data.items():
        if name == 'termsAccepted':
            if value is not True:
                raise ValueError
        elif not isinstance(value, str):
            raise ValueError
        elif len(value) > (256 if 'password' in name else 320):
            raise ValueError
    return data


def _logout_actor(request):
    """Resolve only the existing trusted server session, never request JSON.

    Django returns AnonymousUser for a now-inactive account. Its old server
    session can still be identified for cleanup if the auth hash remains valid;
    that identity grants no business operation or technical access.
    """
    if request.user.is_authenticated:
        return request.user
    user_id = request.session.get(SESSION_KEY)
    backend = request.session.get(BACKEND_SESSION_KEY)
    session_hash = request.session.get(HASH_SESSION_KEY)
    if (not isinstance(user_id, str) or not user_id.isdecimal()
            or backend not in settings.AUTHENTICATION_BACKENDS
            or not isinstance(session_hash, str)):
        return None
    actor = get_user_model().objects.filter(pk=user_id).first()
    if actor and (constant_time_compare(session_hash, actor.get_session_auth_hash())
                  or any(constant_time_compare(session_hash, value)
                         for value in actor.get_session_auth_fallback_hash())):
        return actor
    return None


@transaction.atomic
def _close_sessions_for_logout(request):
    # Cleanup does not require continued eligibility. It can only irreversibly
    # close sessions of the existing server-session identity, never grant access,
    # change actor/resource or revoke the user's authorization.
    actor = _logout_actor(request)
    if actor is None:
        return
    sources = list(SesionTecnica.objects.filter(administrador=actor, cerrada_en__isnull=True)
                   .select_related('permiso__caso'))
    for source in sources:
        # Reuse the service's stable subject/case lock order, skipping only
        # eligibility for this destructive cleanup, as in close_technical.
        case, _ = services._case_lock(source.permiso.caso_id, actor, eligible=False)
        permission = PermisoSoporte.objects.select_for_update().get(pk=source.permiso_id)
        session = SesionTecnica.objects.select_for_update().get(pk=source.pk)
        if session.administrador_id != actor.pk:
            raise PermissionDenied
        if session.cerrada_en is None:
            session.cerrada_en = django_timezone.now()
            session.motivo_cierre = 'logout'
            session.save(update_fields=['cerrada_en', 'motivo_cierre'])
            services.audit(actor, 'technical-closed', caso=case, permiso=permission,
                           huerto=case.huerto, sesion_tecnica=session)


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
            if not request.user.is_active or not EmailAddress.objects.filter(user=request.user, email__iexact=request.user.email, verified=True).exists():
                return error(403, 'verification-required')
        if reset_mail and not delivery_available(data.get('email')):
            return error(503, 'mail-unavailable')
        try:
            if view_class is auth.SessionView and request.method == 'DELETE':
                _close_sessions_for_logout(request)
            return library_view(request, *args, **kwargs)
        except MailUnavailable:
            return error(503, 'mail-unavailable')
        except DatabaseError:
            return error(503, 'service-unavailable')
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
    except DatabaseError:
        return error(503, 'service-unavailable')
