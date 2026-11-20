"""Reglas de administrador y soporte. Los flujos completos: tools/probar_mfa.py."""
from io import StringIO

from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, SimpleTestCase, TestCase

from cuentas.adapters import AdaptadorMFA
from datos import services as s
from datos.models import Auditoria
from tests import cuenta, publicar_textos


class AdministradorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        self.admin = cuenta('admin@example.test', 'gestionar_guias', factor=False)

    def navegador(self):
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.admin, backend='django.contrib.auth.backends.ModelBackend')
        return c

    def test_sin_metodo_el_servicio_lo_rechaza(self):
        with self.assertRaises(s.FactorRequerido):
            s.require_cap(self.admin, 'gestionar_guias')

    def test_sin_metodo_el_panel_responde_403_especifico(self):
        r = self.navegador().get('/api/admin/guias')
        self.assertEqual((r.status_code, r.json()['code']), (403, 'mfa-required'))

    def test_sin_metodo_puede_entrar_a_su_cuenta(self):
        r = self.navegador().get('/api/cuenta')
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.json()['mfaRequired'], True)

    def test_codigos_de_recuperacion_no_bastan(self):
        Authenticator.objects.create(user=self.admin, type='recovery_codes', data={})
        with self.assertRaises(s.FactorRequerido):
            s.require_cap(self.admin, 'gestionar_guias')

    def test_totp_y_webauthn_si_bastan(self):
        for tipo in ('totp', 'webauthn'):
            Authenticator.objects.all().delete()
            Authenticator.objects.create(user=self.admin, type=tipo, data={})
            self.assertEqual(self.navegador().get('/api/admin/guias').status_code, 200, tipo)
            self.assertIs(s.session_contract(self.admin)['mfaRequired'], False)

    def test_usuario_normal_no_necesita_factor_fuerte(self):
        self.assertIs(s.session_contract(cuenta('ana@example.test'))['mfaRequired'], False)

    def test_la_base_no_admite_privilegios_de_django(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.filter(pk=self.admin.pk).update(is_staff=True)


class SoporteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        self.cuenta = cuenta('ana@example.test', factor=True)
        self.operador = cuenta('soporte@example.test', 'gestionar_administradores')

    def retirar(self, *extra, correo='ana@example.test', operador='soporte@example.test', caso=('--caso', 'CS-0001A2B3')):
        call_command('retirar_factores', correo, '--operador', operador, *caso, *extra, stdout=StringIO())

    def test_exige_declarar_la_verificacion(self):
        with self.assertRaises(CommandError):
            self.retirar()
        self.assertTrue(Authenticator.objects.filter(user=self.cuenta).exists())

    def test_retira_y_audita(self):
        self.retirar('--identidad-verificada')
        self.assertFalse(Authenticator.objects.filter(user=self.cuenta).exists())
        registro = Auditoria.objects.get(accion='retirar_segundo_factor')
        self.assertEqual((registro.actor, registro.entidad_id), (self.operador, str(self.cuenta.pk)))
        self.assertEqual(registro.detalle, {'caso': 'CS-0001A2B3'}, 'el folio del caso queda en la auditoría')

    def test_nadie_atiende_su_propia_cuenta(self):
        with self.assertRaises(CommandError):
            self.retirar('--identidad-verificada', operador='ana@example.test')

    # B-9: el operador debe poder responder por el retiro, con caso y doble confirmación si la cuenta administra.
    def test_operador_sin_capacidad_o_sin_factor_no_puede(self):
        cuenta('cualquiera@example.test')
        cuenta('sin-factor@example.test', 'gestionar_administradores', factor=False)
        for operador in ('cualquiera@example.test', 'sin-factor@example.test'):
            with self.subTest(operador=operador), self.assertRaises(CommandError):
                self.retirar('--identidad-verificada', operador=operador)
        self.assertTrue(Authenticator.objects.filter(user=self.cuenta).exists())
        self.assertFalse(Auditoria.objects.filter(accion='retirar_segundo_factor').exists())

    def test_exige_folio_del_caso(self):
        for caso in ((), ('--caso', ''), ('--caso', 'x')):
            with self.subTest(caso=caso), self.assertRaises(CommandError):
                self.retirar('--identidad-verificada', caso=caso)
        self.assertTrue(Authenticator.objects.filter(user=self.cuenta).exists())

    def test_cuenta_con_capacidades_pide_confirmar_el_correo(self):
        jefa = cuenta('jefa@example.test', 'gestionar_guias')
        with self.assertRaises(CommandError):
            self.retirar('--identidad-verificada', correo='jefa@example.test')
        self.assertTrue(Authenticator.objects.filter(user=jefa).exists())
        self.retirar('--identidad-verificada', '--confirmar', 'jefa@example.test', correo='jefa@example.test')
        self.assertFalse(Authenticator.objects.filter(user=jefa).exists())

    def test_sin_metodos_no_audita(self):
        self.retirar('--identidad-verificada')
        with self.assertRaises(CommandError):
            self.retirar('--identidad-verificada')
        self.assertEqual(Auditoria.objects.filter(accion='retirar_segundo_factor').count(), 1)


class CifradoTests(SimpleTestCase):
    def test_ida_y_vuelta_sin_texto_claro(self):
        adaptador = AdaptadorMFA()
        cifrado = adaptador.encrypt('SECRETO')
        self.assertNotIn('SECRETO', cifrado)
        self.assertEqual(adaptador.decrypt(cifrado), 'SECRETO')
