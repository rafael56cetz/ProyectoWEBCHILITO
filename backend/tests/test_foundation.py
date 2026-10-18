from pathlib import Path
from unittest.mock import patch
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, IntegrityError, ProgrammingError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, SimpleTestCase
from cuentas.adapters import ClosedRegistrationAdapter
from cuentas.email import DisabledEmailBackend, MailUnavailable
from huerto.models import Huerto, Zona, Membresia
from huerto.services import provision_garden, assign_membership, visible_gardens, require_garden

class FoundationTests(TestCase):
    def user(self, email="persona@example.invalid", verified=False, **kwargs):
        user = get_user_model().objects.create_user(email=email, **kwargs)
        if verified:
            EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
        return user

    def test_email_identity_normalizes(self):
        user = self.user(" Persona@Example.invalid ")
        self.assertEqual(user.email, "persona@example.invalid")
        self.assertEqual(get_user_model().objects.get_by_natural_key("PERSONA@example.invalid"), user)

    def test_password_is_derived_not_stored_plain(self):
        password = "Frase local extensa 9 para pruebas!"
        user = get_user_model().objects.create_user("hash@example.invalid", password)
        self.assertNotEqual(user.password, password)
        self.assertTrue(user.check_password(password))

    def test_weak_password_rejected(self):
        with self.assertRaises(ValidationError):
            get_user_model().objects.create_user("weak@example.invalid", "123")

    def test_db_case_insensitive_unique_even_without_clean(self):
        self.user()
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.bulk_create([get_user_model()(email="PERSONA@example.invalid", password="!")])

    def test_registration_grants_neither_verification_nor_membership(self):
        user = self.user()
        self.assertFalse(EmailAddress.objects.filter(user=user, verified=True).exists())
        self.assertFalse(Membresia.objects.filter(usuario=user).exists())

    def test_signup_closed_and_no_email_fallback(self):
        self.assertFalse(ClosedRegistrationAdapter().is_open_for_signup(None))
        with self.assertRaises(MailUnavailable):
            DisabledEmailBackend().send_messages([object()])

    def test_provision_idempotent_and_preserves_manual_names(self):
        garden = provision_garden()
        Zona.objects.filter(huerto=garden, numero=1).update(nombre="Nombre conservado")
        again = provision_garden()
        self.assertEqual(again.pk, garden.pk)
        self.assertEqual(list(garden.zona_set.order_by("numero").values_list("numero", flat=True)), [1, 2, 3])
        self.assertEqual(garden.zona_set.get(numero=1).nombre, "Nombre conservado")

    def test_provision_atomic_on_failure(self):
        original = Zona.objects.get_or_create
        def third_fails(*args, **kwargs):
            if kwargs.get("numero") == 3:
                raise RuntimeError("Fallo controlado")
            return original(*args, **kwargs)
        with patch.object(Zona.objects, "get_or_create", side_effect=third_fails):
            with self.assertRaises(RuntimeError):
                provision_garden()
        self.assertFalse(Huerto.objects.filter(clave="principal").exists())
        self.assertEqual(Zona.objects.count(), 0)

    def test_zone_range_enforced_in_database(self):
        garden = provision_garden()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Zona.objects.bulk_create([Zona(huerto=garden, numero=4, nombre="Fuera")])

    def test_zone_uniqueness_enforced_in_database(self):
        garden = provision_garden()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Zona.objects.bulk_create([Zona(huerto=garden, numero=1, nombre="Duplicada")])

    def test_zone_cannot_move_even_with_queryset_update(self):
        garden = provision_garden()
        other = Huerto.objects.create(clave="aislado", nombre="Solo pruebas")
        with self.assertRaises(IntegrityError), transaction.atomic():
            garden.zona_set.filter(numero=1).update(huerto=other)

    def test_zone_number_is_stable_in_database(self):
        garden = Huerto.objects.create(clave="numero-estable", nombre="Solo pruebas")
        zone = Zona.objects.create(huerto=garden, numero=1, nombre="Planta de prueba")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Zona.objects.filter(pk=zone.pk).update(numero=2)

    def test_database_rejects_orphan_zone(self):
        with self.assertRaises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
            Zona.objects.bulk_create([Zona(huerto_id=999999, numero=1, nombre="Huerfana")])
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")

    def test_membership_cannot_move_even_with_queryset_update(self):
        garden = provision_garden()
        member = assign_membership(self.user(), garden)
        other = self.user("otra@example.invalid")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Membresia.objects.filter(pk=member.pk).update(usuario=other)

    def test_membership_unique_even_without_clean(self):
        garden = provision_garden()
        user = self.user()
        assign_membership(user, garden)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Membresia.objects.bulk_create([Membresia(usuario=user, huerto=garden)])

    def test_garden_delete_protected(self):
        garden = provision_garden()
        with self.assertRaises(ProtectedError):
            garden.delete()

    def test_invalid_timezone_rejected(self):
        with self.assertRaises(ValidationError):
            Huerto.objects.create(clave="invalido", nombre="Zona invalida", zona_horaria="no/existe")

    def test_unverified_account_denied_even_with_membership(self):
        garden = provision_garden()
        user = self.user()
        assign_membership(user, garden)
        self.assertFalse(visible_gardens(user).exists())

    def test_verified_account_without_membership_denied(self):
        provision_garden()
        self.assertFalse(visible_gardens(self.user(verified=True)).exists())

    def test_verified_member_allowed_only_for_own_garden(self):
        garden = provision_garden()
        other = Huerto.objects.create(clave="otro", nombre="Aislado de pruebas")
        user = self.user(verified=True)
        assign_membership(user, garden)
        self.assertEqual(require_garden(user, garden.pk), garden)
        with self.assertRaises(PermissionDenied):
            require_garden(user, other.pk)

    def test_inactive_account_or_membership_denied(self):
        garden = provision_garden()
        user = self.user(verified=True)
        assign_membership(user, garden, active=False)
        self.assertFalse(visible_gardens(user).exists())
        assign_membership(user, garden, active=True)
        user.is_active = False
        self.assertFalse(visible_gardens(user).exists())

    def test_staff_has_no_automatic_garden_permission(self):
        provision_garden()
        self.assertFalse(visible_gardens(self.user(verified=True, is_staff=True)).exists())

    def test_anonymous_denied(self):
        provision_garden()
        self.assertFalse(visible_gardens(AnonymousUser()).exists())

    def test_verification_authority_is_allauth(self):
        garden = provision_garden()
        user = self.user(verified=True)
        assign_membership(user, garden)
        EmailAddress.objects.filter(user=user).update(verified=False)
        self.assertFalse(visible_gardens(user).exists())

    def test_app_cannot_create_schema_objects(self):
        with self.assertRaises(ProgrammingError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("CREATE TABLE chilito_forbidden_test(id integer)")

    def test_app_cannot_alter_tables(self):
        with self.assertRaises(ProgrammingError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("ALTER TABLE huerto_zona ADD COLUMN chilito_forbidden integer")

    def test_app_is_not_administrative(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user")
            self.assertEqual(cursor.fetchone(), (False, False, False, False))

class FrontendPreservationTests(SimpleTestCase):
    def test_same_index_served_without_copy_or_rewrite(self):
        from config.views import DIST
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), (DIST / "index.html").read_bytes())

    def test_existing_css_and_favicon_served(self):
        for path in ["/vista/css/aplicacion.css", "/favicon.svg"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_no_backend_files_or_traversal_exposed(self):
        for path in ["/compose.yaml", "/backend/config/settings/local.py",
                     "/vista/../../compose.yaml", "/desarrollo/inicio.js"]:
            self.assertEqual(self.client.get(path).status_code, 404)
