"""Soporte resuelto, avisos por correo y buzón de consultas, en la capa que autoriza.

Base PostgreSQL temporal con nombre verificado y correo en memoria: no se envía nada real.
Los tokens se generan en memoria y se comprueba que no aparecen en ningún aviso.
"""
import secrets
from smtplib import SMTPException
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase, override_settings

from datos import avisos_correo, services
from datos.models import (AvisoCorreo, CasoSoporte, ConsultaProducto, Dispositivo, PermisoSoporte,
                          ResolucionSoporte)
from huerto.models import Huerto, Membresia


@override_settings(CHILITO_CONTACTO_SOPORTE='soporte@example.test', ORIGIN='https://chilito.example.test')
class SoporteYBuzonTests(TransactionTestCase):
    def setUp(self):
        if not str(connection.settings_dict['NAME']).startswith('test_chilito_integracion_sinteticos'):
            raise RuntimeError('Solo en la base temporal de pruebas.')
        self.owner = self.make_user('soporte-dueno@example.test')
        self.admin = self.make_user('soporte-admin@example.test')
        self.buzon = self.make_user('buzon-admin@example.test')
        self.root = self.make_user('soporte-root@example.test', is_staff=True, is_superuser=True)
        self.garden = Huerto.objects.create(clave='soporte-a', nombre='Huerto sintético')
        Membresia.objects.create(usuario=self.owner, huerto=self.garden)
        Dispositivo.objects.create(huerto=self.garden, identificador='soporte-device-a')
        self.grant(self.admin, 'atender_soporte')
        self.grant(self.buzon, 'atender_consultas')
        Authenticator.objects.get_or_create(user=self.root, type='totp', defaults={'data': {}})

    def make_user(self, email, **fields):
        user = get_user_model().objects.create_user(email, secrets.token_urlsafe(24), **fields)
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
        return user

    def grant(self, actor, *codes):
        actor.user_permissions.add(*Permission.objects.filter(content_type__app_label='datos', codename__in=codes))
        Authenticator.objects.get_or_create(user=actor, type='totp', defaults={'data': {}})

    def issue(self):
        return services.issue_support(self.owner, self.garden.pk, 'connection', True)['permission']

    # Soporte -------------------------------------------------------------------------------
    def test_caso_nuevo_avisa_a_soporte_con_folio_y_enlace_sin_token(self):
        permission = self.issue()
        self.assertTrue(permission['folio'].startswith('CS-'))
        self.assertEqual(permission['supportEmail'], 'soporte@example.test')
        aviso = AvisoCorreo.objects.get(tipo='caso_nuevo')
        self.assertEqual(aviso.estado, 'aceptado_smtp')
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, ['soporte@example.test'])
        self.assertEqual(mensaje.subject, f"[El Chilito] Nuevo caso de soporte {permission['folio']}")
        self.assertIn('https://chilito.example.test/index.html#admin/soporte', mensaje.body)
        self.assertNotIn(permission['token'], mensaje.subject + mensaje.body)

    def test_solicitar_token_avisa_a_la_persona_una_vez_y_sin_secreto(self):
        permission = self.issue()
        primero = services.request_support_token(self.admin, permission['ticket'])
        segundo = services.request_support_token(self.admin, permission['ticket'])
        self.assertEqual((primero['repeated'], segundo['repeated']), (False, True))
        self.assertEqual(AvisoCorreo.objects.filter(tipo='token_solicitado').count(), 1)
        aviso = [m for m in mail.outbox if 'solicita el token' in m.subject]
        self.assertEqual(len(aviso), 1)
        self.assertEqual(aviso[0].to, ['soporte-dueno@example.test'])
        self.assertNotIn(permission['token'], aviso[0].subject + aviso[0].body)
        self.assertIn('#soporte', aviso[0].body)

    def test_resolver_exige_capacidad_y_no_basta_superusuario(self):
        permission = self.issue()
        for actor in (self.root, self.buzon, self.owner):
            with self.subTest(actor=actor.email), self.assertRaises(PermissionDenied):
                services.resolve_case(actor, permission['ticket'], 'solucionado')
        self.assertFalse(ResolucionSoporte.objects.exists())

    def test_resolver_revoca_cierra_y_el_mismo_token_no_reabre(self):
        permission = self.issue()
        session = services.open_technical(self.admin, permission['ticket'], permission['token'])
        services.resolve_case(self.admin, permission['ticket'], 'solucionado', 'Conexión restablecida.')
        self.assertIsNotNone(PermisoSoporte.objects.get(caso_id=permission['ticket']).revocado_en)
        session.refresh_from_db()
        self.assertEqual(session.motivo_cierre, 'resolved')
        with self.assertRaises(PermissionDenied):
            services.open_technical(self.admin, permission['ticket'], permission['token'])
        dto = services.case_dto(CasoSoporte.objects.get(pk=permission['ticket']))
        self.assertEqual((dto['caseState'], dto['resolution']['result']), ('resolved', 'solucionado'))
        with self.assertRaises(services.RegistroDesactualizado):
            services.resolve_case(self.admin, permission['ticket'], 'sin_falla')
        with self.assertRaises(services.RegistroDesactualizado):
            services.request_support_token(self.admin, permission['ticket'])

    def test_revocar_o_vencer_no_es_resolver(self):
        permission = self.issue()
        services.revoke_support(self.owner, permission['ticket'])
        dto = services.case_dto(CasoSoporte.objects.get(pk=permission['ticket']))
        self.assertEqual((dto['permissionState'], dto['caseState']), ('revoked', 'open'))

    def test_resultado_otro_exige_nota_y_la_resolucion_es_inmutable(self):
        permission = self.issue()
        with self.assertRaises(ValidationError):
            services.resolve_case(self.admin, permission['ticket'], 'otro', '   ')
        with self.assertRaises(ValidationError):
            services.resolve_case(self.admin, permission['ticket'], 'inventado')
        resolution = services.resolve_case(self.admin, permission['ticket'], 'otro', 'Se cambió el router.')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResolucionSoporte.objects.filter(pk=resolution.pk).update(resultado='sin_falla')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResolucionSoporte.objects.filter(pk=resolution.pk).delete()

    def test_fallo_smtp_conserva_el_caso_y_no_se_presenta_como_enviado(self):
        with patch('datos.avisos_correo.EmailMessage.send', side_effect=SMTPException('caido')):
            permission = self.issue()
        self.assertTrue(CasoSoporte.objects.filter(pk=permission['ticket']).exists())
        aviso = AvisoCorreo.objects.get(tipo='caso_nuevo')
        self.assertEqual((aviso.estado, aviso.intentos, aviso.aceptado_en), ('fallido', 1, None))
        AvisoCorreo.objects.filter(pk=aviso.pk).update(ultimo_intento_en=aviso.ultimo_intento_en.replace(year=2000))
        self.assertEqual(avisos_correo.reintentar_pendientes(), 1)
        aviso.refresh_from_db()
        self.assertEqual((aviso.estado, aviso.intentos), ('aceptado_smtp', 2))
        with self.assertRaises(IntegrityError), transaction.atomic():
            AvisoCorreo.objects.filter(pk=aviso.pk).update(estado='pendiente')

    # Buzón de consultas -------------------------------------------------------------------
    def test_consulta_se_guarda_avisa_y_no_se_duplica(self):
        primera = services.record_inquiry('Ana', 'ana@example.test', 'Quiero uno')
        repetida = services.record_inquiry('Ana', 'ANA@example.test', 'Quiero uno ')
        self.assertEqual(primera.pk, repetida.pk)
        self.assertEqual(AvisoCorreo.objects.get(consulta=primera).estado, 'aceptado_smtp')
        self.assertEqual(mail.outbox[0].reply_to, ['ana@example.test'])

    def test_buzon_solo_con_atender_consultas(self):
        services.record_inquiry('', 'bea@example.test', 'Hola')
        for actor in (self.admin, self.root, self.owner):
            with self.subTest(actor=actor.email), self.assertRaises(PermissionDenied):
                list(services.admin_inquiries(actor))
        self.assertEqual(services.admin_inquiries(self.buzon).count(), 1)

    def test_buzon_sin_segundo_factor_no_entra(self):
        Authenticator.objects.filter(user=self.buzon).delete()
        with self.assertRaises(services.FactorRequerido):
            list(services.admin_inquiries(self.buzon))

    def test_atencion_solo_avanza_y_conserva_responsable(self):
        consulta = services.record_inquiry('', 'cris@example.test', 'Precio')
        services.update_inquiry(self.buzon, consulta.pk, 'atendida')
        services.update_inquiry(self.buzon, consulta.pk, 'archivada')
        consulta.refresh_from_db()
        self.assertEqual((consulta.estado, consulta.atendida_por_id), ('archivada', self.buzon.pk))
        with self.assertRaises(services.RegistroDesactualizado):
            services.update_inquiry(self.buzon, consulta.pk, 'nueva')
        # Archivada antes de responderla: puede pasar a atendida, pero nunca volver a nueva.
        services.update_inquiry(self.buzon, consulta.pk, 'atendida')
        consulta.refresh_from_db()
        self.assertEqual(consulta.estado, 'atendida')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConsultaProducto.objects.filter(pk=consulta.pk).update(estado='nueva', atendida_por=None, atendida_en=None)
        sin_responder = services.record_inquiry('', 'dani@example.test', 'Envío')
        services.update_inquiry(self.buzon, sin_responder.pk, 'archivada')
        services.update_inquiry(self.buzon, sin_responder.pk, 'atendida')
        sin_responder.refresh_from_db()
        self.assertEqual((sin_responder.estado, sin_responder.atendida_por_id), ('atendida', self.buzon.pk))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConsultaProducto.objects.filter(pk=consulta.pk).update(mensaje='Alterado')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConsultaProducto.objects.filter(pk=consulta.pk).delete()
