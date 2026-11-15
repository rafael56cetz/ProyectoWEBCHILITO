"""Límite de «Consíguelo»: 5 envíos por hora y por IP, con y sin proxy de confianza."""
import json

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

INVALIDO = json.dumps({'name': '', 'email': 'no-valido', 'message': '', 'website': ''})   # cuenta en la cuota, no crea nada


class CuotaDeContacto(TestCase):
    def setUp(self):
        cache.clear()

    def enviar(self, cliente, reenviada=None, cuerpo=INVALIDO):
        cabeceras = {'HTTP_X_FORWARDED_FOR': reenviada} if reenviada else {}
        return cliente.post('/api/contacto', cuerpo, content_type='application/json', **cabeceras).status_code

    def agotar(self, cliente, reenviada=lambda i: None):
        return [self.enviar(cliente, reenviada(i)) for i in range(6)]

    def test_sin_proxy_la_cabecera_falsa_no_salta_la_cuota(self):
        cliente = Client(REMOTE_ADDR='198.51.100.1')
        self.assertEqual(self.agotar(cliente, lambda i: f'203.0.113.{i}'), [400] * 5 + [429])

    def test_sin_proxy_dos_ip_tienen_cuotas_separadas(self):
        self.assertEqual(self.agotar(Client(REMOTE_ADDR='198.51.100.1')), [400] * 5 + [429])
        self.assertEqual(self.enviar(Client(REMOTE_ADDR='198.51.100.2')), 400)

    @override_settings(ALLAUTH_TRUSTED_PROXY_COUNT=1)
    def test_tras_proxy_dos_clientes_tienen_cuotas_separadas(self):
        proxy = Client(REMOTE_ADDR='10.0.0.1')
        self.assertEqual(self.agotar(proxy, lambda i: '198.51.100.1'), [400] * 5 + [429])
        self.assertEqual(self.enviar(proxy, '198.51.100.2'), 400)

    @override_settings(ALLAUTH_TRUSTED_PROXY_COUNT=1)
    def test_tras_proxy_la_cabecera_falsa_no_salta_la_cuota(self):
        # El proxy añade la IP real al final de lo que envía el cliente.
        proxy = Client(REMOTE_ADDR='10.0.0.1')
        self.assertEqual(self.agotar(proxy, lambda i: f'203.0.113.{i}, 198.51.100.1'), [400] * 5 + [429])

    @override_settings(ALLAUTH_TRUSTED_PROXY_COUNT=2)
    def test_con_dos_proxies_cuenta_la_ip_real(self):
        proxy = Client(REMOTE_ADDR='10.0.0.1')
        self.assertEqual(self.agotar(proxy, lambda i: f'203.0.113.{i}, 198.51.100.1, 10.0.0.2'), [400] * 5 + [429])
        self.assertEqual(self.enviar(proxy, '203.0.113.9, 198.51.100.2, 10.0.0.2'), 400)

    def test_correos_distintos_desde_la_misma_ip_comparten_cuota(self):
        cliente = Client(REMOTE_ADDR='198.51.100.1')
        cuerpos = [json.dumps({'name': '', 'email': f'sin-arroba-{i}', 'message': '', 'website': ''}) for i in range(6)]
        self.assertEqual([self.enviar(cliente, cuerpo=c) for c in cuerpos], [400] * 5 + [429])
