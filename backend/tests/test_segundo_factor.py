"""Reglas de administrador y soporte. Los flujos completos: tools/probar_mfa.py."""
from io import StringIO

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, SimpleTestCase, TestCase

from cuentas.adapters import AdaptadorMFA
from datos import services as s
from datos.models import Auditoria


def cuenta(email, *capacidades):
    u = get_user_model().objects.create(email=email, password='x')
    EmailAddress.objects.create(user=u, email=email, verified=True, primary=True)
    u.user_permissions.add(*Permission.objects.filter(content_type__app_label='datos', codename__in=capacidades))
    return u


class AdministradorTests(TestCase):
    def setUp(self):
        self.admin = cuenta('admin@example.test', 'ver_flota')

    def navegador(self):
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.admin, backend='django.contrib.auth.backends.ModelBackend')
        return c

    def test_sin_metodo_el_servicio_lo_rechaza(self):
        with self.assertRaises(s.FactorRequerido):
            s.fleet_projection(self.admin)

    def test_sin_metodo_el_panel_responde_403_especifico(self):
        r = self.navegador().get('/api/admin/flota')
        self.assertEqual((r.status_code, r.json()['code']), (403, 'mfa-required'))

    def test_sin_metodo_puede_entrar_a_su_cuenta(self):
        r = self.navegador().get('/api/cuenta')
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.json()['mfaRequired'], True)

    def test_codigos_de_recuperacion_no_bastan(self):
        Authenticator.objects.create(user=self.admin, type='recovery_codes', data={})
        with self.assertRaises(s.FactorRequerido):
            s.fleet_projection(self.admin)

    def test_totp_y_webauthn_si_bastan(self):
        for tipo in ('totp', 'webauthn'):
            Authenticator.objects.all().delete()
            Authenticator.objects.create(user=self.admin, type=tipo, data={})
            self.assertEqual(self.navegador().get('/api/admin/flota').status_code, 200, tipo)
            self.assertIs(s.session_contract(self.admin)['mfaRequired'], False)

    def test_usuario_normal_no_necesita_factor_fuerte(self):
        self.assertIs(s.session_contract(cuenta('ana@example.test'))['mfaRequired'], False)

    def test_is_staff_no_exime(self):
        get_user_model().objects.filter(pk=self.admin.pk).update(is_staff=True, is_superuser=True)
        with self.assertRaises(s.FactorRequerido):
            s.fleet_projection(get_user_model().objects.get(pk=self.admin.pk))


class SoporteTests(TestCase):
    def setUp(self):
        self.cuenta = cuenta('ana@example.test')
        self.operador = cuenta('soporte@example.test')
        Authenticator.objects.create(user=self.cuenta, type='totp', data={})

    def retirar(self, *extra):
        call_command('retirar_factores', 'ana@example.test', '--operador', 'soporte@example.test', *extra, stdout=StringIO())

    def test_exige_declarar_la_verificacion(self):
        with self.assertRaises(CommandError):
            self.retirar()
        self.assertTrue(Authenticator.objects.filter(user=self.cuenta).exists())

    def test_retira_y_audita(self):
        self.retirar('--identidad-verificada')
        self.assertFalse(Authenticator.objects.filter(user=self.cuenta).exists())
        self.assertEqual(Auditoria.objects.get(accion='mfa-reset').actor, self.operador)

    def test_nadie_atiende_su_propia_cuenta(self):
        with self.assertRaises(CommandError):
            call_command('retirar_factores', 'ana@example.test', '--operador', 'ana@example.test', '--identidad-verificada')


class CifradoTests(SimpleTestCase):
    def test_ida_y_vuelta_sin_texto_claro(self):
        adaptador = AdaptadorMFA()
        cifrado = adaptador.encrypt('SECRETO')
        self.assertNotIn('SECRETO', cifrado)
        self.assertEqual(adaptador.decrypt(cifrado), 'SECRETO')
