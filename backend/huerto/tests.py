"""Fase 3 sobre PostgreSQL: huertos, plantas, órdenes, vinculación del equipo y aceptación de textos."""
import json
import os
import unittest
import uuid
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import connection
import psycopg
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from datos.models import (Auditoria, CodigoVinculacion, Comando, Cuidado, CuidadoRevision, Dispositivo, Medicion, MedicionPlanta,
                          Notificacion)
from huerto.models import Huerto, Planta
from privacidad.models import Decision
from tests import aceptar_vigentes, cuenta, publicar_textos
try:
    from tools import simular_equipo
except ImportError:      # la entrega a la nube no incluye el simulador
    simular_equipo = None

from . import services

CREDENCIAL = 'credencial-de-prueba-0001'


def equipo(identificador='CHI-0001', mac='02:00:00:00:00:01'):
    return Dispositivo.objects.create(identificador=identificador, mac=mac, credencial_hash=make_password(CREDENCIAL))


class AyudasHuerto:
    """Cuentas, huertos y el equipo vinculado que usan las pruebas de esta fase."""

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


class BaseHuerto(AyudasHuerto, TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()


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


def medir(huerto_id, hace_minutos, humedad=40, luz=None, **campos):
    """Una medición del equipo vinculado, con sus 3 plantas (la inserta el propietario de la base)."""
    equipo_del_huerto = Dispositivo.objects.get(huerto_id=huerto_id)
    medicion = Medicion.objects.create(dispositivo=equipo_del_huerto, huerto_id=huerto_id, luz_lux=luz,
                                       medida_en=timezone.now() - timedelta(minutes=hace_minutos),
                                       **{'temperatura_c': 25, 'humedad_aire_pct': 60, 'deposito_con_agua': True, **campos})
    for numero in (1, 2, 3):
        MedicionPlanta.objects.create(medicion=medicion, planta_numero=numero, humedad_sustrato_pct=humedad + numero, adc_crudo=2000 + numero)
    return medicion


class Telemetria(BaseHuerto):
    def test_horas_trae_series_por_planta_con_adc(self):
        huerto_id = self.huerto_con_equipo()
        medir(huerto_id, 30, luz=1200)
        medir(huerto_id, 10, luz=1300)
        datos = self.client.get(f'/api/huertos/{huerto_id}/telemetria?rango=1h').json()
        self.assertEqual([len(p['points']) for p in datos['series']['plants']], [2, 2, 2])
        self.assertEqual([p['adc'] for p in datos['plants']], [2001, 2002, 2003])
        self.assertTrue(datos['hasLight'])
        self.assertEqual(len(datos['series']['temperature']), 2)

    def test_sin_luz_no_se_inventa(self):
        huerto_id = self.huerto_con_equipo()
        medir(huerto_id, 5)
        datos = self.client.get(f'/api/huertos/{huerto_id}/telemetria?rango=24h').json()
        self.assertFalse(datos['hasLight'])
        self.assertEqual(datos['series']['light'], [])

    def test_dias_salen_de_los_resumenes_por_hora(self):
        huerto_id = self.huerto_con_equipo()
        medir(huerto_id, 90)
        medir(huerto_id, 80, humedad=50)
        with connection.cursor() as cursor:
            cursor.execute("SELECT chilito_resumir_mediciones(now() - interval '3 hours', now() + interval '1 hour')")
        datos = self.client.get(f'/api/huertos/{huerto_id}/telemetria?rango=7d').json()
        punto = datos['series']['plants'][0]['points'][0]
        self.assertIsNotNone(punto['min']) and self.assertIsNotNone(punto['max'])
        self.assertTrue(datos['series']['temperature'])

    def test_sin_datos_devuelve_vacio_y_no_ceros(self):
        huerto_id = self.huerto_con_equipo()
        datos = self.client.get(f'/api/huertos/{huerto_id}/telemetria?rango=30d').json()
        self.assertEqual([p['points'] for p in datos['series']['plants']], [[], [], []])
        self.assertIsNone(datos['latest'])
        self.assertEqual([p['moisture'] for p in datos['plants']], [None, None, None])

    def test_validacion_y_otra_cuenta(self):
        huerto_id = self.huerto_con_equipo()
        for consulta in ('?rango=1y', '?rango=1h&x=1', '?rango='):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}/telemetria{consulta}').status_code, 400)
        self.assertEqual(self.cliente(self.otra).get(f'/api/huertos/{huerto_id}/telemetria?rango=1h').status_code, 404)


class Bitacora(BaseHuerto):
    def test_ordenes_y_eventos_paginados(self):
        huerto_id = self.huerto_con_equipo()
        self.post(f'/api/huertos/{huerto_id}/comandos', {'type': 'autodiagnostico'})
        ordenes = self.client.get(f'/api/huertos/{huerto_id}/bitacora?tipo=ordenes').json()
        self.assertEqual((ordenes['total'], ordenes['items'][0]['origin']), (1, 'usuario'))
        eventos = self.client.get(f'/api/huertos/{huerto_id}/bitacora?tipo=eventos').json()
        self.assertEqual(eventos['status'], 'ready')
        self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}/bitacora?tipo=actuaciones').json()['items'], [])

    def test_validacion_y_otra_cuenta(self):
        huerto_id = self.huerto_con_equipo()
        for consulta in ('?tipo=todo', '?tipo=ordenes&page=0', '?tipo=ordenes&page=10001', '?tipo=ordenes&otra=1'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}/bitacora{consulta}').status_code, 400)
        self.assertEqual(self.cliente(self.otra).get(f'/api/huertos/{huerto_id}/bitacora?tipo=ordenes').status_code, 404)


class Cuidados(BaseHuerto):
    def setUp(self):
        super().setUp()
        self.editor = cuenta('huerto-editor@example.test', 'gestionar_mantenimientos')
        self.huerto_id = self.huerto_con_equipo()

    def registrar(self, **datos):
        return self.post(f'/api/huertos/{self.huerto_id}/cuidados', datos)

    def listar(self, consulta=''):
        return self.client.get(f'/api/huertos/{self.huerto_id}/cuidados{consulta}')

    def test_registrar_con_fecha_y_chiles(self):
        hace_dos_dias = (timezone.now() - timedelta(days=2)).isoformat()
        respuesta = self.registrar(type='cosecha', plant=2, chiles=7, doneAt=hace_dos_dias)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        cuidado = respuesta.json()['care']
        self.assertEqual((cuidado['type'], cuidado['plant'], cuidado['chiles']), ('cosecha', 2, 7))

    def test_fecha_no_valida(self):
        for fecha in ((timezone.now() - timedelta(days=9)).isoformat(), (timezone.now() + timedelta(days=1)).isoformat(), '2026-11-01', 'ayer', 5):
            with self.subTest(fecha=fecha):
                self.assertEqual(self.registrar(type='rellenar_deposito', doneAt=fecha).status_code, 400)

    def test_historial_aplica_la_ultima_revision(self):
        cuidado = Cuidado.objects.create(huerto_id=self.huerto_id, tipo='sustrato', planta_numero=1, registrado_por=self.dueña)
        CuidadoRevision.objects.create(cuidado=cuidado, numero=1, tipo='correccion', tipo_corregido='germinacion', planta_corregida=3,
                                       motivo='Se anotó mal', editor=self.editor)
        fila = self.listar().json()['items'][0]
        self.assertEqual((fila['type'], fila['plant'], fila['corrected'], fila['reason']), ('germinacion', 3, True, 'Se anotó mal'))
        self.assertEqual(self.listar('?tipo=sustrato').json()['total'], 0)
        self.assertEqual(self.listar('?tipo=germinacion&planta=3').json()['total'], 1)

    def test_anulado_se_ve_tachado(self):
        cuidado = Cuidado.objects.create(huerto_id=self.huerto_id, tipo='rellenar_deposito', registrado_por=self.dueña)
        CuidadoRevision.objects.create(cuidado=cuidado, numero=1, tipo='anulacion', motivo='Duplicado', editor=self.editor)
        fila = self.listar().json()['items'][0]
        self.assertEqual((fila['voided'], fila['reason']), (True, 'Duplicado'))

    def test_filtros_planta_tipo_y_fechas(self):
        self.registrar(type='rellenar_deposito')
        self.registrar(type='sustrato', plant=1)
        self.assertEqual(self.listar().json()['total'], 2)
        self.assertEqual(self.listar('?planta=huerto').json()['total'], 1)
        self.assertEqual(self.listar('?planta=1').json()['total'], 1)
        hoy = timezone.localdate().isoformat()
        self.assertEqual(self.listar(f'?desde={hoy}&hasta={hoy}').json()['total'], 2)
        self.assertEqual(self.listar('?hasta=2020-01-01').json()['total'], 0)

    def test_filtros_no_validos(self):
        for consulta in ('?planta=4', '?tipo=otro', '?desde=ayer', '?desde=2026-02-01&hasta=2026-01-01', '?pagina=1', '?page=0'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.listar(consulta).status_code, 400)

    def test_otra_cuenta(self):
        ajena = self.cliente(self.otra)
        self.assertEqual(ajena.get(f'/api/huertos/{self.huerto_id}/cuidados').status_code, 404)
        self.assertEqual(self.post(f'/api/huertos/{self.huerto_id}/cuidados', {'type': 'rellenar_deposito'}, ajena).status_code, 404)


class Soporte(BaseHuerto):
    def setUp(self):
        super().setUp()
        self.huerto_id = self.huerto_con_equipo()
        self.ruta = f'/api/huertos/{self.huerto_id}/soporte'

    def abrir(self, **cambios):
        return self.post(self.ruta, {'incident': 'bomba', 'note': 'No riega', 'consent': True, **cambios})

    def test_sin_caso(self):
        datos = self.client.get(self.ruta).json()
        self.assertEqual((datos['active'], datos['history'], datos['orders'], datos['hasDevice']), (None, [], [], True))

    def test_abrir_revisar_y_auditar(self):
        respuesta = self.abrir()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        caso = respuesta.json()['case']
        self.assertRegex(caso['folio'], r'^CS-[0-9A-F]{8}$')
        self.assertEqual((caso['state'], caso['incident']), ('abierto', 'bomba'))
        self.assertEqual(self.client.get(self.ruta).json()['active']['id'], caso['id'])
        auditoria = Auditoria.objects.get(accion='abrir_caso', actor=self.dueña)
        self.assertEqual(auditoria.detalle, {'incidente': 'bomba'})

    def test_sin_consentimiento_o_con_datos_no_validos(self):
        for cambios in ({'consent': False}, {'consent': 'si'}, {'incident': 'otra'}, {'note': 'x' * 501}, {'note': 7}, {'diagnostic': 'no-es-uuid'}):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.abrir(**cambios).status_code, 400)
        self.assertEqual(self.post(self.ruta, {'incident': 'bomba'}).status_code, 400)

    def test_un_solo_caso_activo(self):
        self.abrir()
        respuesta = self.abrir()
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'caso-activo'))

    def test_adjunta_solo_su_autodiagnostico(self):
        orden = self.post(f'/api/huertos/{self.huerto_id}/comandos', {'type': 'autodiagnostico'}).json()['command']
        self.assertTrue(orden['diagnosticId'])
        self.assertEqual(self.abrir(diagnostic=orden['diagnosticId']).status_code, 200)

    def test_no_adjunta_el_autodiagnostico_de_otra_cuenta(self):
        otro = self.cliente(self.otra)
        huerto_ajeno = self.crear_huerto(cliente=otro)
        equipo('CHI-0002', '02:00:00:00:00:02')
        codigo = self.post(f'/api/huertos/{huerto_ajeno}/codigo', cliente=otro).json()['code']
        self.assertEqual(self.vincular('CHI-0002', codigo=codigo).json()['result'], 'vinculado')
        orden = self.post(f'/api/huertos/{huerto_ajeno}/comandos', {'type': 'autodiagnostico'}, otro).json()['command']
        self.assertEqual(self.abrir(diagnostic=orden['diagnosticId']).status_code, 400)

    def test_revocar_deja_el_caso_abierto_y_cancelar_lo_cierra(self):
        caso = self.abrir().json()['case']
        revocado = self.post(f"/api/soporte/{caso['id']}/revocar").json()['case']
        self.assertIsNotNone(revocado['revokedAt'])
        self.assertEqual(revocado['state'], 'abierto')
        self.assertEqual(self.post(f"/api/soporte/{caso['id']}/revocar").status_code, 400)
        cancelado = self.post(f"/api/soporte/{caso['id']}/cancelar").json()['case']
        self.assertEqual(cancelado['state'], 'cancelado')
        self.assertEqual(self.post(f"/api/soporte/{caso['id']}/cancelar").status_code, 400)
        acciones = set(Auditoria.objects.filter(actor=self.dueña).values_list('accion', flat=True))
        self.assertTrue({'abrir_caso', 'revocar_soporte', 'cancelar_caso'} <= acciones)
        self.assertEqual(self.client.get(self.ruta).json()['history'][0]['state'], 'cancelado')

    def test_otra_cuenta_recibe_404(self):
        caso = self.abrir().json()['case']
        ajena = self.cliente(self.otra)
        self.assertEqual(ajena.get(self.ruta).status_code, 404)
        self.assertEqual(self.post(self.ruta, {'incident': 'bomba', 'consent': True}, ajena).status_code, 404)
        for accion in ('revocar', 'cancelar'):
            with self.subTest(accion=accion):
                self.assertEqual(self.post(f"/api/soporte/{caso['id']}/{accion}", cliente=ajena).status_code, 404)
        self.assertEqual(self.client.get(self.ruta).json()['active']['state'], 'abierto')

    def test_sin_equipo_no_hay_caso(self):
        sin_equipo = self.cliente(self.otra)
        huerto_id = self.crear_huerto(cliente=sin_equipo)
        respuesta = self.post(f'/api/huertos/{huerto_id}/soporte', {'incident': 'bomba', 'consent': True}, sin_equipo)
        self.assertEqual(respuesta.status_code, 400)

    def test_autodiagnostico_propio_y_ajeno(self):
        orden = self.post(f'/api/huertos/{self.huerto_id}/comandos', {'type': 'autodiagnostico'}).json()['command']
        propio = self.client.get(f"/api/autodiagnosticos/{orden['diagnosticId']}").json()['diagnostic']
        self.assertEqual((propio['state'], propio['checks']), ('en_curso', []))
        self.assertEqual(self.cliente(self.otra).get(f"/api/autodiagnosticos/{orden['diagnosticId']}").status_code, 404)

    def test_orden_igual_en_curso_responde_con_codigo(self):
        self.post(f'/api/huertos/{self.huerto_id}/comandos', {'type': 'autodiagnostico'})
        repetida = self.post(f'/api/huertos/{self.huerto_id}/comandos', {'type': 'autodiagnostico'})
        self.assertEqual((repetida.status_code, repetida.json()['code']), (409, 'orden-en-curso'))


class Avisos(BaseHuerto):
    def aviso(self, usuario, **campos):
        return Notificacion.objects.create(destinatario=usuario, origen='sistema', titulo='Aviso de prueba', **campos)

    def test_el_contador_baja_al_marcar_leido(self):
        avisos = [self.aviso(self.dueña) for _ in range(3)]
        self.aviso(self.otra)
        self.assertEqual(self.client.get('/api/avisos/contador').json()['unread'], 3)
        leido = self.post(f'/api/avisos/{avisos[0].pk}/leido').json()['notice']
        self.assertTrue(leido['read'])
        self.assertEqual(self.client.get('/api/avisos/contador').json()['unread'], 2)
        self.assertEqual(self.post(f'/api/avisos/{avisos[0].pk}/leido').status_code, 200)
        self.assertEqual(self.client.get('/api/avisos/contador').json()['unread'], 2)

    def test_leer_todos_solo_toca_los_propios(self):
        self.aviso(self.dueña), self.aviso(self.dueña)
        ajeno = self.aviso(self.otra)
        self.assertEqual(self.post('/api/avisos/leer-todos').json()['updated'], 2)
        self.assertEqual(self.client.get('/api/avisos/contador').json()['unread'], 0)
        ajeno.refresh_from_db()
        self.assertIsNone(ajeno.leida_en)

    def test_filtros_y_paginacion(self):
        Notificacion.objects.create(destinatario=self.dueña, origen='dispositivo', severidad='critico', titulo='Equipo')
        Notificacion.objects.create(destinatario=self.dueña, origen='soporte', titulo='Soporte')
        self.aviso(self.dueña)
        total = lambda filtro: self.client.get(f'/api/avisos?filtro={filtro}').json()['total']
        self.assertEqual([total(f) for f in ('todos', 'equipo', 'soporte', 'ia', 'legales', 'no_leidos')], [3, 1, 1, 0, 0, 3])
        for consulta in ('?filtro=otro', '?page=0', '?page=10001', '?x=1'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.client.get(f'/api/avisos{consulta}').status_code, 400)

    def test_resolver_solo_criticos_del_equipo(self):
        critico = Notificacion.objects.create(destinatario=self.dueña, origen='dispositivo', severidad='critico', titulo='Sin agua')
        normal = self.aviso(self.dueña)
        self.assertTrue(self.client.get(f'/api/avisos/{critico.pk}').json()['notice']['resolvable'])
        resuelto = self.post(f'/api/avisos/{critico.pk}/resuelto').json()['notice']
        self.assertIsNotNone(resuelto['resolvedAt'])
        self.assertEqual(self.post(f'/api/avisos/{normal.pk}/resuelto').status_code, 400)

    def test_otra_cuenta_recibe_404(self):
        mio = self.aviso(self.dueña)
        ajena = self.cliente(self.otra)
        self.assertEqual(ajena.get(f'/api/avisos/{mio.pk}').status_code, 404)
        for accion in ('leido', 'resuelto'):
            with self.subTest(accion=accion):
                self.assertEqual(self.post(f'/api/avisos/{mio.pk}/{accion}', cliente=ajena).status_code, 404)
        self.assertEqual(ajena.get('/api/avisos').json()['total'], 0)

    def test_el_administrador_tiene_sus_avisos(self):
        admin = cuenta('huerto-admin@example.test', 'atender_soporte')
        self.aviso(admin)
        sesion = self.cliente(admin)
        self.assertEqual(sesion.get('/api/avisos/contador').json()['unread'], 1)
        self.assertEqual(sesion.get('/api/avisos').json()['total'], 1)
        self.assertEqual(self.client.get('/api/avisos/contador').json()['unread'], 0)


@unittest.skipIf(simular_equipo is None, 'Esta copia no incluye el simulador')
class SimuladorDeEquipoEntorno(SimpleTestCase):
    BASE = {'CHILITO_ENV': 'local', 'CHILITO_DEBUG': '1', 'CHILITO_SIM_DB': 'test_chilito_x', 'CHILITO_SIM_CLAVE_IOT': 'x'}

    def test_se_niega_fuera_de_desarrollo(self):
        cambios = ({'CHILITO_DEBUG': '0'}, {'CHILITO_DEBUG': ''}, {'CHILITO_ENV': 'deployment'}, {'CHILITO_ENV': ''},
                   {'CHILITO_SIM_DB': 'chilito_produccion'}, {'CHILITO_SIM_DB': ''}, {'CHILITO_SIM_CLAVE_IOT': ''})
        for cambio in cambios:
            with self.subTest(cambio=cambio), self.assertRaises(SystemExit):
                simular_equipo.exigir_entorno({**self.BASE, **cambio})

    def test_usa_solo_el_rol_iot_y_sus_variables(self):
        ajustes = simular_equipo.exigir_entorno({**self.BASE, 'CHILITO_DB_USER': 'chilito_pkg_runtime', 'CHILITO_DB_PASSWORD': 'de-la-app'})
        self.assertEqual((ajustes['user'], ajustes['password'], ajustes['dbname']), ('chilito_pkg_iot', 'x', 'test_chilito_x'))


@unittest.skipIf(simular_equipo is None, 'Esta copia no incluye el simulador')
@unittest.skipUnless(os.environ.get('CHILITO_PRUEBAS_CLAVE_IOT'), 'Falta CHILITO_PRUEBAS_CLAVE_IOT para probar el rol IoT')
class SimuladorDeEquipo(AyudasHuerto, TransactionTestCase):
    """El simulador escribe con otra conexión (rol IoT), así que la prueba confirma sus datos en la base de pruebas."""

    def setUp(self):
        publicar_textos()
        super().setUp()

    def conexion_iot(self):
        ajustes = connection.settings_dict
        return psycopg.connect(**simular_equipo.exigir_entorno({
            'CHILITO_ENV': 'testing', 'CHILITO_DEBUG': '1', 'CHILITO_SIM_DB': ajustes['NAME'], 'CHILITO_SIM_HOST': ajustes['HOST'] or 'localhost',
            'CHILITO_SIM_PUERTO': str(ajustes['PORT'] or 5432), 'CHILITO_SIM_CLAVE_IOT': os.environ['CHILITO_PRUEBAS_CLAVE_IOT']}))

    def orden(self, huerto_id, **datos):
        respuesta = self.post(f'/api/huertos/{huerto_id}/comandos', datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()['command']

    def test_mediciones_ordenes_autodiagnostico_y_marca(self):
        huerto_id = self.huerto_con_equipo()
        riego = self.orden(huerto_id, type='regar', plant=2, duration=8)
        revision = self.orden(huerto_id, type='autodiagnostico')
        lampara = self.orden(huerto_id, type='lampara_apagar')
        with self.conexion_iot() as con:
            dispositivo = simular_equipo.equipo(con, 'CHI-0001')
            simular_equipo.marcar_simulado(con, dispositivo)
            simular_equipo.conexion(con, dispositivo, 'en_linea')
            simular_equipo.medir(con, dispositivo, cuantas=3, intervalo=60, luz=True)
            self.assertEqual(simular_equipo.atender(con, dispositivo, pausa=0, falla='bomba_2'), 3)
        estados = {orden['id']: self.client.get(f"/api/comandos/{orden['id']}").json()['command']['state'] for orden in (riego, revision, lampara)}
        self.assertEqual(set(estados.values()), {'confirmado'})
        diagnostico = self.client.get(f"/api/autodiagnosticos/{revision['diagnosticId']}").json()['diagnostic']
        self.assertEqual((diagnostico['state'], diagnostico['overall'], len(diagnostico['checks'])), ('completado', 'con_fallas', 12))
        self.assertEqual([c['component'] for c in diagnostico['checks']], list(simular_equipo.COMPONENTES))
        telemetria = self.client.get(f'/api/huertos/{huerto_id}/telemetria?rango=1h').json()
        self.assertEqual([len(planta['points']) for planta in telemetria['series']['plants']], [3, 3, 3])
        self.assertTrue(telemetria['hasLight'] and all(planta['adc'] is not None for planta in telemetria['plants']))
        detalle = self.client.get(f'/api/huertos/{huerto_id}').json()
        self.assertEqual((detalle['lamp']['state'], detalle['lamp']['mode']), ('off', 'manual-off'))
        self.assertEqual(detalle['garden']['device']['connection'], 'en_linea')
        eventos = self.client.get(f'/api/huertos/{huerto_id}/bitacora?tipo=eventos').json()['items']
        self.assertIn(('reinicio', 'simulador'), [(e['type'], e['detail']) for e in eventos])
        actuaciones = self.client.get(f'/api/huertos/{huerto_id}/bitacora?tipo=actuaciones').json()['items']
        self.assertIn(('bomba', 2, 'usuario'), [(a['actuator'], a['plant'], a['origin']) for a in actuaciones])

    def test_orden_fallida_y_equipo_desconectado(self):
        huerto_id = self.huerto_con_equipo()
        riego = self.orden(huerto_id, type='regar', plant=1, duration=5)
        with self.conexion_iot() as con:
            dispositivo = simular_equipo.equipo(con, 'CHI-0001')
            simular_equipo.atender(con, dispositivo, pausa=0, fallar=('regar',))
            simular_equipo.conexion(con, dispositivo, 'desconectado')
        resultado = self.client.get(f"/api/comandos/{riego['id']}").json()['command']
        self.assertEqual((resultado['state'], resultado['error']), ('fallido', 'Falla simulada'))
        self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}').json()['garden']['device']['connection'], 'desconectado')

    def test_solo_equipos_vinculados(self):
        equipo('CHI-0009', '02:00:00:00:00:09')
        with self.conexion_iot() as con, self.assertRaises(SystemExit):
            simular_equipo.equipo(con, 'CHI-0009')
