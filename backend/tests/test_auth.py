"""Integration-stage HTTP tests. PostgreSQL and in-memory mail only; no SMTP sends."""
import json
import re
import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.mfa.models import Authenticator
from allauth.account.internal.flows.email_verification_by_code import EMAIL_VERIFICATION_CODE_SESSION_KEY as CODE_KEY
from cuentas.email import AuthorizedSMTPBackend, MailUnavailable
from privacidad.models import Decision
from privacidad.services import documento_vigente
from tests import cuenta, publicar_textos

P = '/_allauth/browser/v1/'
PASSWORD = 'Frase aislada para comprobar cuentas extensas 73!'
NEW_PASSWORD = 'Nueva frase aislada para comprobar el cambio 81!'


@override_settings(ELCHILITO_REGISTRATION_ENABLED=True,
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthenticationHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

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
        return cuenta(email, password=PASSWORD, verificada=verified, **fields)

    def login(self, user=None, client=None):
        user = user or self.make_user()
        mail.outbox.clear()
        response = self.post('auth/login', {'email': user.email, 'password': PASSWORD}, client=client)
        pendientes = [f['id'] for f in response.json().get('data', {}).get('flows', []) if f.get('is_pending')]
        if pendientes != ['login_by_code'] or not mail.outbox:
            return response
        codigo = re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)
        return self.post('auth/code/confirm', {'code': codigo}, client=client)

    def signup(self, **kwargs):
        return self.post('auth/signup', {'email': 'new-auth@example.test', 'password': PASSWORD,
                                        'termsAccepted': True, 'privacyRead': True, **kwargs})

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

    def test_signup_verification_and_no_privileges(self):
        exact = ' ' + '\U0001f680' * 13 + ' '
        response = self.signup(password=exact)
        self.assertEqual(response.status_code, 401)
        user = get_user_model().objects.get()
        self.assertTrue(user.check_password(exact))
        self.assertFalse(user.is_staff or user.is_superuser)
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
        self.assertEqual(profile['pendingLegal'], [])

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
                        {'termsAccepted': False}, {'privacyRead': False}, {'privacyRead': 'true'},
                        {'approved': True}]:
            with self.subTest(changes=list(changes)):
                self.assertEqual(self.signup(**changes).status_code, 400)
        self.assertFalse(get_user_model().objects.exists())

    def test_signup_saves_each_legal_act_with_its_current_version(self):
        self.assertIn(self.signup().status_code, (200, 401))
        user = get_user_model().objects.get()
        actos = {d.acto: d for d in Decision.objects.filter(sujeto__usuario=user, sujeto__ambito='cuenta')}
        self.assertEqual(set(actos), {'aceptacion_terminos', 'lectura_aviso'})
        self.assertTrue(all(d.decision is True for d in actos.values()))
        self.assertEqual(actos['aceptacion_terminos'].documento, documento_vigente('terminos'))
        self.assertEqual(actos['lectura_aviso'].documento, documento_vigente('aviso_privacidad'))
        self.assertEqual({d.ip_recortada for d in actos.values()}, {'127.0.0.0'})
        self.assertEqual({d.usuario_id for d in actos.values()}, {user.pk})

    def test_signup_requires_reading_the_privacy_notice(self):
        r = self.client.post(P + 'auth/signup', json.dumps({'email': 'new-auth@example.test', 'password': PASSWORD,
                                                            'termsAccepted': True}),
                             content_type='application/json', HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value)
        self.assertEqual((r.status_code, r.json().get('code')), (400, 'privacy-required'))
        self.assertFalse(get_user_model().objects.exists())

    def test_strict_json_rejects_non_standard_numbers(self):
        for body in ['{"email":NaN}', '{"email":Infinity}', '{"email":-Infinity}', '{"email":1e999}']:
            with self.subTest(body=body):
                r = self.client.post(P + 'auth/signup', body, content_type='application/json',
                                     HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value)
                self.assertEqual(r.status_code, 400)
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

    def test_capabilities_come_only_from_explicit_grants(self):
        user = self.make_user()
        self.login(user)
        profile = self.client.get('/api/cuenta').json()
        self.assertEqual((profile['role'], profile['capabilities']), ('user', []))
        self.assertFalse(get_user_model()._meta.get_field('is_staff').default)
        user.user_permissions.add(Permission.objects.get(content_type__app_label='cuentas', codename='ver_flota'))
        profile = self.client.get('/api/cuenta').json()
        self.assertEqual((profile['role'], profile['capabilities']), ('admin', ['ver_flota']))

    def test_unverified_login_requires_code_and_inactive_login_rejected(self):
        user = self.make_user(verified=False)
        respuesta = self.post('auth/login', {'email': user.email, 'password': PASSWORD})
        self.assertEqual(respuesta.status_code, 401)
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
