"""Tests of the trusted data-service boundary, not an HTTP endpoint or live frontend.

Database tests require the package's named synthetic PostgreSQL database. No email,
external service, sensor, real device or deployment is involved. Raw support tokens
are generated in memory and never logged or placed in reusable fixtures.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, datetime, timezone as datetime_timezone
import json
import secrets
import threading
from unittest import skipUnless
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, connections, IntegrityError
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from huerto.models import Huerto, Membresia
from datos.models import (
    Dispositivo, Mantenimiento, CasoSoporte, PermisoSoporte, SesionTecnica,
    ValidacionVersion, RevisionConocimiento, Solicitud, Auditoria,
)
from datos import services


class TokenContractWithoutDatabaseTests(SimpleTestCase):
    """Cryptographic/serialization rules that can be checked without PostgreSQL."""

    @override_settings(CHILITO_SUPPORT_KEY=secrets.token_urlsafe(48))
    def test_urlsafe_token_and_case_sensitive_verifier(self):
        raw = secrets.token_urlsafe(32)
        self.assertTrue(services.TOKEN_RE.fullmatch(raw) is not None)
        self.assertEqual(len(raw), 43)
        digest = services.token_verifier(raw)
        self.assertEqual(len(digest), 64)
        self.assertTrue(digest == services.token_verifier(raw))
        # A different valid character is a different token; no strip/upper operation.
        changed = ('A' if raw[0] != 'A' else 'B') + raw[1:]
        self.assertTrue(digest != services.token_verifier(changed))
        for invalid in [raw + ' ', ' ' + raw, raw[:-1], raw + 'x', None, 43]:
            with self.subTest(type=type(invalid).__name__):
                with self.assertRaises(PermissionDenied):
                    services.token_verifier(invalid)

    def test_missing_or_short_external_key_fails_closed(self):
        for key in ['', 'short']:
            with self.subTest(length=len(key)), override_settings(CHILITO_SUPPORT_KEY=key):
                with self.assertRaises(ValidationError):
                    services.token_verifier(secrets.token_urlsafe(32))

    @override_settings(CHILITO_SUPPORT_KEY=secrets.token_urlsafe(48))
    def test_key_rotation_changes_verifier(self):
        raw = secrets.token_urlsafe(32)
        first = services.token_verifier(raw)
        with override_settings(CHILITO_SUPPORT_KEY=secrets.token_urlsafe(48)):
            self.assertTrue(first != services.token_verifier(raw))

    def test_permission_state_and_epoch_milliseconds_match_the_contract(self):
        now = timezone.now()
        record = type('PermissionRecord', (), {
            'revocado_en': None, 'vence_en': now + timedelta(hours=1),
        })()
        self.assertEqual(services.permission_state(record, now), 'active')
        self.assertEqual(services.permission_state(record, record.vence_en), 'expired')
        record.revocado_en = now
        self.assertEqual(services.permission_state(record, now), 'revoked')
        encoded = int(now.timestamp() * 1000)
        self.assertIsInstance(encoded, int)
        restored = datetime.fromtimestamp(encoded / 1000, tz=datetime_timezone.utc)
        self.assertLess(abs((now - restored).total_seconds()), .0011)


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL, not an SQLite substitute.')
@override_settings(CHILITO_SUPPORT_KEY=secrets.token_urlsafe(48))
class TrustedDataServiceTests(TransactionTestCase):
    """Authorization tested through the layer that actually enforces it."""

    def setUp(self):
        if not str(connection.settings_dict['NAME']).startswith('test_chilito_integracion_sinteticos'):
            raise RuntimeError('Refusing service tests outside the named synthetic test database.')
        self.owner = self.make_user('service-owner@example.test')
        self.other = self.make_user('service-other@example.test')
        self.admin = self.make_user('service-admin@example.test')
        self.second_admin = self.make_user('service-second-admin@example.test')
        self.superuser = self.make_user('service-root@example.test', is_staff=True, is_superuser=True)
        self.garden = Huerto.objects.create(clave='service-synthetic-a', nombre='Huerto sintético A')
        self.other_garden = Huerto.objects.create(clave='service-synthetic-b', nombre='Huerto sintético B')
        self.membership = Membresia.objects.create(usuario=self.owner, huerto=self.garden)
        Membresia.objects.create(usuario=self.other, huerto=self.other_garden)
        self.device = Dispositivo.objects.create(huerto=self.garden, identificador='service-device-a')
        Dispositivo.objects.create(huerto=self.other_garden, identificador='service-device-b')
        for actor in [self.admin, self.second_admin]:
            self.grant(actor, 'atender_soporte', 'gestionar_cambios', 'ver_flota', 'ver_gobernanza')

    def make_user(self, email, **fields):
        user = get_user_model().objects.create_user(email, secrets.token_urlsafe(24), **fields)
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        return user

    def grant(self, actor, *codes):
        permissions = Permission.objects.filter(content_type__app_label='datos', codename__in=codes)
        self.assertEqual(permissions.count(), len(codes))
        actor.user_permissions.add(*permissions)

    def issue(self, actor=None, garden=None, **options):
        return services.issue_support(actor or self.owner, (garden or self.garden).pk,
                                      'connection', True, **options)

    def opened_session(self):
        response = self.issue()
        session = services.open_technical(self.admin, response['permission']['ticket'],
                                          response['permission']['token'])
        return response, session

    def test_session_contract_requires_identity_and_explicit_admin_capabilities(self):
        with self.assertRaises(PermissionDenied):
            services.session_contract(AnonymousUser())
        user_contract = services.session_contract(self.owner)
        self.assertEqual(user_contract['role'], 'user')
        self.assertEqual(user_contract['capabilities'], [])
        self.assertEqual(user_contract['profile']['id'], str(self.owner.pk))
        # No implicit bypass from the Django infrastructure flags.
        self.assertEqual(services.session_contract(self.superuser)['role'], 'user')
        with self.assertRaises(PermissionDenied):
            services.request_platform_restart(self.superuser)
        admin_contract = services.session_contract(self.admin)
        self.assertEqual(admin_contract['role'], 'admin')
        self.assertIn('atender_soporte', admin_contract['capabilities'])

    def test_group_grants_work_and_removed_privileges_are_rechecked(self):
        group = Group.objects.create(name='synthetic-support-group')
        permission = Permission.objects.get(content_type__app_label='datos', codename='atender_soporte')
        group.permissions.add(permission)
        self.other.groups.add(group)
        self.assertIn('atender_soporte', services.capabilities(self.other))
        group.permissions.remove(permission)
        self.assertNotIn('atender_soporte', services.capabilities(self.other))
        self.admin.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            services.governance_projection(self.admin)

    def test_inactive_or_unverified_database_identity_overrides_stale_actor_object(self):
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            services.record_maintenance(self.owner, self.garden.pk, 'inspection')
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=True)
        EmailAddress.objects.filter(user=self.owner).update(verified=False)
        with self.assertRaises(PermissionDenied):
            services.session_contract(self.owner)

    def test_maintenance_is_durable_with_actor_resource_date_and_history(self):
        row = services.record_maintenance(self.owner, self.garden.pk, 'inspection')
        self.assertEqual(row.actor_id, self.owner.pk)
        self.assertEqual(row.huerto_id, self.garden.pk)
        self.assertTrue(timezone.is_aware(row.registrado_en))
        self.assertEqual(list(services.maintenance_history(self.owner, self.garden.pk)), [row])
        event = Auditoria.objects.get(accion='maintenance', mantenimiento=row)
        self.assertEqual(event.actor_id, self.owner.pk)
        with self.assertRaises(PermissionDenied):
            services.record_maintenance(self.other, self.garden.pk, 'inspection')
        with self.assertRaises(PermissionDenied):
            services.maintenance_history(self.other, self.garden.pk)
        with self.assertRaises(ValidationError):
            services.record_maintenance(self.owner, self.garden.pk, 'made-up')
        self.assertEqual(Mantenimiento.objects.count(), 1)
        self.assertEqual(CasoSoporte.objects.count(), 0)

    def test_revoked_membership_blocks_new_user_operations_without_deleting_history(self):
        services.record_maintenance(self.owner, self.garden.pk, 'refill')
        Membresia.objects.filter(pk=self.membership.pk).update(activa=False)
        for operation in [
            lambda: services.record_maintenance(self.owner, self.garden.pk, 'refill'),
            lambda: services.record_user_request(self.owner, self.garden.pk, 'water'),
            lambda: self.issue(),
        ]:
            with self.assertRaises(PermissionDenied):
                operation()
        self.assertEqual(Mantenimiento.objects.count(), 1)

    def test_user_requests_are_saved_as_pending_without_device_actuation(self):
        for kind in ['water', 'lamp-off', 'lamp-auto']:
            row = services.record_user_request(self.owner, self.garden.pk, kind)
            self.assertEqual(row.estado, 'pending')
            self.assertEqual(row.actor_id, self.owner.pk)
            self.assertEqual(row.dispositivo_id, self.device.pk)
            self.assertTrue(Auditoria.objects.filter(solicitud=row, resultado='pending').exists())
        with self.assertRaises(PermissionDenied):
            services.record_user_request(self.other, self.garden.pk, 'water')
        with self.assertRaises(ValidationError):
            services.record_user_request(self.owner, self.garden.pk, 'restart-platform')
        self.assertEqual(Solicitud.objects.count(), 3)

    def test_support_requires_boolean_consent_and_owned_resource(self):
        for consent in [False, None, 1, 'true']:
            with self.subTest(consent_type=type(consent).__name__):
                with self.assertRaises(ValidationError):
                    services.issue_support(self.owner, self.garden.pk, 'connection', consent)
        with self.assertRaises(ValidationError):
            services.issue_support(self.owner, self.garden.pk, 'made-up', True)
        with self.assertRaises(PermissionDenied):
            services.issue_support(self.other, self.garden.pk, 'connection', True)
        self.assertEqual(CasoSoporte.objects.count(), 0)
        self.assertEqual(PermisoSoporte.objects.count(), 0)

    def test_support_token_is_once_returned_raw_and_only_verifier_is_persisted(self):
        issued = self.issue()['permission']
        raw = issued['token']
        permission = PermisoSoporte.objects.get(caso_id=issued['ticket'])
        self.assertEqual(permission.otorgante_id, self.owner.pk)
        self.assertEqual(permission.caso.huerto_id, self.garden.pk)
        self.assertEqual(permission.caso.dispositivo_id, self.device.pk)
        self.assertEqual(permission.alcance, 'diagnostico_incidente')
        self.assertEqual(permission.vence_en - permission.emitido_en, timedelta(hours=24))
        self.assertTrue(permission.verificador == services.token_verifier(raw))
        stored = json.dumps({
            'permissions': list(PermisoSoporte.objects.values()),
            'cases': list(CasoSoporte.objects.values()),
            'audit': list(Auditoria.objects.values()),
        }, default=str)
        self.assertFalse(raw in stored)
        self.assertIsInstance(issued['createdAt'], int)
        self.assertIsInstance(issued['expiresAt'], int)
        self.assertEqual(issued['expiresAt'] - issued['createdAt'], 86400000)
        self.assertEqual(issued['user'], str(self.owner.pk))
        self.assertEqual(Mantenimiento.objects.count(), 0)

    def test_invalid_duration_does_not_create_partial_case_or_permission(self):
        for duration in [timedelta(0), timedelta(seconds=-1), timedelta(hours=24, seconds=1)]:
            with self.subTest(duration=duration):
                with self.assertRaises(ValidationError):
                    self.issue(duration=duration)
        self.assertEqual(CasoSoporte.objects.count(), 0)
        self.assertEqual(PermisoSoporte.objects.count(), 0)
        self.assertEqual(Auditoria.objects.count(), 0)

    def test_issuance_fails_closed_without_verifier_key(self):
        with override_settings(CHILITO_SUPPORT_KEY=''):
            with self.assertRaises(ValidationError):
                self.issue()
        self.assertEqual(CasoSoporte.objects.count(), 0)
        self.assertEqual(PermisoSoporte.objects.count(), 0)

    def test_case_token_and_technical_session_are_not_interchangeable(self):
        first = self.issue()['permission']
        second = self.issue(self.other, self.other_garden)['permission']
        with self.assertRaises(PermissionDenied):
            services.open_technical(self.admin, second['ticket'], first['token'])
        with self.assertRaises(PermissionDenied):
            services.open_technical(self.owner, first['ticket'], first['token'])
        session = services.open_technical(self.admin, first['ticket'], first['token'])
        with self.assertRaises(PermissionDenied):
            services.technical_action(self.second_admin, session.pk, 'diagnostic')
        with self.assertRaises(PermissionDenied):
            services.revoke_support(self.other, first['ticket'])

    def test_expiration_is_checked_again_at_each_technical_operation(self):
        issued, session = self.opened_session()
        deadline = PermisoSoporte.objects.get(pk=session.permiso_id).vence_en
        with patch('datos.services.timezone.now', return_value=deadline):
            with self.assertRaises(PermissionDenied):
                services.open_technical(self.admin, issued['permission']['ticket'], issued['permission']['token'])
            with self.assertRaises(PermissionDenied):
                services.technical_action(self.admin, session.pk, 'diagnostic')
            with self.assertRaises(PermissionDenied):
                services.technical_action(self.admin, session.pk, 'restart-node')
        self.assertEqual(Solicitud.objects.count(), 0)

    def test_revocation_closes_technical_session_and_preserves_case(self):
        issued, session = self.opened_session()
        response = services.revoke_support(self.owner, issued['permission']['ticket'])
        self.assertEqual(response['status'], 'accepted')
        session.refresh_from_db()
        self.assertIsNotNone(session.cerrada_en)
        self.assertEqual(session.motivo_cierre, 'revoked')
        with self.assertRaises(PermissionDenied):
            services.technical_action(self.admin, session.pk, 'diagnostic')
        with self.assertRaises(PermissionDenied):
            services.open_technical(self.admin, issued['permission']['ticket'], issued['permission']['token'])
        self.assertTrue(CasoSoporte.objects.filter(pk=issued['permission']['ticket']).exists())

    def test_new_permission_revokes_prior_one_and_keeps_both_reports(self):
        first, session = self.opened_session()
        second = self.issue()['permission']
        self.assertTrue(first['permission']['ticket'] != second['ticket'])
        old = PermisoSoporte.objects.get(caso_id=first['permission']['ticket'])
        self.assertIsNotNone(old.revocado_en)
        session.refresh_from_db()
        self.assertEqual(session.motivo_cierre, 'replaced')
        self.assertEqual(CasoSoporte.objects.count(), 2)

    def test_technical_actions_are_audited_and_request_only(self):
        issued, session = self.opened_session()
        diagnosis = services.technical_action(self.admin, session.pk, 'diagnostic')
        self.assertEqual(diagnosis['source'], 'unavailable')
        self.assertEqual(diagnosis['pins'], [])
        request = services.technical_action(self.admin, session.pk, 'restart-node')
        self.assertEqual(request.estado, 'pending')
        self.assertEqual(request.sesion_tecnica_id, session.pk)
        event = Auditoria.objects.get(solicitud=request)
        self.assertEqual(event.actor_id, self.admin.pk)
        self.assertEqual(event.permiso_id, session.permiso_id)
        self.assertEqual(event.caso_id, session.permiso.caso_id)
        services.close_technical(self.admin, session.pk)
        with self.assertRaises(PermissionDenied):
            services.technical_action(self.admin, session.pk, 'diagnostic')

    def test_deployment_uses_actor_owned_immutable_validation(self):
        validation = services.validate_version(self.admin, 'weights', 'v1.0', "Owner's notes; SELECT remains text")
        with self.assertRaises(PermissionDenied):
            services.request_deployment(self.second_admin, validation.pk)
        request = services.request_deployment(self.admin, validation.pk)
        self.assertEqual(request.validacion_id, validation.pk)
        self.assertEqual(request.estado, 'pending')
        with self.assertRaises(IntegrityError):
            services.request_deployment(self.admin, validation.pk)
        self.assertEqual(Solicitud.objects.count(), 1)

    def test_knowledge_retains_revisions_and_platform_restart_is_pending(self):
        content = "Texto sintético O'Hara; SELECT y apóstrofes se conservan como datos."
        first = services.save_knowledge(self.admin, content)
        second = services.save_knowledge(self.admin, content + ' Otra revisión.')
        self.assertTrue(second.pk > first.pk)
        self.assertEqual(RevisionConocimiento.objects.get(pk=first.pk).contenido, content)
        self.assertEqual(Auditoria.objects.filter(accion='knowledge-saved').count(), 2)
        request = services.request_platform_restart(self.admin)
        self.assertEqual(request.estado, 'pending')
        with self.assertRaises(PermissionDenied):
            services.save_knowledge(self.owner, content)

    def test_four_admin_capabilities_are_checked_separately(self):
        self.admin.user_permissions.clear()
        self.grant(self.admin, 'ver_flota')
        self.assertIn('nodes', services.fleet_projection(self.admin))
        with self.assertRaises(PermissionDenied):
            services.governance_projection(self.admin)
        with self.assertRaises(PermissionDenied):
            services.validate_version(self.admin, 'weights', 'v1.0')
        issued = self.issue()['permission']
        with self.assertRaises(PermissionDenied):
            services.open_technical(self.admin, issued['ticket'], issued['token'])

    def race(self, first_operation, second_operation):
        """Hold first operation after the real grantor-row lock; start the competitor.

        Threads use different Django connections. Releasing the gate lets PostgreSQL
        serialize the transactions; no sleep-based guess about the winner is used.
        """
        acquired = threading.Event()
        release = threading.Event()
        attempted = threading.Event()
        local = threading.local()
        original = services._owner_lock

        def gate(user_id):
            if local.order == 'first':
                result = original(user_id)
                acquired.set()
                if not release.wait(10):
                    raise RuntimeError('Concurrency gate timed out')
                return result
            attempted.set()
            return original(user_id)

        def worker(order, operation):
            connections.close_all()
            local.order = order
            try:
                return operation()
            finally:
                connections.close_all()

        with patch('datos.services._owner_lock', side_effect=gate):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(worker, 'first', first_operation)
                try:
                    self.assertTrue(acquired.wait(10))
                    second = executor.submit(worker, 'second', second_operation)
                    self.assertTrue(attempted.wait(10))
                finally:
                    release.set()
                first_result = first.result(timeout=15)
                second_result = second.result(timeout=15)
        return first_result, second_result

    def test_concurrent_revocation_wins_before_technical_use(self):
        issued, session = self.opened_session()

        def revoke():
            return services.revoke_support(self.owner, issued['permission']['ticket'])['status']

        def action():
            try:
                services.technical_action(self.admin, session.pk, 'restart-node')
                return 'accepted'
            except PermissionDenied:
                return 'denied'

        self.assertEqual(self.race(revoke, action), ('accepted', 'denied'))
        self.assertEqual(Solicitud.objects.count(), 0)

    def test_concurrent_use_commits_before_revocation_then_further_use_denied(self):
        issued, session = self.opened_session()

        def action():
            request = services.technical_action(self.admin, session.pk, 'restart-node')
            return request.estado

        def revoke():
            return services.revoke_support(self.owner, issued['permission']['ticket'])['status']

        self.assertEqual(self.race(action, revoke), ('pending', 'accepted'))
        self.assertEqual(Solicitud.objects.count(), 1)
        with self.assertRaises(PermissionDenied):
            services.technical_action(self.admin, session.pk, 'restart-node')
