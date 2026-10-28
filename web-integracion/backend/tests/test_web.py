"""HTTP checks for the integrated, same-origin application.

PostgreSQL and synthetic accounts only. These exercise endpoints, not browser UI,
SMTP, hardware or deployments. Database service regressions are a separate suite.
"""
import json
import re
import secrets
import uuid
from unittest import skipUnless
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from datos.models import (
    Auditoria, CasoSoporte, Dispositivo, Mantenimiento, PermisoSoporte,
    RevisionConocimiento, SesionTecnica, Solicitud, ValidacionVersion,
)
from huerto.models import Aviso, AvisoLeido, Huerto, Membresia


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL, not SQLite.')
@override_settings(CHILITO_SUPPORT_KEY=secrets.token_urlsafe(48))
class IntegratedWebHTTPTests(TestCase):
    """Positive paths and negative resource/identity/CSRF boundaries over HTTP."""

    def setUp(self):
        if 'sintetico' not in str(connection.settings_dict['NAME']):
            raise RuntimeError('HTTP tests require an explicitly synthetic database.')
        cache.clear()
        self.owner = self.user('web-owner@example.test')
        self.other = self.user('web-other@example.test')
        self.admin = self.user('web-admin@example.test')
        self.staff = self.user('web-staff@example.test', is_staff=True, is_superuser=True)
        self.unverified = self.user('web-unverified@example.test', verified=False)
        self.garden = Huerto.objects.create(clave='principal', nombre='Huerto HTTP sintético')
        self.other_garden = Huerto.objects.create(clave='http-other', nombre='Otro huerto HTTP')
        Membresia.objects.create(usuario=self.owner, huerto=self.garden)
        Membresia.objects.create(usuario=self.other, huerto=self.other_garden)
        Dispositivo.objects.create(huerto=self.garden, identificador='http-device-a')
        Dispositivo.objects.create(huerto=self.other_garden, identificador='http-device-b')
        self.notice = self.make_notice(self.garden, "Aviso O'Hara; SELECT <script>alert(1)</script>")
        self.foreign_notice = self.make_notice(self.other_garden, 'Aviso de otro recurso')
        self.grant(self.admin, 'ver_flota', 'atender_soporte', 'ver_gobernanza', 'gestionar_cambios')
        self.client = self.client_for(self.owner)

    def user(self, email, verified=True, **fields):
        user = get_user_model().objects.create_user(email, secrets.token_urlsafe(24), **fields)
        EmailAddress.objects.create(user=user, email=email, verified=verified, primary=True)
        return user

    def make_notice(self, garden, title):
        return Aviso.objects.create(
            huerto=garden, zona=garden.zona_set.get(numero=1), severidad='advertencia',
            titulo=title, descripcion='Contenido sintético <img src=x onerror=alert(1)>',
            recomendacion="No interpretar O'Hara como SQL.", creado_en=timezone.now(),
        )

    def grant(self, user, *codenames):
        perms = Permission.objects.filter(content_type__app_label='datos', codename__in=codenames)
        self.assertEqual(perms.count(), len(codenames))
        user.user_permissions.add(*perms)

    def client_for(self, user=None, csrf=False):
        client = Client(enforce_csrf_checks=csrf, HTTP_HOST='127.0.0.1')
        if user is not None:
            client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        if csrf:
            response = client.get('/api/acceso/configuracion')
            self.assertEqual(response.status_code, 200)
        return client

    def post(self, path, payload, *, client=None, key=None, csrf=True, **extra):
        client = client or self.client
        headers = {'HTTP_IDEMPOTENCY_KEY': str(key or uuid.uuid4()), **extra}
        if csrf and 'csrftoken' in client.cookies:
            headers['HTTP_X_CSRFTOKEN'] = client.cookies['csrftoken'].value
        return client.post(path, json.dumps(payload), content_type='application/json', **headers)

    def accepted(self, response):
        self.assertIn(response.status_code, [200, 201, 202])
        data = response.json()
        self.assertEqual(data['status'], 'accepted')
        return data

    def issue(self, client=None):
        response = self.post('/api/soporte', {'incident': 'connection', 'consent': True}, client=client)
        return self.accepted(response)['permission']

    def open_console(self, permission):
        client = self.client_for(self.admin)
        response = self.post('/api/admin/soporte/' + permission['ticket'] + '/abrir',
                             {'token': permission['token']}, client=client)
        return client, self.accepted(response)['session']['id']

    def test_private_and_admin_urls_require_authenticated_session(self):
        anonymous = self.client_for()
        for url in ['/api/cuenta', '/api/huertos/actual', '/api/huertos/actual/avisos',
                    '/api/huertos/actual/mantenimiento', '/api/huertos/actual/solicitudes',
                    '/api/soporte', '/api/admin/flota', '/api/admin/soporte',
                    '/api/admin/gobernanza', '/api/admin/cambios']:
            with self.subTest(url=url):
                response = anonymous.get(url)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response['Content-Type'].split(';')[0], 'application/json')
                self.assertNotIn('Traceback', response.content.decode())

    def test_session_profile_roles_are_server_derived_and_flags_are_not_capabilities(self):
        normal = self.client.get('/api/cuenta').json()
        self.assertEqual(normal['session']['role'], 'user')
        self.assertEqual(normal['session']['capabilities'], [])
        self.assertEqual(normal['session']['profile']['id'], str(self.owner.pk))
        self.assertTrue(normal['gardenAssigned'])
        for user, role in [(self.staff, 'user'), (self.admin, 'admin')]:
            response = self.client_for(user).get('/api/cuenta')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['session']['role'], role)

    def test_unverified_inactive_or_revoked_membership_is_not_authorized(self):
        unverified = self.client_for(self.unverified)
        self.assertEqual(unverified.get('/api/huertos/actual').status_code, 403)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertIn(self.client.get('/api/huertos/actual').status_code, [401, 403])
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=True)
        self.client = self.client_for(self.owner)
        Membresia.objects.filter(usuario=self.owner).update(activa=False)
        response = self.client.get('/api/huertos/actual')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'garden-unassigned')
        self.assertEqual(self.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'}).status_code, 403)
        self.assertFalse(Mantenimiento.objects.exists())

    def test_garden_projection_keeps_three_plants_crop_and_null_readings(self):
        response = self.client.get('/api/huertos/actual')
        self.assertEqual(response.status_code, 200)
        garden = response.json()['garden']
        self.assertEqual([p['id'] for p in garden['plants']], [1, 2, 3])
        for plant in garden['plants']:
            self.assertIsInstance(plant['zoneId'], str)
            self.assertEqual(plant['crop'], 'Chile habanero')
            self.assertIsNone(plant['reading']['value'])
            self.assertIsNone(plant['reading']['at'])
        self.assertIsNone(garden['temperature']['value'])
        self.assertEqual(garden['tank']['state'], 'unknown')

    def test_notices_preserve_text_as_json_and_translate_names(self):
        response = self.client.get('/api/huertos/actual/avisos')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'].split(';')[0], 'application/json')
        data = response.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['page'], 1)
        notice = data['items'][0]
        self.assertEqual(notice['id'], str(self.notice.pk))
        self.assertEqual(notice['title'], self.notice.titulo)
        self.assertEqual(notice['description'], self.notice.descripcion)
        self.assertEqual(notice['importance'], 'medium')
        self.assertEqual(notice['condition'], 'active')
        self.assertFalse(notice['read'])
        self.assertIsNone(notice['resolvedAt'])

    def test_notice_read_is_persistent_and_does_not_resolve_notice(self):
        response = self.post(f'/api/huertos/actual/avisos/{self.notice.pk}/lectura', {})
        self.accepted(response)
        self.assertEqual(AvisoLeido.objects.filter(usuario=self.owner, aviso=self.notice).count(), 1)
        self.notice.refresh_from_db()
        self.assertIsNone(self.notice.resuelto_en)
        self.client = self.client_for(self.owner)
        self.assertTrue(self.client.get('/api/huertos/actual/avisos').json()['items'][0]['read'])

    def test_foreign_notice_and_unknown_notice_have_neutral_denials(self):
        unknown = self.foreign_notice.pk + 100000
        for suffix, method in [('', 'get'), ('/lectura', 'post')]:
            responses = []
            for notice_id in [self.foreign_notice.pk, unknown]:
                url = f'/api/huertos/actual/avisos/{notice_id}' + suffix
                r = self.client.get(url) if method == 'get' else self.post(url, {})
                self.assertEqual(r.status_code, 403)
                responses.append(r.json())
            self.assertEqual(responses[0], responses[1])
        self.assertFalse(AvisoLeido.objects.filter(aviso=self.foreign_notice).exists())

    def test_maintenance_round_trip_and_pending_requests_survive_new_client(self):
        self.accepted(self.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'}))
        self.accepted(self.post('/api/huertos/actual/solicitudes', {'type': 'water'}))
        maintenance = Mantenimiento.objects.get()
        request = Solicitud.objects.get()
        self.assertEqual(maintenance.actor_id, self.owner.pk)
        self.assertEqual(maintenance.huerto_id, self.garden.pk)
        self.assertEqual(request.estado, 'pending')
        self.assertEqual(Auditoria.objects.filter(mantenimiento=maintenance).count(), 1)
        fresh = self.client_for(self.owner)
        for path in ['/api/huertos/actual/mantenimiento', '/api/huertos/actual/solicitudes']:
            response = fresh.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['total'], 1)
            self.assertEqual(len(response.json()['items']), 1)

    def test_business_posts_reject_missing_key_extra_fields_and_invalid_json_types(self):
        no_key = self.client.post('/api/huertos/actual/mantenimiento', json.dumps({'type': 'inspection'}), content_type='application/json')
        self.assertEqual(no_key.status_code, 400)
        bad_key = self.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'}, key='not-a-uuid')
        self.assertEqual(bad_key.status_code, 400)
        for payload in [[], None, {'type': []}, {'type': 'inspection', 'actor': str(self.other.pk)},
                        {'type': 'inspection', 'huerto_id': str(self.other_garden.pk)},
                        {'type': 'inspection', 'registeredAt': '2030-01-01T00:00:00Z'},
                        {'type': 'inspection', 'status': 'executed'}]:
            with self.subTest(payload_type=type(payload).__name__):
                self.assertEqual(self.post('/api/huertos/actual/mantenimiento', payload).status_code, 400)
        self.assertFalse(Mantenimiento.objects.exists())

    def test_write_requires_json_content_type(self):
        response = self.client.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'},
                                    HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertIn(response.status_code, [400, 415])
        self.assertFalse(Mantenimiento.objects.exists())

    def test_duplicate_key_replays_without_duplicate_write_and_changed_body_conflicts(self):
        key = uuid.uuid4()
        first = self.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'}, key=key)
        second = self.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'}, key=key)
        self.accepted(first)
        self.accepted(second)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(Mantenimiento.objects.count(), 1)
        self.assertEqual(Auditoria.objects.filter(accion='maintenance').count(), 1)
        changed = self.post('/api/huertos/actual/mantenimiento', {'type': 'refill'}, key=key)
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(Mantenimiento.objects.count(), 1)

    def test_csrf_cookie_and_header_are_required_for_business_mutations(self):
        strict = self.client_for(self.owner, csrf=True)
        before = Mantenimiento.objects.count()
        response = self.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'}, client=strict, csrf=False)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Mantenimiento.objects.count(), before)
        self.accepted(self.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'}, client=strict))
        self.assertEqual(Mantenimiento.objects.count(), before + 1)

    def test_get_cannot_trigger_write_operations(self):
        for path in [f'/api/huertos/actual/avisos/{self.notice.pk}/lectura',
                     '/api/admin/reinicio', '/api/admin/validaciones', '/api/admin/despliegues']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 405)
        self.assertFalse(AvisoLeido.objects.exists())
        self.assertFalse(Solicitud.objects.exists())
        self.assertFalse(ValidacionVersion.objects.exists())

    def test_admin_capabilities_are_separate_and_not_granted_by_staff(self):
        endpoints = ['/api/admin/flota', '/api/admin/soporte', '/api/admin/gobernanza', '/api/admin/cambios']
        for user in [self.owner, self.staff]:
            for url in endpoints:
                with self.subTest(user_id=user.pk, url=url):
                    self.assertEqual(self.client_for(user).get(url).status_code, 403)
        flota_user = self.user('web-fleet-only@example.test')
        self.grant(flota_user, 'ver_flota')
        fleet_client = self.client_for(flota_user)
        self.assertEqual(fleet_client.get('/api/admin/flota').status_code, 200)
        for path in endpoints[1:]:
            self.assertEqual(fleet_client.get(path).status_code, 403)
        flota_user.user_permissions.clear()
        self.assertEqual(fleet_client.get('/api/admin/flota').status_code, 403)

    def test_administrative_projections_do_not_fabricate_telemetry_or_active_version(self):
        admin_client = self.client_for(self.admin)
        fleet = admin_client.get('/api/admin/flota')
        self.assertEqual(fleet.status_code, 200)
        body = fleet.json()
        fleet_data = body.get('fleet', body)
        self.assertTrue(fleet_data['nodes'])
        self.assertTrue(all(node['connected'] is None for node in fleet_data['nodes']))
        changes = admin_client.get('/api/admin/cambios')
        self.assertEqual(changes.status_code, 200)
        data = changes.json()
        self.assertIsNone(data.get('changes', data)['activeVersion'])
        self.assertEqual(admin_client.get('/api/admin/gobernanza').status_code, 200)

    def test_support_requires_explicit_boolean_consent(self):
        for consent in [False, None, 'true', 1]:
            self.assertEqual(self.post('/api/soporte', {'incident': 'connection', 'consent': consent}).status_code, 400)
        self.assertFalse(CasoSoporte.objects.exists())
        self.assertFalse(PermisoSoporte.objects.exists())
        self.assertFalse(Mantenimiento.objects.exists())

    def test_support_token_is_once_only_and_never_in_lists_verifier_or_idempotency_storage(self):
        key = uuid.uuid4()
        body = {'incident': 'connection', 'consent': True}
        first = self.accepted(self.post('/api/soporte', body, key=key))
        permission = first['permission']
        raw = permission['token']
        self.assertEqual(len(raw), 43)
        self.assertTrue(all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in raw))
        replay = self.accepted(self.post('/api/soporte', body, key=key))
        self.assertIsNone(replay['permission']['token'])
        self.assertEqual(CasoSoporte.objects.count(), 1)
        self.assertEqual(PermisoSoporte.objects.count(), 1)
        stored = PermisoSoporte.objects.get()
        self.assertEqual(len(stored.verificador), 64)
        self.assertTrue(stored.verificador != raw, 'Only the protected verifier is persisted.')
        for client, path in [(self.client, '/api/soporte'), (self.client_for(self.admin), '/api/admin/soporte')]:
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            rendered = response.content.decode()
            self.assertTrue(raw not in rendered, 'Raw support token must not appear in listings.')
            self.assertTrue(stored.verificador not in rendered, 'Protected verifier must not appear in listings.')
        ledger = apps.get_model('web', 'Idempotencia')
        persisted = json.dumps(list(ledger.objects.values()), default=str)
        self.assertTrue(raw not in persisted, 'Raw support token must not enter the idempotency ledger.')
        self.assertEqual(Mantenimiento.objects.count(), 0)

    def test_support_token_body_only_exact_case_and_malformed_token_rejected(self):
        permission = self.issue()
        admin_client = self.client_for(self.admin)
        path = '/api/admin/soporte/' + permission['ticket'] + '/abrir'
        self.assertEqual(admin_client.get(path + '?token=' + permission['token']).status_code, 405)
        for token in [permission['token'] + ' ', permission['token'][:-1], 43]:
            self.assertIn(self.post(path, {'token': token}, client=admin_client).status_code, [400, 403])
        altered = ('A' if permission['token'][0] != 'A' else 'B') + permission['token'][1:]
        self.assertEqual(self.post(path, {'token': altered}, client=admin_client).status_code, 403)
        self.assertEqual(SesionTecnica.objects.count(), 0)
        self.accepted(self.post(path, {'token': permission['token']}, client=admin_client))
        self.assertEqual(SesionTecnica.objects.count(), 1)

    def test_support_case_owner_and_console_owner_are_rechecked(self):
        permission = self.issue()
        other_client = self.client_for(self.other)
        path = '/api/soporte/' + permission['ticket'] + '/revocar'
        self.assertEqual(self.post(path, {}, client=other_client).status_code, 403)
        self.assertIsNone(PermisoSoporte.objects.get().revocado_en)
        admin_client, session_id = self.open_console(permission)
        second_admin = self.user('web-second-admin@example.test')
        self.grant(second_admin, 'atender_soporte')
        for suffix, payload in [('accion', {'action': 'diagnostic'}), ('cerrar', {})]:
            response = self.post(f'/api/admin/sesiones/{session_id}/{suffix}', payload, client=self.client_for(second_admin))
            self.assertEqual(response.status_code, 403)
        self.accepted(self.post(f'/api/admin/sesiones/{session_id}/accion', {'action': 'diagnostic'}, client=admin_client))

    def test_technical_diagnosis_and_restart_are_unavailable_or_pending_not_executed(self):
        admin_client, session_id = self.open_console(self.issue())
        diagnosis = self.accepted(self.post(f'/api/admin/sesiones/{session_id}/accion', {'action': 'diagnostic'}, client=admin_client))
        data = diagnosis.get('diagnosis', diagnosis)
        self.assertEqual(data['source'], 'unavailable')
        self.assertEqual(data['pins'], [])
        self.assertEqual(data['logs'], [])
        self.assertIsNone(data['at'])
        self.accepted(self.post(f'/api/admin/sesiones/{session_id}/accion', {'action': 'restart-node'}, client=admin_client))
        request = Solicitud.objects.get()
        self.assertEqual(request.estado, 'pending')
        self.assertEqual(request.sesion_tecnica_id, uuid.UUID(session_id))

    def test_support_expiry_revocation_and_console_close_are_distinct(self):
        permission = self.issue()
        admin_client, session_id = self.open_console(permission)
        self.accepted(self.post(f'/api/admin/sesiones/{session_id}/cerrar', {}, client=admin_client))
        permit = PermisoSoporte.objects.get()
        self.assertIsNone(permit.revocado_en)
        self.assertEqual(self.post(f'/api/admin/sesiones/{session_id}/accion', {'action': 'diagnostic'}, client=admin_client).status_code, 403)
        response = self.post('/api/admin/soporte/' + permission['ticket'] + '/abrir', {'token': permission['token']}, client=admin_client)
        session_id = self.accepted(response)['session']['id']
        # Advance only the service clock: patching the shared timezone.now would
        # also expire Django's eight-hour browser session before this check.
        with patch('datos.services.timezone', wraps=timezone) as support_clock:
            support_clock.now.return_value = permit.vence_en
            self.assertEqual(self.post(f'/api/admin/sesiones/{session_id}/accion', {'action': 'diagnostic'}, client=admin_client).status_code, 403)
        self.accepted(self.post('/api/soporte/' + permission['ticket'] + '/revocar', {}))
        permit.refresh_from_db()
        self.assertIsNotNone(permit.revocado_en)
        self.assertEqual(self.post(f'/api/admin/sesiones/{session_id}/accion', {'action': 'diagnostic'}, client=admin_client).status_code, 403)
        self.assertEqual(CasoSoporte.objects.count(), 1)

    def test_logout_invalidates_browser_and_closes_technical_session_without_revocation(self):
        permission = self.issue()
        admin_client, session_id = self.open_console(permission)
        response = admin_client.delete('/_allauth/browser/v1/auth/session')
        self.assertIn(response.status_code, [200, 401])
        self.assertEqual(admin_client.get('/api/admin/soporte').status_code, 401)
        technical = SesionTecnica.objects.get(pk=session_id)
        self.assertIsNotNone(technical.cerrada_en)
        self.assertEqual(technical.motivo_cierre, 'logout')
        self.assertIsNone(PermisoSoporte.objects.get().revocado_en)

    def test_administrative_changes_persist_validation_revision_and_pending_requests(self):
        admin_client = self.client_for(self.admin)
        validation_response = self.accepted(self.post('/api/admin/validaciones',
            {'type': 'weights', 'version': 'v-http-1', 'notes': "O'Hara; SELECT remains text"}, client=admin_client))
        validation_id = validation_response['validation']['id']
        self.accepted(self.post('/api/admin/despliegues', {'validationId': validation_id}, client=admin_client))
        content = "Conocimiento sintético <script>alert(1)</script> O'Hara; SELECT."
        self.accepted(self.post('/api/admin/conocimiento', {'content': content}, client=admin_client))
        self.accepted(self.post('/api/admin/reinicio', {}, client=admin_client))
        self.assertEqual(ValidacionVersion.objects.count(), 1)
        self.assertEqual(RevisionConocimiento.objects.get().contenido, content)
        self.assertEqual(Solicitud.objects.count(), 2)
        self.assertEqual(set(Solicitud.objects.values_list('estado', flat=True)), {'pending'})
        response = self.client_for(self.admin).get('/api/admin/cambios')
        self.assertEqual(response.status_code, 200)
        serialized = json.dumps(response.json())
        self.assertTrue(content in serialized or content in json.loads(serialized).get('knowledge', ''), 'Knowledge text is returned as JSON data.')

    def test_list_pagination_is_bounded_and_bad_page_is_rejected(self):
        for page in ['0', '-1', 'x']:
            self.assertEqual(self.client.get('/api/huertos/actual/avisos', {'page': page}).status_code, 400)
        for _ in range(3):
            self.accepted(self.post('/api/huertos/actual/mantenimiento', {'type': 'inspection'}))
        response = self.client.get('/api/huertos/actual/mantenimiento', {'page': '1'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['total'], 3)
        self.assertEqual(body['page'], 1)
        self.assertLessEqual(len(body['items']), 100)

    def test_api_and_error_responses_are_noncacheable_and_have_browser_protection_headers(self):
        for path in ['/api/cuenta', '/api/huertos/actual', '/api/admin/flota']:
            response = self.client.get(path)
            self.assertIn('no-store', response.get('Cache-Control', ''))
            self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
            self.assertEqual(response.get('X-Frame-Options'), 'DENY')
            policy = response.get('Content-Security-Policy', '')
            self.assertIn("script-src 'self'", policy)
            self.assertIn("object-src 'none'", policy)
            self.assertIn("frame-ancestors 'none'", policy)

    def test_technical_token_attempts_have_a_server_side_limit(self):
        permission = self.issue()
        admin_client = self.client_for(self.admin)
        path = '/api/admin/soporte/' + permission['ticket'] + '/abrir'
        # Freeze the quota window only; never alter the fixture's expiry.
        now = timezone.now()
        statuses = []
        with patch('web.api.timezone.now', return_value=now):
            for _ in range(16):
                response = self.post(path, {'token': 'A' * 43}, client=admin_client)
                statuses.append(response.status_code)
        self.assertEqual(statuses[-1], 429)
        self.assertTrue(all(code in [403, 429] for code in statuses))
        self.assertEqual(SesionTecnica.objects.count(), 0)

    def test_replayed_open_after_revocation_cannot_restore_access_or_repeat_audit(self):
        permission = self.issue()
        admin_client = self.client_for(self.admin)
        path = '/api/admin/soporte/' + permission['ticket'] + '/abrir'
        key = uuid.uuid4()
        original = self.accepted(self.post(path, {'token': permission['token']}, client=admin_client, key=key))
        session_id = original['session']['id']
        self.accepted(self.post('/api/soporte/' + permission['ticket'] + '/revocar', {}))
        audit_count = Auditoria.objects.count()
        # A replay is a receipt of the original operation, not a new authorization.
        replay = self.accepted(self.post(path, {'token': permission['token']}, client=admin_client, key=key))
        self.assertEqual(replay['session']['id'], session_id)
        self.assertEqual(SesionTecnica.objects.count(), 1)
        self.assertEqual(Auditoria.objects.count(), audit_count)
        self.assertIsNotNone(SesionTecnica.objects.get(pk=session_id).cerrada_en)
        self.assertTrue(permission['token'] not in json.dumps(replay), 'A session receipt contains no raw token.')
        denied = self.post(f'/api/admin/sesiones/{session_id}/accion', {'action': 'diagnostic'}, client=admin_client)
        self.assertEqual(denied.status_code, 403)

    def test_idempotent_receipts_do_not_bypass_revoked_membership_or_return_old_notice_text(self):
        notice_path = f'/api/huertos/actual/avisos/{self.notice.pk}/lectura'
        maintenance_path = '/api/huertos/actual/mantenimiento'
        notice_key, maintenance_key = uuid.uuid4(), uuid.uuid4()
        self.accepted(self.post(notice_path, {}, key=notice_key))
        self.accepted(self.post(maintenance_path, {'type': 'inspection'}, key=maintenance_key))
        audit_count = Auditoria.objects.count()
        Membresia.objects.filter(usuario=self.owner, huerto=self.garden).update(activa=False)
        for path, payload, key in [(notice_path, {}, notice_key),
                                   (maintenance_path, {'type': 'inspection'}, maintenance_key)]:
            response = self.post(path, payload, key=key)
            self.assertEqual(response.status_code, 403)
            data = response.json()
            self.assertNotIn('item', data)
            self.assertNotIn('notice', data)
            self.assertNotIn('record', data)
            self.assertTrue(self.notice.titulo not in response.content.decode(), 'Revoked membership must not recover stored notice contents.')
        self.assertEqual(Mantenimiento.objects.count(), 1)
        self.assertEqual(AvisoLeido.objects.filter(usuario=self.owner).count(), 1)
        self.assertEqual(Auditoria.objects.count(), audit_count)

    def test_maintenance_pagination_limits_the_database_read_before_serialization(self):
        Mantenimiento.objects.bulk_create([
            Mantenimiento(actor=self.owner, huerto=self.garden, tipo='inspection')
            for _ in range(26)
        ])
        with CaptureQueriesContext(connection) as queries:
            first = self.client.get('/api/huertos/actual/mantenimiento', {'page': '1'})
        self.assertEqual(first.status_code, 200)
        page_one = first.json()
        self.assertEqual(page_one['total'], 26)
        self.assertEqual(len(page_one['items']), 25)
        # Counting can read the total; the row-producing maintenance query must
        # itself be bounded, not an unbounded list sliced later in Python.
        row_queries = [q['sql'] for q in queries.captured_queries
                       if 'datos_mantenimiento' in q['sql'].lower()
                       and q['sql'].lstrip().lower().startswith('select')
                       and 'count(' not in q['sql'].lower()]
        self.assertTrue(row_queries, 'The endpoint reads the maintenance rows.')
        self.assertTrue(all(re.search(r'\bLIMIT\s+(?:25|26)\b', q, re.IGNORECASE) for q in row_queries),
                        'The row-producing query is bounded to the page before DTO creation.')
        second = self.client.get('/api/huertos/actual/mantenimiento', {'page': '2'})
        self.assertEqual(second.status_code, 200)
        page_two = second.json()
        self.assertEqual(page_two['total'], 26)
        self.assertEqual(len(page_two['items']), 1)
        self.assertTrue({item['id'] for item in page_one['items']}.isdisjoint(
            {item['id'] for item in page_two['items']}))
