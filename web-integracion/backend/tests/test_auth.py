"""Integration-stage HTTP tests. PostgreSQL and in-memory mail only; no SMTP sends."""
import json
import re
import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from django.db import transaction
from django.test import Client, TestCase, override_settings
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification_by_code import EMAIL_VERIFICATION_CODE_SESSION_KEY as CODE_KEY
from cuentas.models import ConfirmacionRegistroLocal
from cuentas.email import AuthorizedSMTPBackend, MailUnavailable
from datos import services
from datos.models import Dispositivo, SesionTecnica, PermisoSoporte
from huerto.models import Huerto, Membresia

P = '/_allauth/browser/v1/'
PASSWORD = 'Frase aislada para comprobar cuentas extensas 73!'
NEW_PASSWORD = 'Nueva frase aislada para comprobar el cambio 81!'


@override_settings(ELCHILITO_REGISTRATION_ENABLED=True,
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthenticationHTTPTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST='127.0.0.1')
        self.client.get('/api/acceso/configuracion')

    def post(self, path, data=None, client=None, method='post'):
        c = client or self.client
        cookie = c.cookies.get('csrftoken')
        return getattr(c, method)(P + path, {} if data is None else data,
                                 content_type='application/json',
                                 HTTP_X_CSRFTOKEN=cookie.value if cookie else '')

    def make_user(self, email='auth-user@example.test', verified=True, **fields):
        user = get_user_model().objects.create_user(email, PASSWORD, **fields)
        EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=verified)
        return user

    def login(self, user=None, client=None):
        user = user or self.make_user()
        return self.post('auth/login', {'email': user.email, 'password': PASSWORD}, client=client)

    def signup(self, **kwargs):
        return self.post('auth/signup', {'email': 'new-auth@example.test', 'password': PASSWORD,
                                        'termsAccepted': True, **kwargs})

    def code(self):
        return self.client.session[CODE_KEY]['code']

    def reset_key(self, user):
        response = self.post('auth/password/request', {'email': user.email})
        self.assertEqual(response.status_code, 200)
        match = re.search(r'(?:token|key)=([^\s]+)', mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match[1]

    def test_bootstrap_policy_and_no_store(self):
        response = self.client.get('/api/acceso/configuracion')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['registrationAllowed'])
        self.assertEqual(body['password']['minLength'], 15)
        self.assertEqual(body['password']['maxLength'], 256)
        self.assertEqual(body['code']['maxAttempts'], 3)
        self.assertEqual(body['code']['maxResends'], 5)
        self.assertFalse(body['legal']['approved'])
        self.assertTrue(response.cookies['csrftoken'].value)
        self.assertIn('no-store', response['Cache-Control'])

    def test_csrf_required_for_all_auth_mutations_and_foreign_origin(self):
        c = Client(enforce_csrf_checks=True, HTTP_HOST='127.0.0.1')
        for path, method in [('auth/login', 'post'), ('auth/signup', 'post'),
                             ('auth/email/verify', 'post'), ('auth/email/verify/resend', 'post'),
                             ('auth/password/request', 'post'), ('auth/password/reset', 'post'),
                             ('account/password/change', 'post'), ('auth/session', 'delete')]:
            with self.subTest(path=path):
                response = getattr(c, method)(P + path, {}, content_type='application/json')
                self.assertEqual(response.status_code, 403)
        foreign = self.client.post(P + 'auth/signup', {}, content_type='application/json',
                                  HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value,
                                  HTTP_ORIGIN='https://foreign.example.test')
        self.assertEqual(foreign.status_code, 403)
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_signup_verification_and_no_automatic_membership(self):
        exact = ' ' + '\U0001f680' * 13 + ' '
        response = self.signup(password=exact)
        self.assertEqual(response.status_code, 401)
        user = get_user_model().objects.get()
        self.assertTrue(user.check_password(exact))
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertTrue(ConfirmacionRegistroLocal.objects.get(usuario=user).documentos_pendientes)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(self.code(), response.content.decode())
        self.assertEqual(self.post('auth/email/verify', {'key': self.code()}).status_code, 200)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        profile = self.client.get('/api/cuenta').json()
        self.assertFalse(profile['gardenAssigned'])
        self.assertEqual(profile['role'], 'user')
        self.assertEqual(profile['capabilities'], [])
        self.assertEqual(profile['profile']['id'], str(user.pk))
        self.assertFalse(Membresia.objects.exists())
        self.assertNotEqual(self.client.get('/api/huertos/actual').status_code, 200)

    def test_invalid_password_policy_and_maximum_256(self):
        for password in ['x' * 14, '\U0001f680' * 257, '123456789012345', 'password']:
            with self.subTest(length=len(password)):
                self.assertEqual(self.signup(password=password).status_code, 400)
        self.assertFalse(get_user_model().objects.exists())
        maximum = 'Aq!7' * 64
        self.assertEqual(len(maximum), 256)
        self.assertEqual(self.signup(password=maximum).status_code, 401)
        self.assertTrue(get_user_model().objects.get().check_password(maximum))

    def test_similarity_uses_signup_email(self):
        self.assertEqual(self.signup(email='sustratoyhabanerofamiliar@example.test',
                                     password='sustratoyhabanerofamiliar').status_code, 400)
        self.assertFalse(get_user_model().objects.exists())

    def test_signup_rejects_protected_extra_fields_and_non_boolean_checkbox(self):
        for changes in [{'is_staff': True}, {'is_superuser': True}, {'role': 'admin'},
                        {'actor': '123'}, {'termsAccepted': 'true'}, {'termsAccepted': 1},
                        {'termsAccepted': False}, {'approved': True}]:
            with self.subTest(changes=list(changes)):
                self.assertEqual(self.signup(**changes).status_code, 400)
        self.assertFalse(get_user_model().objects.exists())

    def test_strict_json_rejects_duplicate_keys_arrays_and_wrong_content_type(self):
        for body in ['[]', '{"email":"one@example.test","email":"two@example.test"}', '{']:
            r = self.client.post(P + 'auth/signup', body, content_type='application/json',
                                 HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value)
            self.assertEqual(r.status_code, 400)
        r = self.client.post(P + 'auth/login', {'email': 'one@example.test', 'password': PASSWORD},
                             HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value)
        self.assertEqual(r.status_code, 400)

    def test_three_incorrect_codes_abort_process(self):
        self.assertEqual(self.signup().status_code, 401)
        wrong = str((int(self.code()) + 1) % 1000000).zfill(6)
        for _ in range(3):
            self.assertEqual(self.post('auth/email/verify', {'key': wrong}).status_code, 400)
        self.assertEqual(self.client.get('/api/acceso/verificacion').status_code, 409)
        self.assertFalse(EmailAddress.objects.get().verified)

    def test_expired_verification_and_reuse_rejected(self):
        self.signup()
        code = self.code()
        session = self.client.session
        state = session[CODE_KEY]
        state['at'] = time.time() - 601
        session[CODE_KEY] = state
        session.save()
        self.assertEqual(self.post('auth/email/verify', {'key': code}).status_code, 409)
        self.assertFalse(EmailAddress.objects.get().verified)

    def test_successful_code_cannot_be_reused(self):
        self.signup()
        code = self.code()
        self.assertEqual(self.post('auth/email/verify', {'key': code}).status_code, 200)
        self.assertEqual(self.post('auth/email/verify', {'key': code}).status_code, 409)

    def test_resend_wait_window_quota_and_initial_deadline(self):
        self.signup()
        original = self.client.session[CODE_KEY].copy()
        self.assertEqual(self.post('auth/email/verify/resend', {}).status_code, 429)
        for index in range(5):
            cache.clear()  # Test-only clock/rate isolation; never exposed by the app.
            new_code = str((int(original['code']) + index + 1) % 1000000).zfill(6)
            with patch('allauth.account.adapter.DefaultAccountAdapter.generate_email_verification_code', return_value=new_code):
                self.assertEqual(self.post('auth/email/verify/resend', {}).status_code, 200)
            current = self.client.session[CODE_KEY]
            self.assertEqual(current['at'], original['at'])
            self.assertEqual(current['resend_count'], index + 1)
        cache.clear()
        self.assertEqual(self.post('auth/email/verify/resend', {}).status_code, 409)
        self.assertEqual(len(mail.outbox), 6)
        self.assertEqual(self.post('auth/email/verify', {'key': original['code']}).status_code, 400)

    def test_login_restore_logout_and_session_invalidation(self):
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get(P + 'auth/session').status_code, 200)
        self.assertEqual(self.client.get('/api/cuenta').status_code, 200)
        old_key = self.client.cookies['sessionid'].value
        self.assertEqual(self.post('auth/session', {}, method='delete').status_code, 401)
        self.assertEqual(self.client.get('/api/cuenta').status_code, 401)
        restored = Client(HTTP_HOST='127.0.0.1')
        restored.cookies['sessionid'] = old_key
        self.assertEqual(restored.get('/api/cuenta').status_code, 401)

    def test_session_eight_hour_policy_and_expired_row_rejected_by_server(self):
        from datetime import timedelta
        from django.conf import settings
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        self.assertEqual(settings.SESSION_COOKIE_AGE, 8 * 60 * 60)
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
        self.assertEqual(self.login().status_code, 200)
        session = self.client.session
        self.assertTrue(session.get_expire_at_browser_close())
        self.assertLessEqual(abs(session.get_expiry_age() - 28800), 2)
        key = self.client.cookies['sessionid'].value
        Session.objects.filter(session_key=key).update(expire_date=timezone.now() - timedelta(seconds=1))
        # Keeping the original cookie does not rescue an expired server-side row.
        self.assertEqual(self.client.get('/api/cuenta').status_code, 401)

    def test_invalid_login_is_neutral_for_existing_and_unknown_email(self):
        user = self.make_user()
        known = self.post('auth/login', {'email': user.email, 'password': 'incorrecta'})
        unknown = self.post('auth/login', {'email': 'unknown-auth@example.test', 'password': 'incorrecta'})
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.status_code, 400)
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(self.client.get('/api/cuenta').status_code, 401)

    def test_superuser_flags_do_not_grant_web_capabilities(self):
        user = self.make_user(is_staff=True, is_superuser=True)
        self.login(user)
        profile = self.client.get('/api/cuenta').json()
        self.assertEqual(profile['role'], 'user')
        permission = Permission.objects.get(content_type__app_label='datos', codename='ver_flota')
        user.user_permissions.add(permission)
        profile = self.client.get('/api/cuenta').json()
        self.assertEqual(profile['role'], 'admin')
        self.assertEqual(profile['capabilities'], ['ver_flota'])

    def test_unverified_login_requires_code_and_inactive_login_rejected(self):
        user = self.make_user(verified=False)
        self.assertEqual(self.login(user).status_code, 401)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.client.get('/api/cuenta').status_code, 401)
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertNotEqual(self.login(user).status_code, 200)

    def test_recovery_neutral_unknown_and_new_request_does_not_revoke_previous_link(self):
        user = self.make_user()
        first = self.reset_key(user)
        cache.clear()
        self.reset_key(user)
        self.assertEqual(self.client.get(P + 'auth/password/reset', HTTP_X_PASSWORD_RESET_KEY=first).status_code, 200)
        cache.clear()
        known = self.post('auth/password/request', {'email': user.email})
        cache.clear()
        unknown = self.post('auth/password/request', {'email': 'unknown@example.test'})
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.status_code, 200)

    def test_recovery_reset_expiry_invalidation_and_no_automatic_login(self):
        user = self.make_user()
        key = self.reset_key(user)
        reset = self.post('auth/password/reset', {'key': key, 'password': NEW_PASSWORD})
        # allauth returns the unauthenticated state after a successful reset;
        # HTTP 401 here does not mean the password mutation failed.
        self.assertEqual(reset.status_code, 401)
        self.assertFalse(reset.json()['meta']['is_authenticated'])
        user.refresh_from_db()
        self.assertTrue(user.check_password(NEW_PASSWORD))
        self.assertEqual(self.client.get('/api/cuenta').status_code, 401)
        self.assertEqual(self.client.get(P + 'auth/password/reset', HTTP_X_PASSWORD_RESET_KEY=key).status_code, 400)
        cache.clear()
        expired = self.reset_key(user)
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            self.assertEqual(self.client.get(P + 'auth/password/reset', HTTP_X_PASSWORD_RESET_KEY=expired).status_code, 400)

    def test_change_password_checks_current_and_invalidates_other_session(self):
        user = self.make_user()
        self.login(user)
        other = Client(HTTP_HOST='127.0.0.1')
        other.cookies = self.client.cookies.copy()
        self.assertEqual(self.post('account/password/change', {'current_password': 'incorrecta', 'new_password': NEW_PASSWORD}).status_code, 400)
        self.assertEqual(self.post('account/password/change', {'current_password': PASSWORD, 'new_password': 'short'}).status_code, 400)
        self.assertEqual(self.post('account/password/change', {'current_password': PASSWORD, 'new_password': NEW_PASSWORD}).status_code, 200)
        self.assertEqual(self.client.get('/api/cuenta').status_code, 200)
        self.assertEqual(other.get('/api/cuenta').status_code, 401)

    def test_failed_login_and_signup_server_limits(self):
        user = self.make_user()
        results = [self.post('auth/login', {'email': user.email, 'password': 'incorrecta'}) for _ in range(7)]
        self.assertTrue(any(r.status_code == 429 or any(e.get('code') == 'too_many_login_attempts' for e in r.json().get('errors', [])) for r in results))
        cache.clear()
        with override_settings(ACCOUNT_RATE_LIMITS={'signup': '2/m/ip'}):
            self.assertEqual(self.signup(email='first@example.test').status_code, 401)
            self.assertEqual(self.signup(email='second@example.test').status_code, 401)
            self.assertEqual(self.signup(email='third@example.test').status_code, 429)

    def test_closed_registration_and_unavailable_email_never_claim_success(self):
        with override_settings(ELCHILITO_REGISTRATION_ENABLED=False):
            self.assertEqual(self.signup().status_code, 403)
        with patch('cuentas.api.delivery_problem', return_value='mail-unavailable'):
            self.assertEqual(self.signup().status_code, 503)
        self.assertFalse(get_user_model().objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_logout_closes_technical_session_without_revoking_permission(self):
        owner = self.make_user()
        admin = self.make_user('auth-admin@example.test')
        admin.user_permissions.add(Permission.objects.get(content_type__app_label='datos', codename='atender_soporte'))
        garden = Huerto.objects.create(clave='auth-garden', nombre='Huerto sintético')
        Membresia.objects.create(usuario=owner, huerto=garden)
        Dispositivo.objects.create(huerto=garden, identificador='auth-device')
        issued = services.issue_support(owner, garden.pk, 'connection', True)
        technical = services.open_technical(admin, issued['permission']['ticket'], issued['permission']['token'])
        self.login(admin)
        self.assertEqual(self.post('auth/session', {}, method='delete').status_code, 401)
        technical.refresh_from_db()
        self.assertIsNotNone(technical.cerrada_en)
        self.assertEqual(technical.motivo_cierre, 'logout')
        self.assertIsNone(PermisoSoporte.objects.get(pk=technical.permiso_id).revocado_en)

    def test_logout_cleans_up_after_admin_loses_verification_or_activity(self):
        # Both variants use the original server-session cookie and body {} only.
        # An arbitrary anonymous payload never supplies the cleanup identity.
        owner = self.make_user()
        garden = Huerto.objects.create(clave='logout-ineligible', nombre='Huerto sintético')
        Membresia.objects.create(usuario=owner, huerto=garden)
        Dispositivo.objects.create(huerto=garden, identificador='logout-ineligible-device')
        admin = self.make_user('logout-ineligible@example.test')
        admin.user_permissions.add(Permission.objects.get(content_type__app_label='datos', codename='atender_soporte'))
        issued = services.issue_support(owner, garden.pk, 'connection', True)
        for loss in ['verification', 'activity']:
            with self.subTest(loss=loss):
                cache.clear()
                self.assertEqual(self.login(admin).status_code, 200)
                technical = services.open_technical(admin, issued['permission']['ticket'], issued['permission']['token'])
                if loss == 'verification':
                    EmailAddress.objects.filter(user=admin).update(verified=False)
                else:
                    get_user_model().objects.filter(pk=admin.pk).update(is_active=False)
                self.assertEqual(self.post('auth/session', {}, method='delete').status_code, 401)
                technical.refresh_from_db()
                self.assertIsNotNone(technical.cerrada_en)
                self.assertEqual(technical.motivo_cierre, 'logout')
                self.assertIsNone(PermisoSoporte.objects.get(pk=technical.permiso_id).revocado_en)
                from datos.models import Auditoria
                self.assertTrue(Auditoria.objects.filter(sesion_tecnica=technical, accion='technical-closed').exists())
                EmailAddress.objects.filter(user=admin).update(verified=True)
                get_user_model().objects.filter(pk=admin.pk).update(is_active=True)
                self.assertEqual(self.login(admin).status_code, 200)
                from django.core.exceptions import PermissionDenied
                with self.assertRaises(PermissionDenied):
                    services.technical_action(admin, technical.pk, 'diagnostic')
                self.post('auth/session', {}, method='delete')

    def test_deep_json_and_oversize_auth_body_are_controlled(self):
        nested = '{"email":' + '[' * 1500 + '0' + ']' * 1500 + '}'
        response = self.client.post(P + 'auth/login', nested, content_type='application/json',
                                    HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'invalid-input')
        with override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=512):
            response = self.client.post(P + 'auth/signup', '{"email":"' + 'a' * 1000 + '"}',
                                        content_type='application/json',
                                        HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value)
            self.assertEqual(response.status_code, 413)
            self.assertEqual(response.json()['code'], 'request-too-large')

    def test_smtp_is_opt_in_and_never_connects_without_authorization(self):
        from django.core.mail import EmailMessage
        with override_settings(ELCHILITO_SMTP_ENABLED=False), patch('cuentas.email.SMTPBackend') as smtp:
            with self.assertRaises(MailUnavailable):
                AuthorizedSMTPBackend().send_messages([EmailMessage('Prueba', 'Prueba', to=['unapproved@example.test'])])
            smtp.assert_not_called()
