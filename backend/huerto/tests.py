"""Sobre PostgreSQL: huertos, plantas, órdenes, vinculación del equipo y aceptación de textos."""
import importlib
import io
import json
import os
import unittest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
import psycopg
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from datos.models import (Auditoria, CodigoVinculacion, Comando, Cuidado, CuidadoRevision, DepositoDeteccion, Dispositivo,
                          DispositivoEvento, Medicion, MedicionPlanta, Notificacion)
from huerto.models import Huerto, Planta, PlantaEtapa
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

    def test_huerto_nuevo_nace_con_su_etapa_inicial(self):
        huerto_id = self.crear_huerto()
        filas = list(PlantaEtapa.objects.filter(planta__huerto_id=huerto_id).order_by('planta__numero')
                     .values_list('planta__numero', 'etapa', 'desde', 'registrada_por_id'))
        hoy = timezone.localdate()
        self.assertEqual(filas, [(n, 'sin_sembrar', hoy, self.dueña.pk) for n in (1, 2, 3)])
        etapas = self.client.get(f'/api/huertos/{huerto_id}/plantas/1').json()['stages']
        self.assertEqual(etapas, [{'stage': 'sin_sembrar', 'since': hoy.isoformat()}])

    def test_cambiar_etapa_agrega_en_orden(self):
        huerto_id = self.crear_huerto()
        respuesta = self.post(f'/api/huertos/{huerto_id}/plantas/1', {'stage': 'germinacion'})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        etapas = self.client.get(f'/api/huertos/{huerto_id}/plantas/1').json()['stages']
        self.assertEqual([e['stage'] for e in etapas], ['sin_sembrar', 'germinacion'])
        self.assertEqual(PlantaEtapa.objects.filter(planta__huerto_id=huerto_id, planta__numero=1).count(), 2)

    def test_relleno_no_duplica(self):
        relleno = importlib.import_module('web.migrations.0003_linea_de_vida').RELLENO
        primero = self.crear_huerto()
        self.post(f'/api/huertos/{primero}/plantas/1', {'stage': 'germinacion'})
        with connection.cursor() as cursor:
            cursor.execute(relleno)
            self.assertEqual(cursor.rowcount, 0, 'las plantas con historial no reciben otra fila')
            # Un huerto como los de antes de la migración: sus plantas nacen sin fila de historial.
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')   # ALTER TABLE no admite comprobaciones pendientes
            cursor.execute('ALTER TABLE huerto_planta DISABLE TRIGGER planta_etapa_inicial')
            segundo = Huerto.objects.create(propietario=self.otra).pk
            cursor.execute('ALTER TABLE huerto_planta ENABLE TRIGGER planta_etapa_inicial')
            self.assertFalse(PlantaEtapa.objects.filter(planta__huerto_id=segundo).exists())
            cursor.execute(relleno)
            self.assertEqual(cursor.rowcount, 3)
            cursor.execute(relleno)
            self.assertEqual(cursor.rowcount, 0)
        creado = timezone.localtime(Huerto.objects.get(pk=segundo).creado_en, ZoneInfo('America/Merida')).date()
        self.assertEqual(sorted(PlantaEtapa.objects.filter(planta__huerto_id=segundo).values_list('planta__numero', 'etapa', 'desde')),
                         [(n, 'sin_sembrar', creado) for n in (1, 2, 3)])
        self.assertEqual(PlantaEtapa.objects.filter(planta__huerto_id=primero).count(), 4)

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

    def test_ultimos_por_tipo_no_dependen_de_la_pagina(self):
        hace = lambda horas: timezone.now() - timedelta(hours=horas)
        Cuidado.objects.create(huerto_id=self.huerto_id, tipo='cosecha', planta_numero=2, chiles_cosechados=4, realizado_en=hace(100), registrado_por=self.dueña)
        anulada = Cuidado.objects.create(huerto_id=self.huerto_id, tipo='cosecha', planta_numero=1, realizado_en=hace(90), registrado_por=self.dueña)
        CuidadoRevision.objects.create(cuidado=anulada, numero=1, tipo='anulacion', motivo='Duplicado', editor=self.editor)
        for numero in range(30):      # más de una página de inspecciones, todas más recientes que la cosecha
            Cuidado.objects.create(huerto_id=self.huerto_id, tipo='inspeccion', realizado_en=hace(80 - numero), registrado_por=self.dueña)
        datos = self.listar().json()
        self.assertTrue(all(fila['type'] == 'inspeccion' for fila in datos['items']), 'la cosecha no está en la página 1')
        ultimos = datos['latest']
        self.assertEqual((ultimos['cosecha']['plant'], ultimos['cosecha']['chiles']), (2, 4), 'la anulada no cuenta')
        self.assertEqual(ultimos['inspeccion']['doneAt'], datos['items'][0]['doneAt'])
        self.assertIsNone(ultimos['sustrato'])
        self.assertIsNone(ultimos['rellenar_deposito'])
        self.assertNotIn('latest', self.listar('?page=2').json())
        self.assertNotIn('latest', self.listar('?tipo=cosecha').json())

    def test_otra_cuenta(self):
        ajena = self.cliente(self.otra)
        self.assertEqual(ajena.get(f'/api/huertos/{self.huerto_id}/cuidados').status_code, 404)
        self.assertEqual(self.post(f'/api/huertos/{self.huerto_id}/cuidados', {'type': 'rellenar_deposito'}, ajena).status_code, 404)


class Deposito(BaseHuerto):
    """El flotador: nivel bajo y recargas detectadas (por confirmar) en la base, límites de la recarga manual y duración de cada carga."""
    HORA = 60

    def setUp(self):
        super().setUp()
        self.editor = cuenta('deposito-editor@example.test', 'gestionar_mantenimientos')
        self.huerto_id = self.huerto_con_equipo()

    def flotador(self, *lecturas, huerto_id=None, confirmar=False):
        """Mediciones en orden: (horas atrás, con agua). Con `confirmar`, el dueño confirma cada recarga detectada."""
        for horas, con_agua in lecturas:
            medir(huerto_id or self.huerto_id, horas * self.HORA, deposito_con_agua=con_agua)
            if confirmar and (pendiente := self.pendiente()):
                self.assertEqual(self.confirmar(pendiente).status_code, 200)

    def pendiente(self):
        return DepositoDeteccion.objects.filter(huerto_id=self.huerto_id, estado='pendiente').first()

    def confirmar(self, deteccion, cliente=None):
        return self.post(f'/api/huertos/{self.huerto_id}/deposito/detecciones/{deteccion.pk}/confirmar', cliente=cliente)

    def descartar(self, deteccion, cliente=None):
        return self.post(f'/api/huertos/{self.huerto_id}/deposito/detecciones/{deteccion.pk}/descartar', cliente=cliente)

    def recargas(self, origen=None):
        filas = Cuidado.objects.filter(huerto_id=self.huerto_id, tipo='rellenar_deposito')
        return filas.filter(origen=origen) if origen else filas

    def registrar(self, huerto_id=None, **datos):
        return self.post(f"/api/huertos/{huerto_id or self.huerto_id}/cuidados", {'type': 'rellenar_deposito', **datos})

    def deposito(self, huerto_id=None):
        respuesta = self.client.get(f"/api/huertos/{huerto_id or self.huerto_id}/deposito")
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def hace(self, horas):
        return (timezone.now() - timedelta(hours=horas)).isoformat()

    def anular(self, cuidado, motivo='Prueba'):
        CuidadoRevision.objects.create(cuidado=cuidado, numero=1, tipo='anulacion', motivo=motivo, editor=self.editor)

    def assertHoras(self, segundos, horas):
        self.assertAlmostEqual(segundos, horas * 3600, delta=5)

    def assertRechazoBase(self, **campos):
        with self.assertRaises(IntegrityError) as fallo, transaction.atomic():
            Cuidado.objects.create(huerto_id=self.huerto_id, tipo='rellenar_deposito', registrado_por=self.dueña, **campos)
        self.assertEqual(fallo.exception.__cause__.sqlstate, '23514')
        return str(fallo.exception)

    # ── Detección automática ──
    def test_bajar_crea_evento_y_aviso_una_vez(self):
        self.flotador((3, True), (2, False), (1, False))
        self.assertEqual(DispositivoEvento.objects.filter(huerto_id=self.huerto_id, tipo='deposito_bajo').count(), 1)
        avisos = Notificacion.objects.filter(destinatario=self.dueña, titulo='Tu depósito necesita agua')
        self.assertEqual((avisos.count(), avisos.first().severidad, avisos.first().enlace), (1, 'advertencia', '#huerto'))
        self.assertEqual(avisos.first().texto, 'Tu depósito se quedó sin agua. Rellénalo y avísanos.')
        tanque = self.client.get(f'/api/huertos/{self.huerto_id}').json()['tank']
        self.assertEqual((tanque['hasWater'], tanque['canRefill']), (False, True))
        bajo = DispositivoEvento.objects.get(huerto_id=self.huerto_id, tipo='deposito_bajo').ocurrido_en
        self.assertEqual(tanque['lowSince'], bajo.isoformat())

    def test_deteccion_queda_pendiente_sin_cuidado(self):
        self.flotador((4, True), (3, False), (2, True), (1, True))
        self.assertFalse(self.recargas().exists())
        deteccion = DepositoDeteccion.objects.get(huerto_id=self.huerto_id)
        medida = Medicion.objects.filter(huerto_id=self.huerto_id).order_by('medida_en')[2].medida_en
        self.assertEqual((deteccion.estado, deteccion.detectada_en, deteccion.cuidado_id, deteccion.decidida_por_id), ('pendiente', medida, None, None))
        self.assertEqual(DispositivoEvento.objects.filter(huerto_id=self.huerto_id, tipo='deposito_recargado').count(), 1)
        self.assertIsNotNone(Notificacion.objects.get(titulo='Tu depósito necesita agua').resuelta_en)
        aviso = Notificacion.objects.get(destinatario=self.dueña, titulo='Confirma la recarga de tu depósito')
        hora = medida.astimezone(ZoneInfo('America/Merida')).strftime('%d/%m/%Y a las %H:%M')
        self.assertEqual((aviso.texto, aviso.enlace, aviso.resuelta_en), (f'Tu equipo detectó agua en el depósito el {hora}. ¿Ya lo rellenaste?', '#huerto', None))
        tanque = self.deposito()['tank']
        self.assertEqual(tanque['state'], 'detectada')
        self.assertEqual(tanque['pendingRefill'], {'id': str(deteccion.pk), 'detectedAt': medida.isoformat()})
        self.assertEqual((tanque['lastRefill'], tanque['canRefill'], tanque['completedLoads']), (None, True, 0))
        self.assertEqual(self.client.get(f'/api/huertos/{self.huerto_id}').json()['tank']['pendingRefill']['id'], str(deteccion.pk))
        self.assertEqual(self.client.get(f'/api/huertos/{self.huerto_id}/cuidados').json()['items'], [])

    def test_confirmar_crea_un_solo_cuidado_con_la_hora_detectada(self):
        self.flotador((3, True), (2, False), (1, True))
        deteccion = self.pendiente()
        respuesta = self.confirmar(deteccion)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        recarga = self.recargas().get()
        self.assertEqual((recarga.origen, recarga.registrado_por_id, recarga.realizado_en), ('equipo', self.dueña.pk, deteccion.detectada_en))
        deteccion.refresh_from_db()
        self.assertEqual((deteccion.estado, deteccion.cuidado_id, deteccion.decidida_por_id), ('confirmada', recarga.pk, self.dueña.pk))
        self.assertIsNotNone(deteccion.decidida_en)
        self.assertIsNotNone(Notificacion.objects.get(titulo='Confirma la recarga de tu depósito').resuelta_en)
        cuerpo = respuesta.json()
        self.assertEqual((cuerpo['care']['origin'], cuerpo['care']['confirmed'], cuerpo['care']['byOwner']), ('equipo', True, True))
        self.assertIsNone(cuerpo['tank']['pendingRefill'])
        ultima = self.deposito()['tank']['lastRefill']
        self.assertEqual((ultima['origin'], ultima['confirmed'], ultima['byOwner'], ultima['at']), ('equipo', True, True, deteccion.detectada_en.isoformat()))
        fila = self.client.get(f'/api/huertos/{self.huerto_id}/cuidados').json()['items'][0]
        self.assertEqual((fila['origin'], fila['confirmed'], fila['byOwner']), ('equipo', True, True))
        otra = self.confirmar(deteccion)                     # repetir el clic no duplica
        self.assertEqual((otra.status_code, otra.json()['code']), (409, 'deposito-resuelta'))
        self.assertEqual(self.registrar().json()['code'], 'deposito-con-agua')
        self.assertEqual(self.recargas().count(), 1)

    def test_descartar_no_crea_nada(self):
        self.flotador((3, True), (2, False), (1, True))
        deteccion = self.pendiente()
        respuesta = self.descartar(deteccion)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        deteccion.refresh_from_db()
        self.assertEqual((deteccion.estado, deteccion.cuidado_id, deteccion.decidida_por_id), ('descartada', None, self.dueña.pk))
        self.assertFalse(self.recargas().exists())
        self.assertIsNone(respuesta.json()['tank']['pendingRefill'])
        self.assertIsNotNone(Notificacion.objects.get(titulo='Confirma la recarga de tu depósito').resuelta_en)
        self.assertEqual(self.confirmar(deteccion).json()['code'], 'deposito-resuelta')
        self.assertFalse(self.recargas().exists())

    def test_nivel_bajo_con_pendiente_la_deja_sin_confirmar(self):
        self.flotador((4, True), (3, False), (2, True))
        deteccion = self.pendiente()
        self.flotador((1, False))
        deteccion.refresh_from_db()
        self.assertEqual((deteccion.estado, deteccion.decidida_por_id, deteccion.cuidado_id), ('sin_confirmar', None, None))
        self.assertIsNotNone(deteccion.decidida_en)
        self.assertIsNotNone(Notificacion.objects.get(titulo='Confirma la recarga de tu depósito').resuelta_en)
        self.assertEqual(self.confirmar(deteccion).json()['code'], 'deposito-resuelta')
        self.assertFalse(self.recargas().exists())
        self.assertIsNone(self.deposito()['tank']['pendingRefill'])
        self.flotador((0.5, True))                           # la siguiente recarga se detecta de nuevo
        self.assertEqual(DepositoDeteccion.objects.filter(huerto_id=self.huerto_id, estado='pendiente').count(), 1)

    def test_manual_con_pendiente_confirma_sin_duplicar(self):
        self.flotador((3, True), (2, False), (1, True))
        deteccion = self.pendiente()
        respuesta = self.registrar(doneAt=self.hace(0.1))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        recarga = self.recargas().get()
        self.assertEqual((recarga.origen, recarga.registrado_por_id, recarga.realizado_en), ('equipo', self.dueña.pk, deteccion.detectada_en))
        deteccion.refresh_from_db()
        self.assertEqual((deteccion.estado, deteccion.cuidado_id), ('confirmada', recarga.pk))
        self.assertEqual(respuesta.json()['care']['confirmed'], True)
        self.assertEqual(self.registrar().json()['code'], 'deposito-con-agua')
        self.assertEqual(self.recargas().count(), 1)

    def test_solo_el_dueno_confirma_o_descarta(self):
        self.flotador((3, True), (2, False), (1, True))
        deteccion = self.pendiente()
        otra = self.cliente(self.otra)
        self.assertEqual(self.confirmar(deteccion, otra).status_code, 404)
        self.assertEqual(self.descartar(deteccion, otra).status_code, 404)
        self.assertEqual(self.confirmar(deteccion, self.cliente(self.editor)).status_code, 404)
        self.assertEqual(self.client.post(f'/api/huertos/{self.huerto_id}/deposito/detecciones/{deteccion.pk}/confirmar').status_code, 400)  # sin recibo
        ajena = self.post(f'/api/huertos/{self.huerto_id}/deposito/detecciones/{uuid.uuid4()}/confirmar')
        self.assertEqual(ajena.status_code, 404)
        # La base lo exige también: nadie más descarta, nadie la cierra a mano ni la crea.
        for cambios in ({'estado': 'descartada', 'decidida_por': self.otra, 'decidida_en': timezone.now()},
                        {'estado': 'sin_confirmar', 'decidida_en': timezone.now()}):
            with self.subTest(cambios=cambios), self.assertRaises(IntegrityError), transaction.atomic():
                DepositoDeteccion.objects.filter(pk=deteccion.pk).update(**cambios)
        with self.assertRaises(IntegrityError), transaction.atomic():
            DepositoDeteccion.objects.create(huerto_id=self.huerto_id, detectada_en=timezone.now())
        with self.assertRaises(IntegrityError), transaction.atomic():
            DepositoDeteccion.objects.filter(pk=deteccion.pk).delete()
        self.assertEqual((self.pendiente(), self.recargas().count()), (deteccion, 0))

    def test_recarga_manual_reciente_no_pide_confirmacion(self):
        self.flotador((2, True), (1, False))
        self.assertEqual(self.registrar(doneAt=self.hace(0.5)).status_code, 200)
        self.flotador((0.2, True))
        self.assertEqual([(r.origen, r.registrado_por_id) for r in self.recargas()], [('persona', self.dueña.pk)])
        self.assertFalse(DepositoDeteccion.objects.filter(huerto_id=self.huerto_id).exists())
        self.assertTrue(self.deposito()['tank']['lastRefill']['byOwner'])

    def test_recarga_registrada_en_el_nivel_bajo_no_pide_confirmacion(self):
        """Más allá de los 30 minutos: si la persona ya avisó en este nivel bajo, el agua detectada es esa recarga."""
        self.flotador((5, True), (4, False))
        self.assertEqual(self.registrar(doneAt=self.hace(3)).status_code, 200)
        self.flotador((1, True))
        self.assertEqual(list(self.recargas().values_list('origen', flat=True)), ['persona'])
        self.assertIsNone(self.pendiente())
        self.assertEqual(self.deposito()['tank']['state'], 'con_agua')

    def test_recargas_automaticas_anteriores_siguen_contando(self):
        """Las que creó la 0004 (origen equipo, sin autor) se quedan: cuentan como recargas y no como confirmadas."""
        self.flotador((50, True), (49, False))
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')     # sin eventos pendientes no se puede alterar la tabla
            cursor.execute('ALTER TABLE cuidado DISABLE TRIGGER cuidado_reglas')
            cursor.execute("INSERT INTO cuidado(huerto_id, tipo, origen, realizado_en) VALUES (%s, 'rellenar_deposito', 'equipo', %s)",
                           [self.huerto_id, timezone.now() - timedelta(hours=40)])
            cursor.execute('ALTER TABLE cuidado ENABLE TRIGGER cuidado_reglas')
        self.flotador((30, True), (20, False))      # esta detección queda sin confirmar
        tanque = self.deposito()['tank']
        self.assertHoras(tanque['averageSeconds'], 20)
        self.assertEqual((tanque['lastRefill']['origin'], tanque['lastRefill']['confirmed']), ('equipo', False))
        fila = self.client.get(f'/api/huertos/{self.huerto_id}/cuidados').json()['items'][0]
        self.assertEqual((fila['origin'], fila['confirmed']), ('equipo', False))

    def test_origen_equipo_no_se_registra_a_mano(self):
        self.flotador((1, False))
        for campos in ({'origen': 'equipo', 'registrado_por': None}, {'origen': 'equipo'}):
            with self.subTest(campos=campos), self.assertRaises(IntegrityError), transaction.atomic():
                Cuidado.objects.create(huerto_id=self.huerto_id, tipo='rellenar_deposito', **{'registrado_por': self.dueña, **campos})

    # ── Estados de la tarjeta Depósito (1 a 6) ──
    def estado(self):
        return self.deposito()['tank']

    def test_estado_1_con_agua_tras_registrar_o_confirmar(self):
        self.flotador((5, True), (4, False))
        self.assertEqual(self.registrar().status_code, 200)
        self.flotador((0, True))
        tanque = self.estado()
        self.assertEqual((tanque['state'], tanque['pendingRefill'], tanque['canRefill'], tanque['lastRefill']['byOwner'], tanque['lastRefill']['origin']),
                         ('con_agua', None, False, True, 'persona'))

    def test_estado_2_nivel_bajo_pide_rellenar_con_un_solo_aviso(self):
        self.flotador((3, True), (2, False), (1, False))
        tanque = self.estado()
        self.assertEqual((tanque['state'], tanque['pendingRefill'], tanque['canRefill']), ('rellenar', None, True))
        self.assertFalse(DepositoDeteccion.objects.filter(huerto_id=self.huerto_id).exists())
        aviso = Notificacion.objects.get(destinatario=self.dueña, origen='dispositivo', titulo='Tu depósito necesita agua')
        self.assertEqual((aviso.texto, aviso.enlace, aviso.resuelta_en), ('Tu depósito se quedó sin agua. Rellénalo y avísanos.', '#huerto', None))
        self.assertFalse(Notificacion.objects.filter(titulo='Confirma la recarga de tu depósito').exists())

    def test_avisos_del_deposito_enlazan_a_mantenimiento(self):
        """La base guarda #huerto; la API lleva los dos avisos del depósito a Mantenimiento, donde se rellena o se confirma."""
        self.flotador((3, True), (2, False), (1, True))
        enlaces = {aviso['title']: aviso['link'] for aviso in self.client.get('/api/avisos').json()['items']}
        self.assertEqual(enlaces['Tu depósito necesita agua'], '#mantenimiento')
        self.assertEqual(enlaces['Confirma la recarga de tu depósito'], '#mantenimiento')
        aviso = Notificacion.objects.get(destinatario=self.dueña, titulo='Confirma la recarga de tu depósito')
        self.assertEqual(aviso.enlace, '#huerto')                                         # la base no cambia
        self.assertEqual(self.client.get(f'/api/avisos/{aviso.pk}').json()['notice']['link'], '#mantenimiento')

    def test_estado_3_ya_lo_rellene_registra_con_la_hora_de_confirmacion(self):
        self.flotador((2, True), (1, False))
        respuesta = self.registrar()                          # «Sí, ya lo rellené»: sin fecha, la hora de confirmación
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        recarga = self.recargas().get()
        self.assertEqual((recarga.origen, recarga.registrado_por_id), ('persona', self.dueña.pk))
        self.assertAlmostEqual((timezone.now() - recarga.realizado_en).total_seconds(), 0, delta=60)
        self.assertIsNotNone(Notificacion.objects.get(titulo='Tu depósito necesita agua').resuelta_en)
        tanque = self.estado()
        self.assertEqual((tanque['state'], tanque['canRefill'], tanque['refillBlock']), ('esperando_lectura', False, 'repetida'))
        self.assertEqual(self.registrar().json()['code'], 'deposito-repetida')
        self.assertEqual(self.recargas().count(), 1)

    def test_estado_4_agua_sin_aviso_pregunta_y_registra_con_la_hora_detectada(self):
        self.flotador((3, True), (2, False), (1, True))
        deteccion = self.pendiente()
        tanque = self.estado()
        self.assertEqual((tanque['state'], tanque['pendingRefill']['id']), ('detectada', str(deteccion.pk)))
        self.assertEqual(self.confirmar(deteccion).status_code, 200)
        self.assertEqual(self.recargas().get().realizado_en, deteccion.detectada_en)
        tanque = self.estado()
        self.assertEqual((tanque['state'], tanque['pendingRefill'], tanque['lastRefill']['origin'], tanque['lastRefill']['confirmed']),
                         ('con_agua', None, 'equipo', True))

    def test_estado_5_registrada_pero_sigue_en_nivel_bajo(self):
        self.flotador((2, True), (1, False))
        self.assertEqual(self.registrar().status_code, 200)
        medir(self.huerto_id, 0, deposito_con_agua=False)      # la siguiente lectura sigue baja
        tanque = self.estado()
        self.assertEqual((tanque['state'], tanque['canRefill'], tanque['refillBlock'], tanque['lastRefill']['byOwner']), ('sigue_bajo', False, 'repetida', True))
        self.assertEqual(self.recargas().count(), 1)              # el registro no se borra
        self.assertEqual(Notificacion.objects.filter(titulo='Tu depósito necesita agua').count(), 1)
        self.assertEqual(self.registrar().json()['code'], 'deposito-repetida')
        self.assertIn('Ya registraste esta recarga', self.assertRechazoBase())
        medir(self.huerto_id, -1, deposito_con_agua=True)      # cuando por fin detecta agua, es esa recarga
        self.assertIsNone(self.pendiente())
        self.assertEqual((self.estado()['state'], self.recargas().count()), ('con_agua', 1))

    def test_estado_6_sin_deteccion_real_no_hay_pregunta(self):
        self.flotador((1, False))                               # solo «medir --sin-agua»
        tanque = self.client.get(f'/api/huertos/{self.huerto_id}').json()['tank']
        self.assertEqual((tanque['state'], tanque['pendingRefill']), ('rellenar', None))
        self.flotador((0.5, True), (0.2, False))                # la detección quedó sin confirmar
        self.assertEqual(DepositoDeteccion.objects.get(huerto_id=self.huerto_id).estado, 'sin_confirmar')
        self.assertEqual((self.estado()['state'], self.estado()['pendingRefill']), ('rellenar', None))

    # ── Recarga manual con equipo ──
    def test_manual_rechazado_con_agua_y_sin_nivel_bajo_previo(self):
        self.flotador((1, True))
        respuesta = self.registrar()
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'deposito-con-agua'))
        self.assertIn('Tu depósito tiene agua: podrás registrar una recarga', self.assertRechazoBase())
        tanque = self.deposito()['tank']
        self.assertEqual((tanque['canRefill'], tanque['refillBlock']), (False, 'con-agua'))
        self.flotador((0.5, False), (0.2, True), confirmar=True)   # la recarga confirmada tampoco deja registrar otra
        self.assertEqual(self.registrar().json()['code'], 'deposito-con-agua')
        self.assertIn('Tu depósito tiene agua desde tu última recarga', self.assertRechazoBase())
        self.assertEqual(self.recargas().count(), 1)

    def test_manual_permitido_tras_nivel_bajo_y_una_sola_vez(self):
        self.flotador((2, True), (1, False))
        self.assertEqual(self.registrar().status_code, 200)
        segunda = self.registrar()
        self.assertEqual((segunda.status_code, segunda.json()['code']), (409, 'deposito-repetida'))
        self.assertIn('Ya registraste esta recarga', self.assertRechazoBase())

    def test_admin_tambien_respeta_la_regla_y_anula_la_del_equipo(self):
        admin = self.cliente(self.editor)
        self.flotador((3, True), (2, False), (1, True), confirmar=True)
        respuesta = self.post('/api/admin/mantenimientos', {'garden': self.huerto_id, 'type': 'rellenar_deposito'}, admin)
        self.assertEqual(respuesta.json().get('code'), 'deposito-con-agua')
        self.anular(self.recargas('equipo').get(), 'El flotador rebotó')
        tanque = self.deposito()['tank']
        self.assertEqual((tanque['lastRefill'], tanque['canRefill'], tanque['refillBlock']), (None, False, 'con-agua'))  # hay agua

    def test_registro_del_admin_con_pendiente_tambien_la_confirma(self):
        self.flotador((3, True), (2, False), (1, True))
        deteccion = self.pendiente()
        respuesta = self.post('/api/admin/mantenimientos', {'garden': self.huerto_id, 'type': 'rellenar_deposito'}, self.cliente(self.editor))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        deteccion.refresh_from_db()
        self.assertEqual((deteccion.estado, deteccion.decidida_por_id), ('confirmada', self.editor.pk))
        self.assertEqual(self.deposito()['tank']['lastRefill']['byOwner'], False)

    # ── Huerto sin equipo ──
    def test_sin_equipo_una_recarga_cada_12_horas(self):
        huerto = self.crear_huerto('Sin equipo')
        self.assertEqual(self.registrar(huerto, doneAt=self.hace(13)).status_code, 200)
        self.assertEqual(self.registrar(huerto).status_code, 200)
        respuesta = self.registrar(huerto, doneAt=self.hace(1))
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'deposito-espera'))
        self.assertIn('Podrás', respuesta.json()['message'].replace('podrás', 'Podrás'))
        tanque = self.deposito(huerto)['tank']
        ultima = Cuidado.objects.filter(huerto_id=huerto).order_by('-realizado_en').first().realizado_en
        self.assertEqual((tanque['hasDevice'], tanque['canRefill'], tanque['refillBlock']), (False, False, 'espera'))
        self.assertEqual(tanque['nextRefillAt'], (ultima + timedelta(hours=12)).isoformat())
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cuidado.objects.create(huerto_id=huerto, tipo='rellenar_deposito', registrado_por=self.dueña)

    def test_sin_equipo_muestra_la_frecuencia(self):
        huerto = self.crear_huerto('Sin equipo')
        self.registrar(huerto, doneAt=self.hace(24 * 6))
        self.assertIsNone(self.deposito(huerto)['tank']['refillEverySeconds'])
        for horas in (24 * 4, 24 * 2):
            self.assertEqual(self.registrar(huerto, doneAt=self.hace(horas)).status_code, 200)
        tanque = self.deposito(huerto)['tank']
        self.assertHoras(tanque['refillEverySeconds'], 48)
        self.assertEqual((tanque['averageSeconds'], tanque['estimatedLowAt'], self.deposito(huerto)['loads']), (None, None, []))

    # ── Duración del depósito ──
    def test_duracion_promedio_y_descarte_de_rebotes(self):
        self.flotador((150, True), (149, False), (140, True), (100, False), (99, True), (79, False),
                      (78, True), (77.5, False), (70, True), (40, False), (10, True), confirmar=True)
        datos = self.deposito()
        tanque, cargas = datos['tank'], datos['loads']
        self.assertEqual(tanque['completedLoads'], 3)                        # la de media hora es rebote
        self.assertHoras(tanque['averageSeconds'], 30)                       # (40 + 20 + 30) / 3
        estimada = datetime.fromisoformat(tanque['estimatedLowAt'])
        self.assertAlmostEqual((estimada - timezone.now()).total_seconds(), 20 * 3600, delta=5)
        self.assertEqual([c['lowAt'] is None for c in cargas], [True, False, False, False])
        for carga, horas in zip(cargas[1:], (30, 20, 40)):
            self.assertHoras(carga['seconds'], horas)
        self.assertEqual({c['origin'] for c in cargas}, {'equipo'})

    def test_promedio_de_las_ultimas_cinco(self):
        lecturas, hora = [(160, True), (159, False)], 150
        for duracion in (2, 10, 10, 10, 10, 10):
            lecturas += [(hora, True), (hora - duracion, False)]
            hora -= duracion + 1
        self.flotador(*lecturas, confirmar=True)
        tanque = self.deposito()['tank']
        self.assertEqual(tanque['completedLoads'], 6)
        self.assertHoras(tanque['averageSeconds'], 10)
        self.assertEqual(tanque['averageLoads'], 5)                          # el promedio usa las últimas 5

    def test_anuladas_no_cuentan(self):
        self.flotador((50, True), (49, False), (40, True), (20, False), (10, True), confirmar=True)
        self.assertHoras(self.deposito()['tank']['averageSeconds'], 20)
        primera = self.recargas().order_by('realizado_en').first()
        self.anular(primera)
        tanque = self.deposito()['tank']
        self.assertEqual((tanque['completedLoads'], tanque['averageSeconds'], tanque['estimatedLowAt']), (0, None, None))

    def test_sin_cargas_completas(self):
        self.flotador((3, True), (2, False), (1, True), confirmar=True)
        datos = self.deposito()
        self.assertEqual((datos['tank']['completedLoads'], datos['tank']['averageSeconds'], datos['tank']['estimatedLowAt']), (0, None, None))
        self.assertEqual([(c['origin'], c['lowAt'], c['seconds']) for c in datos['loads']], [('equipo', None, None)])

    def test_estimacion_solo_con_la_carga_abierta(self):
        self.flotador((50, True), (49, False), (40, True), (20, False), confirmar=True)
        tanque = self.deposito()['tank']
        self.assertHoras(tanque['averageSeconds'], 20)
        self.assertIsNone(tanque['estimatedLowAt'])
        self.flotador((1, True), confirmar=True)
        self.assertIsNotNone(self.deposito()['tank']['estimatedLowAt'])

    def test_promedio_ignora_las_no_confirmadas(self):
        self.flotador((60, True), (59, False), (50, True), confirmar=True)
        self.flotador((30, False), (20, True), (15, False), (10, True))     # una queda sin confirmar
        self.assertEqual(self.descartar(self.pendiente()).status_code, 200)  # y otra no fue una recarga
        datos = self.deposito()
        tanque = datos['tank']
        self.assertEqual((tanque['completedLoads'], tanque['estimatedLowAt'], tanque['lastRefill']['confirmed']), (1, None, True))
        self.assertHoras(tanque['averageSeconds'], 20)
        self.assertEqual([(c['origin'], c['confirmed']) for c in datos['loads']], [('equipo', True)])
        self.assertEqual(sorted(DepositoDeteccion.objects.filter(huerto_id=self.huerto_id).values_list('estado', flat=True)),
                         ['confirmada', 'descartada', 'sin_confirmar'])

    def test_otra_cuenta(self):
        self.assertEqual(self.cliente(self.otra).get(f'/api/huertos/{self.huerto_id}/deposito').status_code, 404)


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
        self.assertNotIn('attendedBy', caso, 'frente a la persona el administrador es solo «Soporte»: no se expone su alias')
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

    def test_solo_los_avisos_del_deposito_cambian_de_enlace(self):
        Notificacion.objects.create(destinatario=self.dueña, origen='dispositivo', titulo='Tu equipo se conectó', enlace='#huerto')
        Notificacion.objects.create(destinatario=self.dueña, origen='sistema', titulo='Tu depósito necesita agua', enlace='#huerto')
        Notificacion.objects.create(destinatario=self.dueña, origen='dispositivo', titulo='Tu depósito necesita agua', enlace='')
        enlaces = sorted((a['origin'], a['title'], a['link'] or '') for a in self.client.get('/api/avisos').json()['items'])
        self.assertEqual(enlaces, [('dispositivo', 'Tu depósito necesita agua', ''), ('dispositivo', 'Tu equipo se conectó', '#huerto'),
                                   ('sistema', 'Tu depósito necesita agua', '#huerto')])

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

    def test_argumentos_del_deposito(self):
        argumentos = simular_equipo.leer_argumentos(['CHI-1', 'medir', '--sin-agua', '--hace', '48'])
        self.assertEqual((argumentos.sin_agua, argumentos.hace), (True, 48.0))
        self.assertEqual(simular_equipo.leer_argumentos(['CHI-1', 'correr']).hace, 0.0)

    def test_usa_solo_el_rol_iot_y_sus_variables(self):
        ajustes = simular_equipo.exigir_entorno({**self.BASE, 'CHILITO_DB_USER': 'chilito_pkg_runtime', 'CHILITO_DB_PASSWORD': 'de-la-app'})
        self.assertEqual((ajustes['user'], ajustes['password'], ajustes['dbname']), ('chilito_pkg_iot', 'x', 'test_chilito_x'))


@unittest.skipIf(simular_equipo is None, 'Esta copia no incluye el simulador')
class SimuladorCorrerSinAgua(SimpleTestCase):
    """«correr --sin-agua» llega hasta cada medición: el flotador marca nivel bajo en todos los ciclos."""

    def test_main_pasa_sin_agua_a_correr_y_a_cada_medicion(self):
        self.assertTrue(simular_equipo.leer_argumentos(['CHI-1', 'correr', '--sin-agua']).sin_agua)
        self.assertFalse(simular_equipo.leer_argumentos(['CHI-1', 'correr']).sin_agua)
        mediciones = []
        with patch.object(simular_equipo, 'exigir_entorno', return_value={}), patch.object(simular_equipo.psycopg, 'connect'), \
                patch.object(simular_equipo, 'equipo', return_value={'id': 1, 'huerto': 1, 'firmware': 'x'}), \
                patch.object(simular_equipo, 'marcar_simulado'), patch.object(simular_equipo, 'conexion'), \
                patch.object(simular_equipo, 'atender', return_value=0), patch.object(simular_equipo.time, 'sleep'), \
                patch.object(simular_equipo, 'medir', side_effect=lambda *a, **k: mediciones.append(k.get('sin_agua'))):
            simular_equipo.main(['CHI-1', 'correr', '--sin-agua', '--ciclos', '3', '--cada', '0'])
            simular_equipo.main(['CHI-1', 'correr', '--ciclos', '2', '--cada', '0'])
        self.assertEqual(mediciones, [True, True, True, False, False])


@unittest.skipIf(simular_equipo is None, 'Esta copia no incluye el simulador')
class SimuladorVincula(BaseHuerto):
    """«vincular» envía lo mismo que el ESP32; aquí la petición llega al endpoint real por el cliente de pruebas."""
    ENTORNO = {'CHILITO_ENV': 'local', 'CHILITO_DEBUG': '1'}

    def enviar(self, peticion, timeout):
        self.enviadas.append(peticion.full_url)
        respuesta = Client(HTTP_HOST='127.0.0.1', enforce_csrf_checks=True).post(
            urlsplit(peticion.full_url).path, peticion.data, content_type=peticion.get_header('Content-type'))
        return io.BytesIO(respuesta.content)

    def simular(self, codigo, entorno=None, credencial=CREDENCIAL):
        self.enviadas = []
        with patch.object(simular_equipo.getpass, 'getpass', return_value=credencial), patch('builtins.input', return_value=codigo), \
                patch.object(simular_equipo.urllib.request, 'urlopen', side_effect=self.enviar), patch('sys.stdout', new_callable=io.StringIO) as salida:
            resultado = simular_equipo.vincular('CHI-0001', {**self.ENTORNO, **(entorno or {})})
        return resultado, salida.getvalue()

    def test_vincula_el_equipo_con_el_codigo_del_huerto(self):
        huerto_id = self.crear_huerto()
        equipo()
        resultado, salida = self.simular(self.codigo(huerto_id))
        self.assertEqual(resultado, 'vinculado')
        self.assertEqual(self.enviadas, [simular_equipo.URL_VINCULAR])
        self.assertEqual(str(Dispositivo.objects.get(identificador='CHI-0001').huerto_id), huerto_id)
        self.assertNotIn(CREDENCIAL, salida)

    def test_credencial_equivocada_no_vincula(self):
        huerto_id = self.crear_huerto()
        equipo()
        self.assertEqual(self.simular(self.codigo(huerto_id), credencial='otra')[0], 'credencial_invalida')
        self.assertIsNone(Dispositivo.objects.get(identificador='CHI-0001').huerto_id)

    def test_codigo_mal_escrito_no_se_envia(self):
        for codigo in ('', 'ABC', 'ABCD-EFGH-1', 'ABCD_EFGH'):
            with self.subTest(codigo=codigo), self.assertRaises(SystemExit):
                self.simular(codigo)
            self.assertEqual(self.enviadas, [])

    def test_usa_la_url_configurada_y_solo_https_fuera_del_equipo(self):
        huerto_id = self.crear_huerto()
        equipo()
        url = 'http://127.0.0.1:9000/api/dispositivos/vincular'
        self.assertEqual(self.simular(self.codigo(huerto_id), {'CHILITO_SIM_URL': url})[0], 'vinculado')
        self.assertEqual(self.enviadas, [url])
        for mala in ('http://ejemplo.test/api/dispositivos/vincular', 'file:///etc/passwd', 'ftp://localhost/x'):
            with self.subTest(url=mala), self.assertRaises(SystemExit):
                self.simular('ABCD-EFGH', {'CHILITO_SIM_URL': mala})
            self.assertEqual(self.enviadas, [])
        self.assertEqual(simular_equipo.url_vinculacion({'CHILITO_SIM_URL': 'https://ejemplo.test/v'}), 'https://ejemplo.test/v')

    def test_se_niega_fuera_de_desarrollo(self):
        with self.assertRaises(SystemExit):
            self.simular('ABCD-EFGH', {'CHILITO_DEBUG': '0'})
        self.assertEqual(self.enviadas, [])


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

    def test_ciclo_del_deposito_con_el_rol_iot(self):
        huerto_id = self.huerto_con_equipo()
        with self.conexion_iot() as con:
            dispositivo = simular_equipo.equipo(con, 'CHI-0001')
            simular_equipo.medir(con, dispositivo, hace=3)
            simular_equipo.medir(con, dispositivo, sin_agua=True, hace=2)
            simular_equipo.medir(con, dispositivo)
        self.assertFalse(Cuidado.objects.filter(huerto_id=huerto_id).exists())      # la recarga espera la confirmación
        self.assertEqual(DepositoDeteccion.objects.get(huerto_id=huerto_id).estado, 'pendiente')
        self.assertTrue(Notificacion.objects.filter(destinatario=self.dueña, titulo='Tu depósito necesita agua').exists())
        self.assertTrue(Notificacion.objects.filter(destinatario=self.dueña, titulo='Confirma la recarga de tu depósito').exists())
        medida = Medicion.objects.filter(huerto_id=huerto_id, deposito_con_agua=False).get().medida_en
        self.assertAlmostEqual((timezone.now() - medida).total_seconds(), 2 * 3600, delta=60)

    def test_solo_medir_sin_agua_pide_rellenar(self):
        """El error reportado: tras un solo «medir --sin-agua», la tarjeta pide rellenar y no pregunta por una recarga."""
        huerto_id = self.huerto_con_equipo()
        with self.conexion_iot() as con:
            simular_equipo.medir(con, simular_equipo.equipo(con, 'CHI-0001'), sin_agua=True)
        tanque = self.client.get(f'/api/huertos/{huerto_id}').json()['tank']
        self.assertEqual((tanque['state'], tanque['hasWater'], tanque['pendingRefill'], tanque['canRefill']), ('rellenar', False, None, True))
        self.assertFalse(DepositoDeteccion.objects.filter(huerto_id=huerto_id).exists())
        avisos = Notificacion.objects.filter(destinatario=self.dueña, origen='dispositivo')
        self.assertEqual([(a.titulo, a.texto, a.enlace) for a in avisos],
                         [('Tu depósito necesita agua', 'Tu depósito se quedó sin agua. Rellénalo y avísanos.', '#huerto')])

    def test_correr_sin_agua_no_genera_recargas(self):
        huerto_id = self.huerto_con_equipo()
        with self.conexion_iot() as con:
            dispositivo = simular_equipo.equipo(con, 'CHI-0001')
            simular_equipo.medir(con, dispositivo, hace=1)                       # con agua antes de empezar
            simular_equipo.correr(con, dispositivo, cada=0, ciclos=3, sin_agua=True, pausa=0)
        lecturas = list(Medicion.objects.filter(huerto_id=huerto_id).order_by('medida_en').values_list('deposito_con_agua', flat=True))
        self.assertEqual(lecturas, [True, False, False, False])
        self.assertEqual(DispositivoEvento.objects.filter(huerto_id=huerto_id, tipo='deposito_bajo').count(), 1)
        self.assertFalse(DispositivoEvento.objects.filter(huerto_id=huerto_id, tipo='deposito_recargado').exists())
        self.assertFalse(DepositoDeteccion.objects.filter(huerto_id=huerto_id).exists())
        self.assertFalse(Cuidado.objects.filter(huerto_id=huerto_id, tipo='rellenar_deposito').exists())
        self.assertEqual(self.client.get(f'/api/huertos/{huerto_id}').json()['tank']['state'], 'rellenar')

    def test_solo_equipos_vinculados(self):
        equipo('CHI-0009', '02:00:00:00:00:09')
        with self.conexion_iot() as con, self.assertRaises(SystemExit):
            simular_equipo.equipo(con, 'CHI-0009')

