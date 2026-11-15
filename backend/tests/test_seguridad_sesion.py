"""Lógica de la Fase 3 sin base. Los flujos reales están en tools/probar_seguridad.py."""
import logging
import sys
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase

from config.registro import FormatoSeguro
from cuentas.adapters import ClosedRegistrationAdapter
from cuentas.email import MailUnavailable
from web import sesion

AHORA = 1_000_000
HORA8 = 28800


class VencimientoTests(SimpleTestCase):
    def vencida(self, edad, inactiva, admin=False):
        return sesion.vencida(AHORA, AHORA - edad, AHORA - inactiva, lambda: admin)

    def test_vigente_dentro_de_los_limites(self):
        self.assertFalse(self.vencida(HORA8 - 1, 899))

    def test_vida_absoluta_no_se_renueva_con_actividad(self):
        self.assertTrue(self.vencida(HORA8, 0))

    def test_inactividad_de_usuario(self):
        self.assertFalse(self.vencida(3600, 1799))
        self.assertTrue(self.vencida(3600, 1800))

    def test_inactividad_de_administrador(self):
        self.assertFalse(self.vencida(3600, 899, admin=True))
        self.assertTrue(self.vencida(3600, 900, admin=True))

    def test_usuario_no_cae_a_los_15_minutos(self):
        self.assertFalse(self.vencida(3600, 900, admin=False))

    def test_sin_marcas_validas_vence(self):
        for inicio, visto in [(None, None), (AHORA, None), ('1', AHORA)]:
            self.assertTrue(sesion.vencida(AHORA, inicio, visto, lambda: False))

    def test_solo_consulta_el_rol_si_hace_falta(self):
        consulta = MagicMock(return_value=True)
        sesion.vencida(AHORA, AHORA - 60, AHORA - 60, consulta)
        consulta.assert_not_called()

    def test_valores_acordados(self):
        self.assertEqual((settings.CHILITO_SESION_ABSOLUTA, settings.CHILITO_INACTIVIDAD_USUARIO,
                          settings.CHILITO_INACTIVIDAD_ADMIN, settings.PASSWORD_RESET_TIMEOUT),
                         (28800, 1800, 900, 600))


class MiddlewareTests(SimpleTestCase):
    def peticion(self, ruta='/api/huertos/actual', edad_visto=120, **extra):
        request = RequestFactory().get(ruta, **extra)
        request.session = {sesion.INICIO: 10_000_000 - 600, sesion.VISTO: 10_000_000 - edad_visto}
        request.user = MagicMock(is_authenticated=True)
        return request

    def atender(self, request):
        with patch('web.sesion.time.time', return_value=10_000_000):
            sesion.SesionAcotada(lambda r: 'respuesta')(request)
        return request.session[sesion.VISTO]

    def test_actividad_renueva(self):
        self.assertEqual(self.atender(self.peticion()), 10_000_000)

    def test_actividad_reciente_no_escribe_en_cada_peticion(self):
        self.assertEqual(self.atender(self.peticion(edad_visto=30)), 10_000_000 - 30)

    def test_consulta_de_sesion_no_renueva(self):
        self.assertEqual(self.atender(self.peticion(sesion.CONSULTA_DE_SESION)), 10_000_000 - 120)

    def test_sondeo_marcado_no_renueva(self):
        self.assertEqual(self.atender(self.peticion('/api/cuenta', HTTP_X_CHILITO_SONDEO='1')), 10_000_000 - 120)

    def test_estaticos_no_cuentan(self):
        self.assertEqual(self.atender(self.peticion('/vistas/estilos/site.css')), 10_000_000 - 120)

    def test_al_vencer_cierra_sesion_tecnica_y_web(self):
        request = self.peticion(edad_visto=2000)
        with patch('web.sesion.services') as servicios, patch('web.sesion.logout') as salir:
            servicios.is_admin.return_value = False
            self.atender(request)
        servicios.close_actor_sessions.assert_called_once_with(request.user, 'expiry')
        salir.assert_called_once_with(request)


class ContrasenaTests(SimpleTestCase):
    def test_guarda_solo_la_columna_de_contrasena(self):
        usuario = MagicMock()
        ClosedRegistrationAdapter().set_password(usuario, 'x' * 20)
        usuario.save.assert_called_once_with(update_fields=['password'])

    def test_aviso_fallido_no_oculta_el_guardado(self):
        with patch('allauth.account.adapter.DefaultAccountAdapter.send_notification_mail', side_effect=MailUnavailable):
            ClosedRegistrationAdapter().send_notification_mail('plantilla', MagicMock())


class RegistroTests(SimpleTestCase):
    def test_el_log_no_incluye_el_texto_de_la_excepcion(self):
        correo = '@'.join(['persona', 'example.test'])
        try:
            raise ValueError(f'Key (email)=({correo}) already exists')
        except ValueError:
            registro = logging.LogRecord('x', logging.ERROR, __file__, 1, 'fallo', (), sys.exc_info())
        salida = FormatoSeguro('%(message)s').format(registro)
        self.assertIn('ValueError', salida)
        self.assertNotIn(correo, salida)
