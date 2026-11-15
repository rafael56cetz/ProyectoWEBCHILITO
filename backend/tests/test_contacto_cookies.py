"""Pregunta sobre el producto y permanencia de la decisión de cookies."""
import json

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from datos.models import AvisoCorreo, ConsultaProducto
from privacidad import services


def enviar(cliente, ruta, datos):
    return cliente.post(ruta, json.dumps(datos), content_type='application/json',
                        HTTP_X_CSRFTOKEN=cliente.cookies['csrftoken'].value)


def cliente_con_csrf():
    cliente = Client(enforce_csrf_checks=True)
    cliente.get('/api/acceso/configuracion')
    if 'csrftoken' not in cliente.cookies:
        cliente.cookies['csrftoken'] = 'a' * 64
    return cliente


@override_settings(CHILITO_CONTACTO_SOPORTE='soporte@example.test')
class ContactoProducto(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = cliente_con_csrf()
        self.valido = {'name': 'Ana', 'email': 'ana@example.test', 'message': '¿Cuánto costará?\nGracias.'}

    def enviar(self, datos):
        # El aviso sale al confirmar la transacción: aquí se ejecuta como en producción.
        with self.captureOnCommitCallbacks(execute=True):
            return enviar(self.cliente, '/api/contacto', datos)

    def test_entrega_a_soporte_con_respuesta_a_la_persona(self):
        respuesta = self.enviar(self.valido)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(mail.outbox[0].to, ['soporte@example.test'])
        self.assertEqual(mail.outbox[0].reply_to, ['ana@example.test'])
        self.assertIn('¿Cuánto costará?', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].subject, '[El Chilito] Pregunta sobre el producto')
        consulta = ConsultaProducto.objects.get()
        self.assertEqual((consulta.estado, consulta.correo), ('nueva', 'ana@example.test'))
        self.assertEqual(AvisoCorreo.objects.get(consulta=consulta).estado, 'aceptado_smtp')

    def test_repetir_la_misma_consulta_no_duplica(self):
        for _ in range(3):
            self.assertEqual(self.enviar(self.valido).status_code, 200)
        self.assertEqual(ConsultaProducto.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_nombre_es_opcional(self):
        datos = {'email': 'ana@example.test', 'message': 'Hola'}
        self.assertEqual(self.enviar(datos).status_code, 200)
        self.assertIn('Sin indicar', mail.outbox[0].body)

    def test_rechaza_entradas_no_validas(self):
        for cambio in ({'email': 'no-es-correo'}, {'email': 'a@b.test\nBcc: c@d.test'}, {'message': '  '},
                       {'message': 'x' * 2001}, {'name': 'x' * 101}, {'name': 'a\nb'}, {'extra': 1}):
            with self.subTest(cambio=list(cambio)):
                cache.clear()  # La cuota se prueba aparte: aquí importa la validación.
                self.assertEqual(self.enviar({**self.valido, **cambio}).status_code, 400)
        self.assertEqual(mail.outbox, [])

    def test_campo_trampa_no_envia_ni_lo_revela(self):
        respuesta = self.enviar({**self.valido, 'website': 'http://x.test'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(mail.outbox, [])

    def test_exige_csrf(self):
        respuesta = self.cliente.post('/api/contacto', json.dumps(self.valido), content_type='application/json')
        self.assertEqual(respuesta.status_code, 403)

    def test_cuota(self):
        estados = [self.enviar({**self.valido, 'message': f'Pregunta {n}'}).status_code for n in range(6)]
        self.assertEqual(estados[-1], 429)
        self.assertEqual(len(mail.outbox), 5)

    @override_settings(CHILITO_CONTACTO_SOPORTE='')
    def test_sin_destino_conserva_la_consulta_y_el_aviso_queda_fallido(self):
        self.assertEqual(self.enviar(self.valido).status_code, 200)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(AvisoCorreo.objects.get(consulta=ConsultaProducto.objects.get()).estado, 'fallido')


class CookiesPermanecen(TestCase):
    def cuenta(self, correo):
        usuario = get_user_model().objects.create_user(correo, 'huerto-claro-de-prueba-01')
        EmailAddress.objects.create(user=usuario, email=correo, primary=True, verified=True)
        return usuario

    def test_la_decision_sobrevive_al_cierre_de_sesion(self):
        usuario = self.cuenta('a@example.test')
        valor = services.decidir_cookies(usuario, None, True)
        estado = services.estado_cookies(valor, None)
        self.assertTrue(estado['decided'] and estado['statistics'])
        self.assertTrue(services.contar_seccion(None, valor, 'identificador', 'inicio'))

    def test_otra_cuenta_no_hereda_la_autorizacion(self):
        valor = services.decidir_cookies(self.cuenta('a@example.test'), None, True)
        otra = self.cuenta('b@example.test')
        self.assertFalse(services.estado_cookies(valor, otra)['decided'])
        self.assertFalse(services.contar_seccion(otra, valor, 'identificador', 'inicio'))

    def test_sin_sesion_se_puede_cambiar_sin_tocar_la_decision_de_la_cuenta(self):
        usuario = self.cuenta('a@example.test')
        valor = services.decidir_cookies(usuario, None, True)
        nuevo = services.decidir_cookies(None, valor, False)
        self.assertFalse(services.estado_cookies(nuevo, None)['statistics'])
        self.assertTrue(services.estado_cookies(valor, usuario)['statistics'])
