"""Stage 3: current-garden permissions and persisted notices, only in the isolated database."""
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError, transaction
from django.test import Client, TestCase
from django.utils import timezone
from allauth.account.models import EmailAddress
from huerto.models import Huerto, Zona, Membresia, Aviso, AvisoLeido
from huerto.services import provision_garden, assign_membership

BASE="/api/huertos/actual"

class GardenIntegrationTests(TestCase):
    def setUp(self):
        self.garden=provision_garden()
        self.user=get_user_model().objects.create_user("garden@example.invalid")
        EmailAddress.objects.create(user=self.user,email=self.user.email,verified=True,primary=True)
        self.client=Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.client.get("/api/acceso/configuracion")

    def member(self):
        return assign_membership(self.user,self.garden)

    def notice(self, **values):
        data={"huerto":self.garden,"severidad":"advertencia","titulo":"Aviso aislado",
              "descripcion":"Contenido de prueba aislada.","recomendacion":"","creado_en":timezone.now()}
        data.update(values)
        return Aviso.objects.create(**data)

    def read(self, notice_id, body=None, client=None):
        client=client or self.client
        return client.put(BASE+f"/avisos/{notice_id}/lectura",body if body is not None else {},
                          content_type="application/json",HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)

    def test_anonymous_endpoints_denied(self):
        anonymous=Client()
        for path in [BASE,BASE+"/avisos",BASE+"/avisos/1"]:
            self.assertEqual(anonymous.get(path).status_code,401)
        anonymous.get("/api/acceso/configuracion")
        self.assertEqual(self.read("1",client=anonymous).status_code,401)

    def test_unverified_account_denied_even_with_membership(self):
        self.member()
        EmailAddress.objects.filter(user=self.user).update(verified=False)
        for path in [BASE,BASE+"/avisos",BASE+"/avisos/1"]:
            response=self.client.get(path)
            self.assertEqual(response.status_code,403)
            self.assertEqual(response.json()["code"],"verification-required")
        self.assertEqual(self.read("1").status_code,403)

    def test_no_membership_discloses_neither_garden_nor_notices(self):
        notice=self.notice()
        for path in [BASE,BASE+"/avisos",BASE+f"/avisos/{notice.pk}"]:
            response=self.client.get(path)
            self.assertEqual(response.status_code,403)
            self.assertEqual(response.json(),{"status":403,"code":"garden-unassigned"})
        self.assertEqual(self.read(str(notice.pk)).status_code,403)
        self.assertFalse(AvisoLeido.objects.exists())

    def test_revoked_membership_denies_existing_session_and_mutation(self):
        member=self.member()
        notice=self.notice()
        self.assertEqual(self.client.get(BASE).status_code,200)
        member.activa=False
        member.save()
        self.assertEqual(self.client.get(BASE).status_code,403)
        self.assertEqual(self.client.get(BASE+"/avisos").status_code,403)
        self.assertEqual(self.read(str(notice.pk)).status_code,403)

    def test_inactive_account_denied(self):
        self.member()
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.client.get(BASE).status_code,401)

    def test_garden_projects_persisted_names_and_no_physical_readings(self):
        self.member()
        self.garden.nombre="Nombre conservado del huerto"
        self.garden.save()
        zone=self.garden.zona_set.get(numero=2)
        zone.nombre="Nombre conservado de la planta"
        zone.save()
        response=self.client.get(BASE+"?huerto=999&user=999")
        self.assertEqual(response.status_code,200)
        body=response.json()
        self.assertEqual(body["status"],"waiting")
        self.assertEqual(body["name"],self.garden.nombre)
        self.assertEqual(body["plants"][1]["name"],zone.nombre)
        self.assertEqual([plant["id"] for plant in body["plants"]],[1,2,3])
        readings=[plant["reading"] for plant in body["plants"]]+[body["temperature"],body["humidity"]]
        self.assertTrue(all(reading=={"value":None,"quality":"missing","at":None} for reading in readings))
        self.assertIsNone(body["updatedAt"])
        self.assertEqual(body["tank"],{"state":"unknown","at":None})
        self.assertNotIn("deviceLastSeen",body)
        self.assertTrue("no-store" in response["Cache-Control"])

    def test_missing_zone_is_configuration_error_not_waiting_or_fake_zone(self):
        self.member()
        self.garden.zona_set.get(numero=3).delete()
        response=self.client.get(BASE)
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()["code"],"garden-configuration-unavailable")

    def test_other_garden_membership_does_not_select_another_current_garden(self):
        other=Huerto.objects.create(clave="otro",nombre="Huerto ajeno")
        assign_membership(self.user,other)
        self.assertEqual(self.client.get(BASE).status_code,403)
        self.assertFalse(self.client.get("/api/cuenta").json()["gardenAssigned"])

    def test_empty_notices_are_valid_and_no_alert_is_created(self):
        self.member()
        response=self.client.get(BASE+"/avisos")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),{"status":"ready","items":[]})
        self.assertEqual(Aviso.objects.count(),0)
        self.assertEqual(AvisoLeido.objects.count(),0)

    def test_database_failure_is_not_successful_empty_collection(self):
        self.member()
        with patch("huerto.api.notice_list",side_effect=DatabaseError):
            response=self.client.get(BASE+"/avisos")
        self.assertEqual(response.status_code,503)
        self.assertNotIn("items",response.json())

    def test_notices_have_stable_order_and_explicit_severity_mapping(self):
        self.member()
        at=timezone.now()
        first=self.notice(severidad="informacion",creado_en=at)
        second=self.notice(severidad="critico",creado_en=at)
        items=self.client.get(BASE+"/avisos").json()["items"]
        self.assertEqual([item["id"] for item in items],[str(second.pk),str(first.pk)])
        self.assertEqual([item["importance"] for item in items],["high","info"])
        self.assertTrue(all(item["read"] is False for item in items))

    def test_foreign_notice_is_neutral_not_found_and_never_marked(self):
        self.member()
        other=Huerto.objects.create(clave="ajeno",nombre="Nombre privado")
        foreign=self.notice(huerto=other,titulo="Contenido privado")
        missing=self.client.get(BASE+"/avisos/999999999")
        response=self.client.get(BASE+f"/avisos/{foreign.pk}")
        self.assertEqual(response.status_code,404)
        self.assertEqual(response.json(),missing.json())
        self.assertEqual(self.read(str(foreign.pk)).status_code,404)
        self.assertEqual(self.client.get(BASE+"/avisos").json()["items"],[])
        self.assertFalse(AvisoLeido.objects.exists())

    def test_invalid_ids_are_neutral_not_found(self):
        self.member()
        for value in ["-1","0","abc","01","999999999999999999999999999","9223372036854775808"]:
            self.assertEqual(self.client.get(BASE+f"/avisos/{value}").status_code,404)
            self.assertEqual(self.read(value).status_code,404)

    def test_mark_read_is_persisted_idempotent_and_does_not_resolve_notice(self):
        self.member()
        notice=self.notice()
        first=self.read(str(notice.pk))
        second=self.read(str(notice.pk))
        self.assertEqual(first.status_code,200)
        self.assertEqual(second.status_code,200)
        self.assertEqual(first.json()["readAt"],second.json()["readAt"])
        self.assertEqual(AvisoLeido.objects.filter(aviso=notice,usuario=self.user).count(),1)
        self.assertEqual(self.client.get(BASE+f"/avisos/{notice.pk}").json()["item"]["read"],True)
        notice.refresh_from_db()
        self.assertIsNone(notice.resuelto_en)
        self.assertEqual(second.json()["item"]["condition"],"active")

    def test_read_state_is_per_user_and_profile_stays_own(self):
        self.member()
        notice=self.notice()
        self.read(str(notice.pk))
        other=get_user_model().objects.create_user("other-garden@example.invalid")
        EmailAddress.objects.create(user=other,email=other.email,verified=True,primary=True)
        assign_membership(other,self.garden)
        self.client.force_login(other)
        self.assertFalse(self.client.get(BASE+f"/avisos/{notice.pk}").json()["item"]["read"])
        self.assertEqual(self.client.get("/api/cuenta?user="+str(self.user.pk)).json()["email"],other.email)

    def test_read_cannot_choose_another_user(self):
        self.member()
        notice=self.notice()
        response=self.read(str(notice.pk),{"usuario":999})
        self.assertEqual(response.status_code,400)
        self.assertFalse(AvisoLeido.objects.exists())

    def test_read_requires_csrf_and_put_not_get(self):
        self.member()
        notice=self.notice()
        self.assertEqual(self.client.put(BASE+f"/avisos/{notice.pk}/lectura",{},content_type="application/json").status_code,403)
        self.assertEqual(self.client.get(BASE+f"/avisos/{notice.pk}/lectura").status_code,405)
        self.assertFalse(AvisoLeido.objects.exists())

    def test_resolved_notice_uses_recorded_resolution_not_read_date(self):
        self.member()
        at=timezone.now()-timedelta(hours=1)
        resolved=at+timedelta(minutes=20)
        notice=self.notice(creado_en=at,resuelto_en=resolved)
        result=self.read(str(notice.pk)).json()["item"]
        self.assertEqual(result["condition"],"resolved")
        self.assertEqual(result["resolvedAt"],resolved.isoformat())

    def test_zone_from_another_garden_rejected_even_bypassing_model_clean(self):
        other=Huerto.objects.create(clave="other",nombre="Otro")
        zone=Zona.objects.create(huerto=other,numero=1,nombre="Zona ajena")
        with self.assertRaises(ValidationError):
            self.notice(zona=zone)
        with self.assertRaises(IntegrityError),transaction.atomic():
            Aviso.objects.bulk_create([Aviso(huerto=self.garden,zona=zone,severidad="informacion",
                titulo="Aviso aislado",descripcion="Texto",creado_en=timezone.now())])

    def test_notice_cannot_move_garden_after_recording_even_by_update(self):
        notice=self.notice()
        other=Huerto.objects.create(clave="otro",nombre="Otro")
        with self.assertRaises(IntegrityError),transaction.atomic():
            Aviso.objects.filter(pk=notice.pk).update(huerto=other)

    def test_read_receipt_cannot_be_reassigned(self):
        self.member()
        first=self.notice()
        second=self.notice()
        self.read(str(first.pk))
        with self.assertRaises(IntegrityError),transaction.atomic():
            AvisoLeido.objects.filter(aviso=first).update(aviso=second)

    def test_database_rejects_invalid_severity_and_reversed_dates(self):
        notice=self.notice()
        for values in [{"severidad":"inventada"},{"resuelto_en":notice.creado_en-timedelta(seconds=1)}]:
            with self.assertRaises(IntegrityError),transaction.atomic():
                Aviso.objects.filter(pk=notice.pk).update(**values)

    def test_unique_receipt_even_when_bypassing_model_validation(self):
        notice=self.notice()
        at=timezone.now()
        AvisoLeido.objects.create(aviso=notice,usuario=self.user,leido_en=at)
        with self.assertRaises(IntegrityError),transaction.atomic():
            AvisoLeido.objects.bulk_create([AvisoLeido(aviso=notice,usuario=self.user,leido_en=at)])

    def test_app_cannot_alter_new_tables(self):
        from django.db import connection,ProgrammingError
        with self.assertRaises(ProgrammingError),transaction.atomic(),connection.cursor() as cursor:
            cursor.execute("ALTER TABLE huerto_aviso ADD COLUMN chilito_prohibido integer")
