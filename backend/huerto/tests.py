"""Fase 3 sobre PostgreSQL: huertos, plantas, órdenes, vinculación del equipo y aceptación de textos."""
import json
import uuid
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase
from django.utils import timezone

from datos.models import Auditoria, CodigoVinculacion, Comando, Dispositivo
from huerto.models import Huerto, Planta
from privacidad.models import Decision
from tests import aceptar_vigentes, cuenta, publicar_textos

from . import services

CREDENCIAL = 'credencial-de-prueba-0001'


def equipo(identificador='CHI-0001', mac='02:00:00:00:00:01'):
    return Dispositivo.objects.create(identificador=identificador, mac=mac, credencial_hash=make_password(CREDENCIAL))


class BaseHuerto(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        cache.clear()
        self.dueña = cuenta('huerto-duena@example.test')
        self.otra = cuenta('huerto-otra@example.test')
        self.client = self.cliente(self.dueña)

    def cliente(self, usuario=None):
        cliente = Client(HTTP_HOST='127.0.0.1')
        if usuario is not None:
            cliente.force_login(usuario, backend='django.contrib.auth.backends.ModelBackend')
        return cliente

    def post(self, ruta, datos=None, cliente=None):
        return (cliente or self.client).post(ruta, json.dumps(datos or {}), content_type='application/json',
                                             HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    def crear_huerto(self, nombre=None, cliente=None):
        respuesta = self.post('/api/huertos', {'name': nombre} if nombre else {}, cliente)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()['garden']['id']

    def codigo(self, huerto_id):
        respuesta = self.post(f'/api/huertos/{huerto_id}/codigo')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()['code']

    def vincular(self, identificador='CHI-0001', credencial=CREDENCIAL, codigo=''):
        return Client(HTTP_HOST='127.0.0.1', enforce_csrf_checks=True).post(
            '/api/dispositivos/vincular', json.dumps({'identifier': identificador, 'credential': credencial, 'code': codigo}),
            content_type='application/json')

    def huerto_con_equipo(self, identificador='CHI-0001', mac='02:00:00:00:00:01'):
        huerto_id = self.crear_huerto()
        equipo(identificador, mac)
        self.assertEqual(self.vincular(identificador, codigo=self.codigo(huerto_id)).json()['result'], 'vinculado')
        return huerto_id


class Huertos(BaseHuerto):
    def test_crear_con_y_sin_nombre_y_listar(self):
        huerto_id = self.crear_huerto('Mi patio')
        listado = self.client.get('/api/huertos').json()['items']
        self.assertEqual([(h['id'], h['name'], h['device']) for h in listado], [(huerto_id, 'Mi patio', None)])
        self.assertEqual(Planta.objects.filter(huerto_id=huerto_id).count(), 3)
        self.assertEqual(Huerto.objects.get(pk=huerto_id).zona_horaria, 'America/Merida')
        self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}').json()['garden']['name'], 'Mi patio')

    def test_sin_nombre_usa_el_de_la_base(self):
        huerto_id = self.crear_huerto()
        self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}').json()['garden']['name'], 'Mi huerto')

    def test_nombre_no_valido(self):
        for nombre in ('', '   ', 'x' * 61, 7, 'a\nb'):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.post('/api/huertos', {'name': nombre}).status_code, 400)

    def test_segundo_huerto_sin_equipo_se_rechaza_con_mensaje_claro(self):
        self.crear_huerto()
        respuesta = self.post('/api/huertos', {})
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'huerto-sin-equipo'))

    def test_cuarto_huerto_se_rechaza(self):
        for numero in range(3):
            self.huerto_con_equipo(f'CHI-10{numero}', f'02:00:00:00:01:0{numero}')
        respuesta = self.post('/api/huertos', {})
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'huerto-limite'))

    def test_renombrar_y_archivar(self):
        huerto_id = self.crear_huerto()
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/renombrar', {'name': 'Nuevo'}).status_code, 200)
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/renombrar', {}).status_code, 400)
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/archivar').status_code, 200)
        self.assertEqual(self.client.get('/api/huertos').json()['items'], [])
        self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}').status_code, 404)

    def test_no_archiva_con_equipo(self):
        huerto_id = self.huerto_con_equipo()
        respuesta = self.post(f'/api/huertos/{huerto_id}/archivar')
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'huerto-con-equipo'))

    def test_otra_cuenta_recibe_404_en_cada_endpoint(self):
        huerto_id = self.huerto_con_equipo()
        ajena = self.cliente(self.otra)
        for ruta in ('', '/ia', '/vinculacion', '/plantas/1'):
            with self.subTest(ruta=ruta):
                self.assertEqual(ajena.get(f'/api/huertos/{huerto_id}{ruta}').status_code, 404)
        pruebas = (('/renombrar', {'name': 'x'}), ('/archivar', {}), ('/codigo', {}), ('/desvincular', {}),
                   ('/plantas/1', {'name': 'x'}), ('/comandos', {'type': 'autodiagnostico'}), ('/cuidados', {'type': 'rellenar_deposito'}))
        for ruta, datos in pruebas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.post(f'/api/huertos/{huerto_id}{ruta}', datos, ajena).status_code, 404)
        self.assertEqual(ajena.get('/api/huertos').json()['items'], [])
        self.assertEqual(Huerto.objects.get(pk=huerto_id).nombre, 'Mi huerto')

    def test_inexistente_y_ajeno_responden_igual(self):
        huerto_id = self.crear_huerto()
        ajena = self.cliente(self.otra)
        self.assertEqual(ajena.get(f'/api/huertos/{huerto_id}').content, ajena.get('/api/huertos/999999999').content)

    def test_detalle_sin_lecturas_no_inventa_datos(self):
        huerto_id = self.huerto_con_equipo()
        detalle = self.client.get(f'/api/huertos/{huerto_id}').json()
        self.assertIsNone(detalle['metrics'])
        self.assertIsNone(detalle['summary'])
        self.assertEqual([p['moisture'] for p in detalle['plants']], [None, None, None])
        self.assertIsNone(detalle['lamp']['state'])
        self.assertEqual(detalle['garden']['device']['connection'], 'nunca')
        self.assertIsNone(detalle['garden']['device']['lastReadingAt'])

    def test_auditoria_sin_valores_personales(self):
        huerto_id = self.crear_huerto('Nombre privado')
        self.post(f'/api/huertos/{huerto_id}/archivar')
        acciones = list(Auditoria.objects.filter(actor=self.dueña).values_list('accion', flat=True))
        self.assertIn('crear_huerto', acciones)
        self.assertIn('archivar_huerto', acciones)
        self.assertFalse(Auditoria.objects.filter(detalle__icontains='privado').exists())


class Plantas(BaseHuerto):
    def test_editar_nombre_fecha_y_etapa(self):
        huerto_id = self.crear_huerto()
        hoy = timezone.localdate().isoformat()
        respuesta = self.post(f'/api/huertos/{huerto_id}/plantas/2', {'name': 'Chilito', 'sowingDate': hoy, 'stage': 'germinacion'})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        planta = self.client.get(f'/api/huertos/{huerto_id}/plantas/2').json()
        self.assertEqual((planta['plant']['name'], planta['plant']['stage']), ('Chilito', 'germinacion'))
        self.assertIsNotNone(planta['plant']['stageSince'])
        self.assertEqual([e['stage'] for e in planta['stages']][-1], 'germinacion')

    def test_validacion(self):
        huerto_id = self.crear_huerto()
        futuro = (timezone.localdate() + timedelta(days=2)).isoformat()
        casos = ({'name': ''}, {'name': 'x' * 41}, {'sowingDate': futuro}, {'sowingDate': 'ayer'}, {'stage': 'madura'}, {}, {'otro': 1})
        for datos in casos:
            with self.subTest(datos=datos):
                self.assertEqual(self.post(f'/api/huertos/{huerto_id}/plantas/1', datos).status_code, 400)
        self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}/plantas/4').status_code, 404)
        self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}/plantas/1?rango=1y').status_code, 400)


class Vinculacion(BaseHuerto):
    def test_flujo_completo_con_el_esp32(self):
        huerto_id = self.crear_huerto()
        equipo()
        codigo = self.codigo(huerto_id)
        self.assertRegex(codigo, r'^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$')
        estado = self.client.get(f'/api/huertos/{huerto_id}/vinculacion').json()
        self.assertEqual((estado['linked'], estado['codeState']), (False, 'pendiente'))
        respuesta = self.vincular(codigo=codigo.lower().replace('-', ' '))
        self.assertEqual((respuesta.status_code, respuesta.json()), (200, {'status': 'ready', 'result': 'vinculado'}))
        estado = self.client.get(f'/api/huertos/{huerto_id}/vinculacion').json()
        self.assertEqual((estado['linked'], estado['codeState'], estado['device']['identifier']), (True, 'utilizado', 'CHI-0001'))

    def test_solo_se_guarda_el_hmac_del_codigo(self):
        huerto_id = self.crear_huerto()
        codigo = self.codigo(huerto_id)
        registro = CodigoVinculacion.objects.get(huerto_id=huerto_id)
        self.assertEqual(registro.codigo_hash, services.huella_codigo(codigo.replace('-', '')))
        self.assertNotIn(codigo.replace('-', ''), registro.codigo_hash.upper())
        self.assertFalse(Auditoria.objects.filter(detalle__icontains=codigo.replace('-', '')).exists())

    def test_reintento_con_la_misma_clave_no_devuelve_el_codigo(self):
        huerto_id = self.crear_huerto()
        clave = str(uuid.uuid4())
        enviar = lambda: self.client.post(f'/api/huertos/{huerto_id}/codigo', '{}', content_type='application/json',
                                          HTTP_IDEMPOTENCY_KEY=clave).json()
        self.assertIsNotNone(enviar()['code'])
        self.assertIsNone(enviar()['code'])

    def test_generar_otro_codigo_cancela_el_anterior(self):
        huerto_id = self.crear_huerto()
        equipo()
        primero = self.codigo(huerto_id)
        self.codigo(huerto_id)
        self.assertEqual(CodigoVinculacion.objects.filter(huerto_id=huerto_id, estado='cancelado').count(), 1)
        self.assertEqual(self.vincular(codigo=primero).json()['result'], 'codigo_invalido')

    def test_codigo_vencido(self):
        huerto_id = self.crear_huerto()
        equipo()
        codigo = self.codigo(huerto_id)
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute("ALTER TABLE codigo_vinculacion DISABLE TRIGGER codigo_reglas")
            cursor.execute("UPDATE codigo_vinculacion SET generado_en=now()-interval '20 minutes', vence_en=now()-interval '10 minutes' "
                           "WHERE huerto_id=%s", [huerto_id])
            cursor.execute("ALTER TABLE codigo_vinculacion ENABLE TRIGGER codigo_reglas")
        self.assertEqual(self.vincular(codigo=codigo).json()['result'], 'codigo_vencido')

    def test_codigo_reutilizado(self):
        huerto_id = self.crear_huerto()
        equipo()
        equipo('CHI-0002', '02:00:00:00:00:02')
        codigo = self.codigo(huerto_id)
        self.assertEqual(self.vincular(codigo=codigo).json()['result'], 'vinculado')
        self.assertEqual(self.vincular('CHI-0002', codigo=codigo).json()['result'], 'codigo_usado')

    def test_equipo_ocupado(self):
        self.huerto_con_equipo()
        otro = self.cliente(self.otra)
        huerto_ajeno = self.crear_huerto(cliente=otro)
        codigo = self.post(f'/api/huertos/{huerto_ajeno}/codigo', cliente=otro).json()['code']
        self.assertEqual(self.vincular(codigo=codigo).json()['result'], 'dispositivo_ocupado')

    def test_credencial_invalida_y_equipo_desconocido_responden_igual(self):
        huerto_id = self.crear_huerto()
        equipo()
        codigo = self.codigo(huerto_id)
        mala = self.vincular(credencial='otra-credencial', codigo=codigo)
        desconocido = self.vincular('NO-EXISTE', codigo=codigo)
        self.assertEqual(mala.json(), desconocido.json())
        self.assertEqual(mala.json()['result'], 'credencial_invalida')
        self.assertEqual(CodigoVinculacion.objects.get(huerto_id=huerto_id).estado, 'pendiente')

    def test_entrada_no_valida(self):
        cliente = Client(HTTP_HOST='127.0.0.1')
        for cuerpo in ({}, {'identifier': 'a', 'credential': 'b'}, {'identifier': 1, 'credential': 'b', 'code': 'c'},
                       {'identifier': 'a', 'credential': 'b', 'code': 'c', 'extra': 1}):
            with self.subTest(cuerpo=cuerpo):
                respuesta = cliente.post('/api/dispositivos/vincular', json.dumps(cuerpo), content_type='application/json')
                self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.vincular(codigo='no-es-un-codigo').json()['result'], 'credencial_invalida')

    def test_cuota_por_identificador(self):
        resultados = [self.vincular('CHI-9999', codigo='AAAA-AAAA').status_code for _ in range(7)]
        self.assertEqual(resultados[:5], [200] * 5)
        self.assertEqual(resultados[5:], [429, 429])

    def test_sin_sesion_el_resto_exige_cuenta(self):
        self.assertEqual(Client(HTTP_HOST='127.0.0.1').get('/api/huertos').status_code, 401)

    def test_desvincular(self):
        huerto_id = self.huerto_con_equipo()
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/desvincular').status_code, 200)
        self.assertEqual(Dispositivo.objects.get(identificador='CHI-0001').estado, 'disponible')
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/desvincular').status_code, 404)
        self.assertTrue(Auditoria.objects.filter(accion='desvincular_dispositivo', actor=self.dueña).exists())

    def test_huerto_con_equipo_no_genera_codigo(self):
        huerto_id = self.huerto_con_equipo()
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/codigo').json()['code'], 'huerto-con-equipo')


class Ordenes(BaseHuerto):
    def test_regar_y_consultar_estado(self):
        huerto_id = self.huerto_con_equipo()
        respuesta = self.post(f'/api/huertos/{huerto_id}/comandos', {'type': 'regar', 'plant': 2, 'duration': 8})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        orden = respuesta.json()['command']
        self.assertEqual((orden['state'], orden['plant'], orden['duration']), ('pendiente', 2, 8))
        self.assertEqual(self.client.get(f"/api/comandos/{orden['id']}").json()['command']['state'], 'pendiente')
        self.assertEqual(self.cliente(self.otra).get(f"/api/comandos/{orden['id']}").status_code, 404)
        self.assertTrue(Auditoria.objects.filter(accion='crear_comando', actor=self.dueña).exists())

    def test_lampara_y_autodiagnostico(self):
        huerto_id = self.huerto_con_equipo()
        for tipo in ('lampara_apagar', 'lampara_automatico', 'autodiagnostico'):
            with self.subTest(tipo=tipo):
                self.assertEqual(self.post(f'/api/huertos/{huerto_id}/comandos', {'type': tipo}).status_code, 200)
        self.assertEqual(Comando.objects.filter(huerto_id=huerto_id).count(), 3)

    def test_validacion(self):
        huerto_id = self.huerto_con_equipo()
        casos = ({'type': 'reiniciar'}, {'type': 'regar'}, {'type': 'regar', 'plant': 4, 'duration': 8},
                 {'type': 'regar', 'plant': 1, 'duration': 7}, {'type': 'regar', 'plant': True, 'duration': 8},
                 {'type': 'lampara_apagar', 'plant': 1}, {'type': 'autodiagnostico', 'duration': 5}, {})
        for datos in casos:
            with self.subTest(datos=datos):
                self.assertEqual(self.post(f'/api/huertos/{huerto_id}/comandos', datos).status_code, 400)

    def test_sin_equipo_no_hay_ordenes(self):
        huerto_id = self.crear_huerto()
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/comandos', {'type': 'autodiagnostico'}).status_code, 400)

    def test_registrar_recarga(self):
        huerto_id = self.huerto_con_equipo()
        respuesta = self.post(f'/api/huertos/{huerto_id}/cuidados', {'type': 'rellenar_deposito'})
        self.assertEqual((respuesta.status_code, respuesta.json()['care']['type']), (200, 'rellenar_deposito'))
        for datos in ({'type': 'rellenar_deposito', 'plant': 1}, {'type': 'cosecha'}, {'type': 'otro'},
                      {'type': 'inspeccion', 'chiles': 3}, {'type': 'cosecha', 'plant': 1, 'chiles': -1}):
            with self.subTest(datos=datos):
                self.assertEqual(self.post(f'/api/huertos/{huerto_id}/cuidados', datos).status_code, 400)


class AceptarTextos(BaseHuerto):
    def pendientes(self):
        return self.client.get('/api/cuenta').json()['pendingLegal']

    def publicar_nueva_version(self):
        # La base exige las aceptaciones vigentes de toda cuenta al cerrar la transacción de la prueba.
        publicar_textos('1.1')
        for usuario in (self.dueña, self.otra):
            self.addCleanup(aceptar_vigentes, usuario)

    def test_acepta_solo_los_pendientes(self):
        self.publicar_nueva_version()
        ids = [p['documentId'] for p in self.pendientes()]
        self.assertEqual(len(ids), 2)
        respuesta = self.post('/api/legales/aceptar', {'documents': ids})
        self.assertEqual((respuesta.status_code, respuesta.json()['pendingLegal']), (200, []))
        self.assertEqual(self.pendientes(), [])
        self.assertEqual(Decision.objects.filter(usuario=self.dueña, documento_id__in=ids).count(), 2)

    def test_rechaza_ids_ajenos_o_repetidos(self):
        self.publicar_nueva_version()
        ids = [p['documentId'] for p in self.pendientes()]
        for documentos in ([str(uuid.uuid4())], [ids[0], ids[0]], [], 'x', [1], ids + [str(uuid.uuid4())]):
            with self.subTest(documentos=documentos):
                self.assertEqual(self.post('/api/legales/aceptar', {'documents': documentos}).status_code, 400)
        self.assertEqual(len(self.pendientes()), 2)

    def test_no_hay_nada_que_aceptar_sin_version_nueva(self):
        ids = [str(uuid.uuid4())]
        self.assertEqual(self.post('/api/legales/aceptar', {'documents': ids}).status_code, 400)

    def test_aceptar_una_cuenta_no_afecta_a_otra(self):
        self.publicar_nueva_version()
        ids = [p['documentId'] for p in self.pendientes()]
        self.post('/api/legales/aceptar', {'documents': ids})
        self.assertEqual(len(self.cliente(self.otra).get('/api/cuenta').json()['pendingLegal']), 2)
