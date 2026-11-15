"""Pregunta sobre el producto, su buzón y permanencia de la decisión de cookies."""
import json

from allauth.mfa.models import Authenticator
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings

from datos import services as datos
from datos.models import ConsultaProducto, CorreoPendiente
from datos.models import Notificacion
from privacidad import services
from privacidad.models import Decision
from tests import cuenta, publicar_textos


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
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

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
        self.assertEqual(CorreoPendiente.objects.get(consulta=consulta).estado, 'aceptado_smtp')
        self.assertEqual(consulta.folio[:3], 'CP-')

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
        self.assertEqual(CorreoPendiente.objects.get(consulta=ConsultaProducto.objects.get()).estado, 'fallido')

    def test_la_base_avisa_a_quien_atiende_consultas(self):
        buzon = cuenta('buzon@example.test', 'atender_consultas')
        self.enviar(self.valido)
        aviso = Notificacion.objects.get(destinatario=buzon)
        self.assertEqual((aviso.origen, aviso.enlace), ('sistema', '#admin/consultas'))


@override_settings(CHILITO_CONTACTO_SOPORTE='soporte@example.test')
class BuzonDeConsultas(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        self.buzon = cuenta('buzon-admin@example.test', 'atender_consultas')
        self.otra = cuenta('otra-admin@example.test', 'gestionar_guias')
        self.persona = cuenta('persona@example.test')

    def test_se_guarda_y_no_se_duplica(self):
        primera = datos.record_inquiry('Ana', 'ana@example.test', 'Quiero uno')
        repetida = datos.record_inquiry('Ana', 'ANA@example.test', 'Quiero uno ')
        self.assertEqual(primera.pk, repetida.pk)
        self.assertEqual(CorreoPendiente.objects.filter(consulta=primera).count(), 1)

    def test_solo_con_atender_consultas(self):
        datos.record_inquiry('', 'bea@example.test', 'Hola')
        for actor in (self.otra, self.persona):
            with self.subTest(actor=actor.email), self.assertRaises(PermissionDenied):
                list(datos.admin_inquiries(actor))
        self.assertEqual(datos.admin_inquiries(self.buzon).count(), 1)

    def test_sin_segundo_factor_no_entra(self):
        Authenticator.objects.filter(user=self.buzon).delete()
        with self.assertRaises(datos.FactorRequerido):
            list(datos.admin_inquiries(self.buzon))

    def test_la_atencion_solo_avanza_y_conserva_responsable(self):
        consulta = datos.record_inquiry('', 'cris@example.test', 'Precio')
        datos.update_inquiry(self.buzon, consulta.pk, 'atendida')
        datos.update_inquiry(self.buzon, consulta.pk, 'archivada')
        consulta.refresh_from_db()
        self.assertEqual((consulta.estado, consulta.atendida_por_id), ('archivada', self.buzon.pk))
        with self.assertRaises(datos.RegistroDesactualizado):
            datos.update_inquiry(self.buzon, consulta.pk, 'nueva')
        datos.update_inquiry(self.buzon, consulta.pk, 'atendida')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConsultaProducto.objects.filter(pk=consulta.pk).update(estado='nueva', atendida_por=None, atendida_en=None)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConsultaProducto.objects.filter(pk=consulta.pk).update(mensaje='Alterado')


def peticion(agente='', ip='189.203.45.77'):
    return RequestFactory().get('/', REMOTE_ADDR=ip, HTTP_USER_AGENT=agente)


class CookiesPermanecen(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def peticion(self, usuario=None, **extra):
        pedido = peticion(**extra)
        pedido.user = usuario or AnonymousUser()
        return pedido

    def test_la_decision_sobrevive_al_cierre_de_sesion(self):
        usuario = cuenta('a@example.test')
        valor = services.decidir_cookies(self.peticion(usuario), None, True)
        estado = services.estado_cookies(valor, None)
        self.assertTrue(estado['decided'] and estado['statistics'])
        self.assertTrue(services.contar_seccion(None, valor, 'identificador', 'inicio'))

    def test_otra_cuenta_no_hereda_la_autorizacion(self):
        valor = services.decidir_cookies(self.peticion(cuenta('a@example.test')), None, True)
        otra = cuenta('b@example.test')
        self.assertFalse(services.estado_cookies(valor, otra)['decided'])
        self.assertFalse(services.contar_seccion(otra, valor, 'identificador', 'inicio'))

    def test_sin_sesion_se_puede_cambiar_sin_tocar_la_decision_de_la_cuenta(self):
        usuario = cuenta('a@example.test')
        valor = services.decidir_cookies(self.peticion(usuario), None, True)
        nuevo = services.decidir_cookies(self.peticion(), valor, False)
        self.assertFalse(services.estado_cookies(nuevo, None)['statistics'])
        self.assertTrue(services.estado_cookies(valor, usuario)['statistics'])

    def test_la_bitacora_guarda_ip_recortada_y_navegador_resumido(self):
        agente = ('Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/130.0.6723.58 Mobile Safari/537.36')
        services.decidir_cookies(self.peticion(cuenta('a@example.test'), agente=agente), None, True)
        decision = Decision.objects.get(acto='cookies')
        self.assertEqual((decision.ip_recortada, decision.navegador), ('189.203.45.0', 'Chrome 130 · Android'))
        self.assertNotIn('Mozilla', decision.navegador)
        self.assertEqual(decision.usuario.email, 'a@example.test')

    def test_ipv6_se_recorta_a_48_bits(self):
        decision = services.ip_recortada(peticion(ip='2001:db8:abcd:12:aaaa:bbbb:cccc:dddd'))
        self.assertEqual(decision, '2001:db8:abcd::')

    def test_una_nueva_version_de_la_politica_invalida_la_decision(self):
        valor = services.decidir_cookies(self.peticion(), None, True)
        publicar_textos('1.1')
        self.assertFalse(services.estado_cookies(valor, None)['decided'])
