"""Reglas de entrada del servidor (web/validacion.py): cada regla por sí sola y en los endpoints que la usan.
El navegador aplica las mismas reglas (frontend/modelos/comun.js), pero aquí se comprueba que el servidor no confía en él."""
import json
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from datos.models import ConsultaProducto, GuiaCuidado, Venta
from datos.tests import test_admin as admin_base
from huerto.models import Huerto, Planta
from huerto.tests import AyudasHuerto
from tests import cuenta, publicar_textos
from web import validacion as v


class Reglas(SimpleTestCase):
    def codigo(self, funcion, *args, **kwargs):
        with self.assertRaises(v.CampoInvalido) as fallo:
            funcion(*args, **kwargs)
        return fallo.exception.codigo

    def test_nombre_de_persona(self):
        for valido in ('Ana', 'José María', 'Peña', 'Müller', "O'Connor", 'O’Brien', 'Ana-Lucía', 'Zoë', 'Łukasz', 'Ñu'):
            with self.subTest(valido=valido):
                self.assertEqual(v.nombre_persona(f'  {valido} ', 'buyer'), valido)
        for invalido in ('Ana3', 'Ana_M', 'Ana.', 'ana@x', '<b>Ana</b>', 'Ana​María', '-Ana', "'Ana", 'Ana\tM'):
            with self.subTest(invalido=invalido):
                self.assertEqual(self.codigo(v.nombre_persona, invalido, 'buyer'), 'solo-letras')
        self.assertEqual(self.codigo(v.nombre_persona, 'A', 'buyer'), 'largo-no-valido')
        self.assertEqual(self.codigo(v.nombre_persona, 'a' * 61, 'buyer'), 'largo-no-valido')
        self.assertEqual(self.codigo(v.nombre_persona, '', 'buyer'), 'campo-requerido')
        self.assertEqual(v.nombre_persona('', 'firstName', requerido=False), '')
        self.assertEqual(self.codigo(v.nombre_persona, 7, 'buyer'), 'texto-no-valido')
        # NFC: «é» escrita como «e» + acento combinado se guarda compuesta.
        self.assertEqual(v.nombre_persona('José', 'buyer'), 'José')

    def test_nombre_de_cosa(self):
        for valido in ('Planta 1', 'Planta 2', 'Mi huerto', 'Huerto-Patio 3', 'Chile habanero', 'Árbol', 'Rafa'):
            with self.subTest(valido=valido):
                self.assertEqual(v.nombre_cosa(valido, 'name', maximo=60), valido)
        for invalido in ('Planta #1', 'Mi_huerto', 'Huerto <b>', "L'huerto", 'Huerto.', 'Huerto\n2', 'a\x00b'):
            with self.subTest(invalido=invalido):
                self.assertEqual(self.codigo(v.nombre_cosa, invalido, 'name', maximo=60), 'solo-letras-numeros')
        self.assertEqual(self.codigo(v.nombre_cosa, 'x' * 41, 'name', maximo=40), 'largo-no-valido')
        self.assertEqual(self.codigo(v.nombre_cosa, '   ', 'name', maximo=40), 'campo-requerido')

    def test_enteros(self):
        self.assertEqual(v.entero(0, 'chiles', 0, 999), 0)
        self.assertEqual(v.entero(999, 'chiles', 0, 999), 999)
        for invalido in ('abc', '7', 7.0, 7.5, True, None, -1, 1000, [7]):
            with self.subTest(invalido=invalido):
                self.assertEqual(self.codigo(v.entero, invalido, 'chiles', 0, 999), 'solo-numeros')
        self.assertEqual(v.entero_texto('123', 'garden', maximo_digitos=18), '123')
        for invalido in ('12a', '١٢', '-1', '1.5', '', '1' * 19, 12):
            with self.subTest(invalido=invalido):
                self.assertEqual(self.codigo(v.entero_texto, invalido, 'garden', maximo_digitos=18), 'solo-numeros')

    def test_dinero(self):
        for valido, valor in (('0', '0'), ('3500', '3500'), ('3500.5', '3500.5'), ('3500.50', '3500.50'), ('99999999.99', '99999999.99')):
            self.assertEqual(v.dinero(valido, 'price'), Decimal(valor))
        for invalido in ('-1', '1e3', '3500.999', '3,500', ' 35', '35 ', '', 'abc', '٣٥', 3500, '123456789', '.5', '5.'):
            with self.subTest(invalido=invalido):
                self.assertEqual(self.codigo(v.dinero, invalido, 'price'), 'importe-no-valido')

    def test_formatos_fijos(self):
        from datos.equipos import IDENTIFICADOR, MAC
        self.assertEqual(v.formato('AA:BB:CC:DD:EE:FF', 'mac', MAC, 'x'), 'AA:BB:CC:DD:EE:FF')
        for invalido in ('AA:BB:CC:DD:EE', 'AA-BB-CC-DD-EE-FF', 'GG:BB:CC:DD:EE:FF'):
            self.assertEqual(self.codigo(v.formato, invalido, 'mac', MAC, 'x'), 'formato-no-valido')
        self.assertEqual(self.codigo(v.formato, 'ESP32-A1B2\nX', 'identifier', IDENTIFICADOR, 'x'), 'formato-no-valido')
        self.assertEqual(v.formato('', 'firmware', MAC, 'x', requerido=False), '')

    def test_texto_libre(self):
        self.assertEqual(v.texto_libre('  Hola ', 'note', maximo=10), 'Hola')
        self.assertEqual(v.texto_libre('a\r\nb\tc', 'note', maximo=10, multilinea=True), 'a\nb c')
        self.assertEqual(v.texto_libre('<b>ñ</b> & «ok»', 'note', maximo=50), '<b>ñ</b> & «ok»', 'libre: se escapa al mostrar')
        for invalido in ('a\x00b', 'a\x1bb', 'a\x7fb', 'a‮b'):
            with self.subTest(invalido=repr(invalido)):
                self.assertEqual(self.codigo(v.texto_libre, invalido, 'note', maximo=10, multilinea=True), 'caracteres-no-validos')
        self.assertEqual(self.codigo(v.texto_libre, 'a\nb', 'reference', maximo=10), 'caracteres-no-validos', 'una sola línea')
        self.assertEqual(self.codigo(v.texto_libre, 'x' * 11, 'note', maximo=10), 'largo-no-valido')
        self.assertEqual(self.codigo(v.texto_libre, ' ', 'reason', maximo=10, requerido=True), 'campo-requerido')

    def test_respuesta(self):
        fallo = v.CampoInvalido('chiles', 'solo-numeros', 'Solo números entre 0 y 999.')
        self.assertEqual(fallo.respuesta(), {'status': 400, 'code': 'solo-numeros', 'field': 'chiles', 'message': 'Solo números entre 0 y 999.'})


class EndpointsDelUsuario(AyudasHuerto, TestCase):
    """Huerto, planta, cuidados, perfil y contacto: 400 con el campo y el código aunque el navegador ya valide."""

    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def rechazo(self, respuesta, campo, codigo):
        self.assertEqual(respuesta.status_code, 400, respuesta.content)
        cuerpo = respuesta.json()
        self.assertEqual((cuerpo['code'], cuerpo['field']), (codigo, campo))
        self.assertTrue(cuerpo['message'])

    def test_nombre_del_huerto(self):
        self.rechazo(self.post('/api/huertos', {'name': 'Huerto <script>'}), 'name', 'solo-letras-numeros')
        self.assertFalse(Huerto.objects.filter(propietario=self.dueña).exists())
        huerto = self.crear_huerto('Patio 2')
        self.rechazo(self.post(f'/api/huertos/{huerto}/renombrar', {'name': 'Patio_2'}), 'name', 'solo-letras-numeros')
        self.rechazo(self.post(f'/api/huertos/{huerto}/renombrar', {'name': ''}), 'name', 'campo-requerido')
        self.assertEqual(self.post(f'/api/huertos/{huerto}/renombrar', {'name': 'Huerto-Balcón 1'}).status_code, 200)

    def test_planta_1_es_valido(self):
        huerto = self.huerto_vinculado()
        ruta = f'/api/huertos/{huerto}/plantas/1'
        self.assertEqual(Planta.objects.get(huerto_id=huerto, numero=1).nombre, 'Planta 1', 'nombre de fábrica')
        self.assertEqual(self.post(ruta, {'name': 'Planta 1'}).status_code, 200)
        self.assertEqual(self.post(ruta, {'name': 'Chile 2'}).status_code, 200)
        self.rechazo(self.post(ruta, {'name': 'Planta #1'}), 'name', 'solo-letras-numeros')
        self.assertEqual(Planta.objects.get(huerto_id=huerto, numero=1).nombre, 'Chile 2')

    def test_chiles(self):
        huerto = self.huerto_vinculado()
        ruta = f'/api/huertos/{huerto}/cuidados'
        for chiles in ('abc', '7', 7.5, -1, 1000, True):
            with self.subTest(chiles=chiles):
                self.rechazo(self.post(ruta, {'type': 'cosecha', 'plant': 1, 'chiles': chiles}), 'chiles', 'solo-numeros')
        self.rechazo(self.post(ruta, {'type': 'cosecha', 'plant': 'uno'}), 'plant', 'solo-numeros')
        self.assertEqual(self.post(ruta, {'type': 'cosecha', 'plant': 1, 'chiles': 999}).status_code, 200)
        self.assertEqual(self.post(ruta, {'type': 'cosecha', 'plant': 2, 'chiles': 0}).status_code, 200)

    def test_perfil(self):
        self.rechazo(self.post('/api/cuenta/perfil', {'firstName': 'Ana3'}), 'firstName', 'solo-letras')
        self.rechazo(self.post('/api/cuenta/perfil', {'lastName': 'A'}), 'lastName', 'largo-no-valido')
        self.rechazo(self.post('/api/cuenta/perfil', {'alias': 'Rafa!'}), 'alias', 'solo-letras-numeros')
        self.assertEqual(self.post('/api/cuenta/perfil', {'firstName': 'José María', 'lastName': "O'Connor-Peña", 'alias': 'Rafa 2'}).status_code, 200)
        self.dueña.refresh_from_db()
        self.assertEqual((self.dueña.first_name, self.dueña.last_name, self.dueña.alias), ('José María', "O'Connor-Peña", 'Rafa 2'))
        self.assertEqual(self.post('/api/cuenta/perfil', {'firstName': '', 'alias': ''}).status_code, 200, 'vacío borra el dato')

    def test_nombre_de_la_llave(self):
        respuesta = self.client.post('/_allauth/browser/v1/account/authenticators/webauthn', json.dumps({'name': 'Llave <1>', 'credential': {}}),
                                     content_type='application/json')
        self.rechazo(respuesta, 'name', 'solo-letras-numeros')

    def test_contacto(self):
        from tests.test_contacto_cookies import cliente_con_csrf, enviar
        anonimo = cliente_con_csrf()
        datos = {'name': 'Ana López', 'email': 'ana@example.test', 'message': 'Hola'}
        self.rechazo(enviar(anonimo, '/api/contacto', {**datos, 'name': 'J0hn'}), 'name', 'solo-letras')
        self.rechazo(enviar(anonimo, '/api/contacto', {**datos, 'email': 'sin-arroba'}), 'email', 'correo-no-valido')
        self.rechazo(enviar(anonimo, '/api/contacto', {**datos, 'message': 'a\x00b'}), 'message', 'caracteres-no-validos')
        self.assertEqual(ConsultaProducto.objects.count(), 0)
        self.assertEqual(enviar(anonimo, '/api/contacto', {**datos, 'name': ''}).status_code, 200, 'el nombre es opcional')


class EndpointsDeAdministracion(admin_base.BaseAdmin):
    """Ventas, equipos, guías, mantenimientos, soporte y administradores."""

    def rechazo(self, respuesta, campo, codigo):
        self.assertEqual(respuesta.status_code, 400, respuesta.content)
        self.assertEqual((respuesta.json()['code'], respuesta.json()['field']), (codigo, campo))

    def test_venta(self):
        admin = self.cliente(cuenta('val-ventas@example.test', 'gestionar_ventas'))
        equipo = self.equipo('VAL-0001')
        datos = {'device': str(equipo.pk), 'buyer': 'Ana Pérez', 'email': 'ana@example.test', 'municipality': 'Mérida', 'price': '3500.00',
                 'received': '0', 'method': 'domicilio', 'soldAt': '2026-01-10'}
        for cambios, campo, codigo in (({'buyer': 'Ana 2'}, 'buyer', 'solo-letras'), ({'buyer': 'A'}, 'buyer', 'largo-no-valido'),
                                       ({'price': '35,00'}, 'price', 'importe-no-valido'), ({'price': '-5'}, 'price', 'importe-no-valido'),
                                       ({'received': '1.234'}, 'received', 'importe-no-valido'), ({'email': 'x'}, 'email', 'correo-no-valido'),
                                       ({'note': 'a\x07'}, 'note', 'caracteres-no-validos')):
            with self.subTest(cambios=cambios):
                self.rechazo(self.post(admin, '/api/admin/ventas', {**datos, **cambios}), campo, codigo)
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(self.post(admin, '/api/admin/ventas', {**datos, 'buyer': "María O'Neil-Ñúñez"}).status_code, 200)

    def test_equipo(self):
        admin = self.cliente(cuenta('val-equipos@example.test', 'gestionar_dispositivos'))
        datos = {'identifier': 'ESP32-A1B2', 'mac': 'AA:BB:CC:DD:EE:01', 'firmware': '1.0.0'}
        self.rechazo(self.post(admin, '/api/admin/equipos', {**datos, 'mac': 'AA:BB'}), 'mac', 'formato-no-valido')
        self.rechazo(self.post(admin, '/api/admin/equipos', {**datos, 'identifier': 'ES P32'}), 'identifier', 'formato-no-valido')
        self.rechazo(self.post(admin, '/api/admin/equipos', {**datos, 'firmware': '1.0 beta'}), 'firmware', 'formato-no-valido')
        self.assertEqual(self.post(admin, '/api/admin/equipos', datos).status_code, 200)

    def test_guia(self):
        admin = self.cliente(cuenta('val-guias@example.test', 'gestionar_guias'))
        antes = GuiaCuidado.objects.count()
        datos = {'question': '¿Cada cuánto riego?', 'answer': 'Cuando el sustrato esté seco.', 'order': 1, 'sourceName': '', 'sourceUrl': ''}
        self.rechazo(self.post(admin, '/api/admin/guias', {**datos, 'order': '1'}), 'order', 'solo-numeros')
        self.rechazo(self.post(admin, '/api/admin/guias', {**datos, 'order': 10000}), 'order', 'solo-numeros')
        self.rechazo(self.post(admin, '/api/admin/guias', {**datos, 'answer': 'a\x1bb'}), 'answer', 'caracteres-no-validos')
        self.rechazo(self.post(admin, '/api/admin/guias', {**datos, 'sourceName': 'X', 'sourceUrl': 'ftp://x'}), 'sourceUrl', 'formato-no-valido')
        self.assertEqual(GuiaCuidado.objects.count(), antes)
        self.assertEqual(self.post(admin, '/api/admin/guias', datos).status_code, 200)

    def test_mantenimiento(self):
        admin = self.cliente(cuenta('val-mant@example.test', 'gestionar_mantenimientos'))
        dueno = self.cliente(cuenta('val-dueno@example.test'))
        huerto = self.post(dueno, '/api/huertos').json()['garden']['id']
        base = {'garden': huerto, 'type': 'cosecha', 'plant': 1}
        self.rechazo(self.post(admin, '/api/admin/mantenimientos', {**base, 'chiles': 'abc'}), 'chiles', 'solo-numeros')
        self.rechazo(self.post(admin, '/api/admin/mantenimientos', {**base, 'garden': '12a'}), 'garden', 'solo-numeros')
        self.assertEqual(admin.get('/api/admin/mantenimientos?huerto=x1').json()['field'], 'huerto')
        self.assertEqual(self.post(admin, '/api/admin/mantenimientos', {**base, 'chiles': 12}).status_code, 200)
