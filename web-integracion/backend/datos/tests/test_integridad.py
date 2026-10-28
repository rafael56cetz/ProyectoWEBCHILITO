"""Executable PostgreSQL integrity checks for the isolated data package.

These tests deliberately bypass model ``full_clean`` with QuerySet/raw writes so
that rejection is attributed to PostgreSQL, not an HTTP API. They do not prove
API authorization, mail delivery, hardware actuation or a frontend integration.
Run only with the package's synthetic test database and a migration-owner role.
"""
from datetime import timedelta
import secrets
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction, IntegrityError, DataError
from django.test import TransactionTestCase, SimpleTestCase
from django.utils import timezone
from allauth.account.models import EmailAddress

from cuentas.adapters import ClosedRegistrationAdapter
from huerto.models import Huerto, Zona, Membresia, Aviso, AvisoLeido
from datos.models import (
    Dispositivo, Mantenimiento, CasoSoporte, PermisoSoporte, SesionTecnica,
    ValidacionVersion, RevisionConocimiento, Solicitud, Auditoria,
)


@skipUnless(connection.vendor == 'postgresql', 'These checks require PostgreSQL, not an SQLite substitute.')
class IntegridadPostgreSQLTests(TransactionTestCase):
    """Each case runs against synthetic rows; owner TRUNCATE is used by Django teardown."""

    def setUp(self):
        name = str(connection.settings_dict['NAME'])
        if not name.startswith('test_chilito_integracion_sinteticos'):
            raise RuntimeError('Refusing integrity tests outside the named synthetic test database.')
        user_model = get_user_model()
        # Generated only in memory. No fixture contains a reusable password or token.
        self.user = user_model.objects.create_user('owner-a@example.test', secrets.token_urlsafe(24))
        self.other = user_model.objects.create_user('owner-b@example.test', secrets.token_urlsafe(24))
        self.admin = user_model.objects.create_user('operator@example.test', secrets.token_urlsafe(24))
        for user in [self.user, self.other, self.admin]:
            EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        self.garden = Huerto.objects.create(clave='sintetico-a', nombre='Huerto sintético A')
        self.other_garden = Huerto.objects.create(clave='sintetico-b', nombre='Huerto sintético B')
        Membresia.objects.create(usuario=self.user, huerto=self.garden)
        Membresia.objects.create(usuario=self.other, huerto=self.other_garden)
        self.device = Dispositivo.objects.create(huerto=self.garden, identificador='synthetic-device-a')
        self.other_device = Dispositivo.objects.create(huerto=self.other_garden, identificador='synthetic-device-b')
        self.now = timezone.now()

    def rejected(self, operation):
        """Commit deferred constraints inside an atomic block; retain the outer test DB."""
        with self.assertRaises((IntegrityError, DataError)):
            with transaction.atomic():
                operation()
                with connection.cursor() as cursor:
                    cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')

    def raw_update(self, model, pk, field, value):
        # Identifiers are fixed model metadata, never request input; values use parameters.
        table = connection.ops.quote_name(model._meta.db_table)
        column = connection.ops.quote_name(model._meta.get_field(field).column)
        key = connection.ops.quote_name(model._meta.pk.column)
        with connection.cursor() as cursor:
            cursor.execute(f'UPDATE {table} SET {column} = %s WHERE {key} = %s', [value, pk])

    def raw_delete(self, model, pk):
        table = connection.ops.quote_name(model._meta.db_table)
        key = connection.ops.quote_name(model._meta.pk.column)
        with connection.cursor() as cursor:
            cursor.execute(f'DELETE FROM {table} WHERE {key} = %s', [pk])

    def case(self, **overrides):
        values = dict(huerto=self.garden, dispositivo=self.device,
                      solicitante=self.user, incidente='connection')
        values.update(overrides)
        return CasoSoporte.objects.create(**values)

    def permission(self, case=None, **overrides):
        values = dict(caso=case or self.case(), otorgante=self.user,
                      verificador=secrets.token_hex(32), emitido_en=self.now,
                      vence_en=self.now + timedelta(hours=23))
        values.update(overrides)
        return PermisoSoporte.objects.create(**values)

    def test_new_garden_contains_exactly_zones_one_two_three(self):
        for garden in [self.garden, self.other_garden]:
            rows = list(Zona.objects.filter(huerto=garden).order_by('numero').values('numero', 'nombre', 'cultivo'))
            self.assertEqual([row['numero'] for row in rows], [1, 2, 3])
            self.assertTrue(all(row['nombre'].strip() and row['cultivo'].strip() for row in rows))

    def test_zone_cannot_be_deleted_or_reassigned(self):
        zone = Zona.objects.get(huerto=self.garden, numero=1)
        self.rejected(lambda: self.raw_delete(Zona, zone.pk))
        self.rejected(lambda: self.raw_update(Zona, zone.pk, 'huerto', self.other_garden.pk))
        self.rejected(lambda: self.raw_update(Zona, zone.pk, 'numero', 2))
        self.assertEqual(Zona.objects.filter(huerto=self.garden).count(), 3)

    def test_zone_range_and_unique_number_are_database_constraints(self):
        for number in [0, 4, 1]:
            with self.subTest(number=number):
                self.rejected(lambda: Zona.objects.bulk_create([
                    Zona(huerto=self.garden, numero=number, nombre='Otra zona', cultivo='Chile habanero')]))

    def test_significant_text_is_checked_in_postgresql(self):
        zone = Zona.objects.get(huerto=self.garden, numero=1)
        for text in ['', '   ', '\t\n']:
            for model, pk, field in [
                (Huerto, self.garden.pk, 'nombre'),
                (Zona, zone.pk, 'nombre'), (Zona, zone.pk, 'cultivo'),
            ]:
                with self.subTest(model=model.__name__, field=field, text=repr(text)):
                    self.rejected(lambda: self.raw_update(model, pk, field, text))
        empty_garden = Huerto.objects.create(clave='sintetico-sin-equipo', nombre='Sin equipo')
        self.rejected(lambda: Dispositivo.objects.create(huerto=empty_garden, identificador='   '))

    def test_apostrophes_and_sql_looking_text_remain_data(self):
        text = "O'Hara'); DROP TABLE huerto_zona; --"
        zone = Zona.objects.get(huerto=self.garden, numero=1)
        self.raw_update(Zona, zone.pk, 'nombre', text)
        zone.refresh_from_db()
        self.assertEqual(zone.nombre, text)
        self.assertEqual(Zona.objects.filter(huerto=self.garden).count(), 3)
        revision = RevisionConocimiento.objects.create(autor=self.admin, contenido=text)
        self.assertEqual(revision.contenido, text)

    def test_membership_pair_is_unique_and_identity_is_stable(self):
        self.rejected(lambda: Membresia.objects.bulk_create([
            Membresia(usuario=self.user, huerto=self.garden)]))
        member = Membresia.objects.get(usuario=self.user, huerto=self.garden)
        self.rejected(lambda: self.raw_update(Membresia, member.pk, 'usuario', self.admin.pk))
        self.rejected(lambda: self.raw_update(Membresia, member.pk, 'huerto', self.other_garden.pk))
        # Revocation changes availability; it does not rewrite or delete the relation.
        Membresia.objects.filter(pk=member.pk).update(activa=False)
        self.assertFalse(Membresia.objects.get(pk=member.pk).activa)

    def test_notice_zone_must_belong_to_notice_garden(self):
        foreign_zone = Zona.objects.get(huerto=self.other_garden, numero=1)
        self.rejected(lambda: Aviso.objects.bulk_create([
            Aviso(huerto=self.garden, zona=foreign_zone, severidad='informacion',
                  titulo='Aviso sintético', descripcion='Prueba aislada', creado_en=self.now)]))

    def test_notice_severity_resolution_dates_and_null_zone(self):
        base = dict(huerto=self.garden, zona=None, titulo='Aviso sintético',
                    descripcion='Prueba aislada', creado_en=self.now)
        notice = Aviso.objects.create(**base, severidad='informacion')
        self.assertIsNone(notice.zona_id)
        self.assertIsNone(notice.resuelto_en)
        self.rejected(lambda: Aviso.objects.bulk_create([Aviso(**base, severidad='urgent')]))
        self.rejected(lambda: Aviso.objects.bulk_create([
            Aviso(**base, severidad='critico', resuelto_en=self.now - timedelta(seconds=1))]))
        self.rejected(lambda: self.raw_update(Aviso, notice.pk, 'huerto', self.other_garden.pk))
        self.rejected(lambda: self.raw_update(Aviso, notice.pk, 'titulo', '  '))
        self.rejected(lambda: self.raw_update(Aviso, notice.pk, 'descripcion', '\t'))

    def test_notice_read_requires_membership_and_is_not_resolution(self):
        notice = Aviso.objects.create(huerto=self.garden, severidad='informacion', titulo='Aviso',
                                     descripcion='Prueba aislada', creado_en=self.now)
        self.rejected(lambda: AvisoLeido.objects.bulk_create([
            AvisoLeido(aviso=notice, usuario=self.other, leido_en=self.now)]))
        read = AvisoLeido.objects.create(aviso=notice, usuario=self.user, leido_en=self.now)
        self.rejected(lambda: AvisoLeido.objects.bulk_create([
            AvisoLeido(aviso=notice, usuario=self.user, leido_en=self.now)]))
        self.rejected(lambda: self.raw_update(AvisoLeido, read.pk, 'usuario', self.other.pk))
        notice.refresh_from_db()
        self.assertIsNone(notice.resuelto_en)

    def test_foreign_key_rejects_nonexistent_resource(self):
        self.rejected(lambda: Mantenimiento.objects.create(
            huerto_id=9223372036854775000, actor=self.user, tipo='inspection'))

    def test_support_case_rejects_device_from_another_garden(self):
        self.rejected(lambda: self.case(dispositivo=self.other_device))
        self.rejected(lambda: self.case(incidente='made-up'))

    def test_permission_is_tied_to_case_requester_and_limited_scope(self):
        case = self.case()
        self.rejected(lambda: self.permission(case, otorgante=self.other))
        self.rejected(lambda: self.permission(case, alcance='all_household_data'))
        self.rejected(lambda: self.permission(case, verificador='not-a-verifier'))
        permission = self.permission(case)
        self.rejected(lambda: self.permission(case, verificador=permission.verificador))

    def test_permission_window_and_revocation_dates(self):
        for deadline in [self.now, self.now - timedelta(seconds=1), self.now + timedelta(hours=24, microseconds=1)]:
            with self.subTest(deadline=deadline):
                self.rejected(lambda: self.permission(vence_en=deadline))
        self.rejected(lambda: self.permission(revocado_en=self.now - timedelta(seconds=1)))
        permission = self.permission(vence_en=self.now + timedelta(hours=24))
        self.assertEqual(permission.vence_en - permission.emitido_en, timedelta(hours=24))
        # Past records are valid history; expiration must be checked at use by service.
        old = self.permission(emitido_en=self.now - timedelta(days=2),
                              vence_en=self.now - timedelta(days=1))
        self.assertLess(old.vence_en, self.now)

    def test_permission_cannot_be_extended_or_unrevoked(self):
        permission = self.permission()
        self.rejected(lambda: self.raw_update(PermisoSoporte, permission.pk, 'vence_en', self.now + timedelta(hours=24)))
        PermisoSoporte.objects.filter(pk=permission.pk).update(revocado_en=self.now + timedelta(seconds=1))
        self.rejected(lambda: self.raw_update(PermisoSoporte, permission.pk, 'revocado_en', None))
        self.rejected(lambda: self.raw_delete(PermisoSoporte, permission.pk))

    def test_technical_session_close_is_coherent_and_irreversible(self):
        permission = self.permission()
        self.rejected(lambda: SesionTecnica.objects.create(
            permiso=permission, administrador=self.admin, iniciada_en=self.now,
            cerrada_en=self.now - timedelta(seconds=1), motivo_cierre='explicit'))
        session = SesionTecnica.objects.create(permiso=permission, administrador=self.admin, iniciada_en=self.now)
        SesionTecnica.objects.filter(pk=session.pk).update(
            cerrada_en=self.now + timedelta(seconds=1), motivo_cierre='explicit')
        self.rejected(lambda: self.raw_update(SesionTecnica, session.pk, 'cerrada_en', None))
        self.rejected(lambda: self.raw_update(SesionTecnica, session.pk, 'administrador', self.other.pk))

    def test_requests_require_correct_shape_and_never_claim_execution(self):
        self.rejected(lambda: Solicitud.objects.create(actor=self.user, tipo='water'))
        self.rejected(lambda: Solicitud.objects.create(actor=self.user, tipo='water',
            huerto=self.garden, dispositivo=self.other_device))
        self.rejected(lambda: Solicitud.objects.create(actor=self.user, tipo='water',
            huerto=self.garden, dispositivo=self.device, estado='executed'))
        request = Solicitud.objects.create(actor=self.user, tipo='water',
            huerto=self.garden, dispositivo=self.device)
        self.assertEqual(request.estado, 'pending')
        self.rejected(lambda: self.raw_update(Solicitud, request.pk, 'estado', 'executed'))

    def test_deployment_is_bound_to_validated_actor_type_and_one_request(self):
        version = ValidacionVersion.objects.create(actor=self.admin, tipo='weights',
                                                  version='v1.0', notas="Owner's SQL-looking notes --")
        self.rejected(lambda: Solicitud.objects.create(actor=self.other, tipo='weights', validacion=version))
        self.rejected(lambda: Solicitud.objects.create(actor=self.admin, tipo='rollback', validacion=version))
        request = Solicitud.objects.create(actor=self.admin, tipo='weights', validacion=version)
        self.rejected(lambda: Solicitud.objects.create(actor=self.admin, tipo='weights', validacion=version))
        self.assertEqual(request.estado, 'pending')

    def test_restart_node_uses_same_actor_and_case_resource(self):
        permission = self.permission()
        session = SesionTecnica.objects.create(permiso=permission, administrador=self.admin, iniciada_en=self.now)
        self.rejected(lambda: Solicitud.objects.create(actor=self.other, tipo='restart-node',
            huerto=self.garden, dispositivo=self.device, sesion_tecnica=session))
        self.rejected(lambda: Solicitud.objects.create(actor=self.admin, tipo='restart-node',
            huerto=self.other_garden, dispositivo=self.other_device, sesion_tecnica=session))

    def test_knowledge_and_validation_lengths_are_database_checked(self):
        for content in [' ', 'x' * 19, 'x' * 10001]:
            with self.subTest(length=len(content)):
                self.rejected(lambda: RevisionConocimiento.objects.create(autor=self.admin, contenido=content))
        for version in ['ab', 'contains spaces', 'x' * 65]:
            with self.subTest(version=version):
                self.rejected(lambda: ValidacionVersion.objects.create(actor=self.admin, tipo='weights', version=version))
        self.rejected(lambda: ValidacionVersion.objects.create(actor=self.admin, tipo='weights', version='v1.0', notas='x' * 2001))

    def test_history_and_audit_are_append_only_even_via_raw_sql(self):
        maintenance = Mantenimiento.objects.create(huerto=self.garden, actor=self.user, tipo='inspection')
        case = self.case()
        version = ValidacionVersion.objects.create(actor=self.admin, tipo='weights', version='v1.0')
        knowledge = RevisionConocimiento.objects.create(autor=self.admin, contenido='Conocimiento sintético suficiente para la prueba.')
        request = Solicitud.objects.create(actor=self.admin, tipo='restart-platform')
        audit = Auditoria.objects.create(actor=self.admin, accion='request-recorded', solicitud=request, resultado='pending')
        fixtures = [(Mantenimiento, maintenance.pk, 'tipo', 'harvest'),
                    (CasoSoporte, case.pk, 'incidente', 'pump'),
                    (ValidacionVersion, version.pk, 'version', 'v2.0'),
                    (RevisionConocimiento, knowledge.pk, 'contenido', 'Contenido modificado que no debe sobreescribir la revisión.'),
                    (Solicitud, request.pk, 'tipo', 'restart-platform'),
                    (Auditoria, audit.pk, 'resultado', 'recorded')]
        for model, pk, field, value in fixtures:
            with self.subTest(model=model.__name__):
                self.rejected(lambda: self.raw_update(model, pk, field, value))
                self.rejected(lambda: self.raw_delete(model, pk))
        self.assertTrue(Auditoria.objects.filter(pk=audit.pk).exists())

    def test_audit_references_cannot_mix_resources(self):
        case = self.case()
        permission = self.permission(case)
        self.rejected(lambda: Auditoria.objects.create(actor=self.admin, accion='support-granted',
            huerto=self.other_garden, caso=case, permiso=permission))
        self.rejected(lambda: Auditoria.objects.create(actor=self.admin, accion='invalid-action'))

    def test_expected_query_indexes_exist(self):
        expected = {
            Mantenimiento: 'mant_huerto_fecha_idx',
            CasoSoporte: 'caso_solicitante_fecha_idx',
            PermisoSoporte: 'permiso_caso_vence_idx',
            Solicitud: 'solicitud_huerto_fecha_idx',
            Auditoria: 'auditoria_actor_fecha_idx',
        }
        with connection.cursor() as cursor:
            for model, name in expected.items():
                with self.subTest(index=name):
                    constraints = connection.introspection.get_constraints(cursor, model._meta.db_table)
                    self.assertIn(name, constraints)
                    self.assertTrue(constraints[name]['index'])


class PoliticaPasswordSinBaseTests(SimpleTestCase):
    """Framework checks without sending mail, opening sessions or creating accounts."""

    def test_password_minimum_15_and_maximum_256_in_original_adapter(self):
        adapter = ClosedRegistrationAdapter()
        # This function checks the framework policy before hashing, not hash-column capacity.
        with self.assertRaises(ValidationError):
            adapter.clean_password('x' * 14)
        with self.assertRaises(ValidationError):
            adapter.clean_password('x' * 257)
        for length in [15, 256]:
            candidate = secrets.token_urlsafe(256)[:length]
            self.assertTrue(adapter.clean_password(candidate) == candidate)

    def test_framework_hash_preserves_long_password_and_unicode_exactly(self):
        from django.contrib.auth.hashers import make_password, check_password
        candidate = 'Cultivo ágil 🌱 ' + secrets.token_urlsafe(32)
        encoded = make_password(candidate)
        self.assertTrue(encoded != candidate)
        self.assertTrue(check_password(candidate, encoded))
        self.assertFalse(check_password(candidate + ' ', encoded))
