"""Administración nueva sobre PostgreSQL temporal: equipos, administradores, ventas (aquí) con cuenta con y sin capacidad."""
import json
import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase
from django.utils import timezone

from datos import ventas
from datos.models import (Auditoria, Comando, Cuidado, Dispositivo, DispositivoEvento, ResumenHoraHuerto, ResumenHoraPlanta,
                          SoporteCaso, SoporteSesion, Venta)
from huerto.services import ZONA_MERIDA
from tests import cuenta, publicar_textos
from web.models import Idempotencia

MAC = '02:00:00:00:aa:{:02x}'
UUID_AJENO = '00000000-0000-4000-8000-000000000001'
FOLIO_AJENO = 'CS-00000000'


class BaseAdmin(TestCase):
    CLAVE_ESP32 = 'credencial-de-prueba-del-equipo-0001'

    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        cache.clear()
        self.numero = 0

    def cliente(self, usuario=None):
        cliente = Client(HTTP_HOST='127.0.0.1')
        if usuario is not None:
            cliente.force_login(usuario, backend='django.contrib.auth.backends.ModelBackend')
        return cliente

    def post(self, cliente, ruta, datos=None):
        return cliente.post(ruta, json.dumps(datos or {}), content_type='application/json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    def equipo(self, identificador=None):
        self.numero += 1
        return Dispositivo.objects.create(identificador=identificador or f'ADM-{self.numero:04d}', mac=MAC.format(self.numero), credencial_hash='x' * 40)

    def equipo_vinculado(self, correo='dueno-admin@example.test', identificador='ADM-VINC'):
        """Un equipo vinculado a un huerto con el flujo real: código generado por la persona y canje del ESP32."""
        dueno = cuenta(correo)
        persona = self.cliente(dueno)
        huerto = self.post(persona, '/api/huertos').json()['garden']['id']
        equipo = Dispositivo.objects.create(identificador=identificador, mac=MAC.format(200 + self.numero), credencial_hash=make_password(self.CLAVE_ESP32))
        codigo = self.post(persona, f'/api/huertos/{huerto}/codigo').json()['code']
        respuesta = Client(HTTP_HOST='127.0.0.1').post('/api/dispositivos/vincular', json.dumps({'identifier': identificador, 'credential': self.CLAVE_ESP32, 'code': codigo}),
                                                       content_type='application/json')
        self.assertEqual(respuesta.json()['result'], 'vinculado')
        return Dispositivo.objects.get(pk=equipo.pk)


class Capacidades(BaseAdmin):
    """Cada endpoint exige su capacidad y el segundo factor: sin sesión 401, sin capacidad 403, sin factor 403 mfa-required."""
    RUTAS = [
        ('get', '/api/admin/equipos', 'gestionar_dispositivos'), ('get', '/api/admin/equipos/1', 'gestionar_dispositivos'),
        ('post', '/api/admin/equipos', 'gestionar_dispositivos'), ('post', '/api/admin/equipos/1/rotar', 'gestionar_dispositivos'),
        ('get', '/api/admin/administradores', 'gestionar_administradores'), ('get', '/api/admin/administradores/historial', 'gestionar_administradores'),
        ('get', '/api/admin/administradores/actividad', 'gestionar_administradores'), ('post', '/api/admin/administradores/cuenta', 'gestionar_administradores'),
        ('get', '/api/admin/ventas', 'gestionar_ventas'), ('get', '/api/admin/ventas/resumen', 'gestionar_ventas'), ('post', '/api/admin/ventas', 'gestionar_ventas'),
        ('post', '/api/admin/ventas/1/cancelar', 'gestionar_ventas'),
        ('get', '/api/admin/legales?tipo=terminos', 'gestionar_legales'), ('post', '/api/admin/legales/vista-previa', 'gestionar_legales'),
        ('get', '/api/admin/consentimientos', 'ver_consentimientos'), ('get', '/api/admin/consentimientos/resumen', 'ver_consentimientos'),
        ('get', '/api/admin/consentimientos/exportar', 'ver_consentimientos'),
        ('get', '/api/admin/flota', 'ver_flota'), ('get', '/api/admin/soporte', 'atender_soporte'),
        ('get', f'/api/admin/soporte/{FOLIO_AJENO}', 'atender_soporte'), ('post', f'/api/admin/soporte/{UUID_AJENO}/atender', 'atender_soporte'),
        ('post', f'/api/admin/soporte/{UUID_AJENO}/conectar', 'atender_soporte'), ('post', f'/api/admin/soporte/{UUID_AJENO}/resolver', 'atender_soporte'),
        ('get', f'/api/admin/sesiones/{UUID_AJENO}', 'atender_soporte'), ('post', f'/api/admin/sesiones/{UUID_AJENO}/accion', 'atender_soporte'),
        ('post', f'/api/admin/sesiones/{UUID_AJENO}/cerrar', 'atender_soporte'),
        ('get', '/api/admin/mantenimientos', 'gestionar_mantenimientos'), ('post', '/api/admin/mantenimientos', 'gestionar_mantenimientos'),
        ('get', f'/api/admin/mantenimientos/{UUID_AJENO}', 'gestionar_mantenimientos'),
        ('post', f'/api/admin/mantenimientos/{UUID_AJENO}/corregir', 'gestionar_mantenimientos'),
        ('post', f'/api/admin/mantenimientos/{UUID_AJENO}/anular', 'gestionar_mantenimientos')]

    def llamar(self, cliente, metodo, ruta):
        return cliente.get(ruta) if metodo == 'get' else self.post(cliente, ruta)

    def test_sin_sesion_sin_capacidad_y_sin_factor(self):
        sin_capacidad = self.cliente(cuenta('cap-otra@example.test', 'gestionar_guias'))
        for metodo, ruta, capacidad in self.RUTAS:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.llamar(self.cliente(), metodo, ruta).status_code, 401)
                respuesta = self.llamar(sin_capacidad, metodo, ruta)
                self.assertEqual((respuesta.status_code, respuesta.json()['code']), (403, 'access-denied'))
                self.numero += 1
                sin_factor = self.cliente(cuenta(f'sin-factor-{self.numero}@example.test', capacidad, factor=False))
                respuesta = self.llamar(sin_factor, metodo, ruta)
                self.assertEqual((respuesta.status_code, respuesta.json()['code']), (403, 'mfa-required'))

    def test_la_capacidad_de_otra_pantalla_no_sirve(self):
        ventas_admin = self.cliente(cuenta('solo-ventas@example.test', 'gestionar_ventas'))
        self.assertEqual(ventas_admin.get('/api/admin/ventas').status_code, 200)
        for ruta in ('/api/admin/equipos', '/api/admin/administradores', '/api/admin/legales?tipo=terminos', '/api/admin/consentimientos'):
            with self.subTest(ruta=ruta):
                self.assertEqual(ventas_admin.get(ruta).status_code, 403)


class Equipos(BaseAdmin):
    def setUp(self):
        super().setUp()
        self.admin = self.cliente(cuenta('equipos-admin@example.test', 'gestionar_dispositivos'))

    def alta(self, **cambios):
        return self.post(self.admin, '/api/admin/equipos', {'identifier': 'ESP32-A1B2', 'mac': 'AA:BB:CC:DD:EE:01', 'firmware': '1.0.0', **cambios})

    def test_alta_muestra_la_credencial_una_vez_y_guarda_solo_su_hash(self):
        respuesta = self.alta()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        credencial = respuesta.json()['credential']
        self.assertGreaterEqual(len(credencial), 32)
        equipo = Dispositivo.objects.get(identificador='ESP32-A1B2')
        self.assertNotEqual(equipo.credencial_hash, credencial)
        self.assertTrue(check_password(credencial, equipo.credencial_hash))
        self.assertEqual((equipo.estado, equipo.conexion, equipo.mac, equipo.firmware_version), ('disponible', 'nunca', 'aa:bb:cc:dd:ee:01', '1.0.0'))
        recibo = Idempotencia.objects.get(ruta='/api/admin/equipos').respuesta
        self.assertIsNone(recibo['credential'], 'la credencial no queda en el recibo de idempotencia')
        self.assertTrue(Auditoria.objects.filter(accion='alta_equipo').exists())
        self.assertFalse(Auditoria.objects.filter(detalle__icontains=credencial).exists())
        self.assertTrue(DispositivoEvento.objects.filter(dispositivo=equipo, tipo='alta').exists())

    def test_datos_no_validos_y_duplicados(self):
        for cambios in ({'identifier': 'ab'}, {'identifier': 'tiene espacio'}, {'mac': 'no-es-mac'}, {'mac': 'AA:BB:CC:DD:EE'}, {'firmware': 'con espacio'}, {'identifier': 5}):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.alta(**cambios).status_code, 400)
        self.assertEqual(self.alta().status_code, 200)
        for cambios in ({'mac': 'AA:BB:CC:DD:EE:02'}, {'identifier': 'esp32-a1b2', 'mac': 'AA:BB:CC:DD:EE:03'}, {'identifier': 'OTRO-0001'}):
            with self.subTest(cambios=cambios):
                repetida = self.alta(**cambios)
                self.assertEqual((repetida.status_code, repetida.json()['code']), (409, 'equipo-duplicado'))

    def test_listar_busca_filtra_y_cuenta(self):
        self.equipo('LIST-0001'), self.equipo('LIST-0002')
        vinculado = self.equipo_vinculado(identificador='LIST-VINC')
        lista = self.admin.get('/api/admin/equipos').json()
        self.assertEqual((lista['counts'], lista['total']), ({'disponible': 2, 'vinculado': 1, 'retirado': 0}, 3))
        self.assertEqual([fila['identifier'] for fila in self.admin.get('/api/admin/equipos?estado=vinculado').json()['items']], ['LIST-VINC'])
        self.assertEqual(self.admin.get('/api/admin/equipos?busqueda=list-0002').json()['total'], 1)
        self.assertEqual(self.admin.get('/api/admin/equipos?busqueda=dueno-admin').json()['total'], 1, 'se busca también por el correo del dueño')
        self.assertEqual(self.admin.get(f'/api/admin/equipos?busqueda={vinculado.mac[:11]}').json()['total'], 3)
        self.assertEqual(self.admin.get('/api/admin/equipos?conexion=en_linea').json()['total'], 0)
        self.assertEqual(self.admin.get('/api/admin/equipos?vendido=no').json()['total'], 3)
        for consulta in ('?estado=otro', '?conexion=x', '?vendido=quizas', '?busqueda=' + 'a' * 61, '?page=0', '?x=1'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.admin.get(f'/api/admin/equipos{consulta}').status_code, 400)

    def test_busqueda_con_comodines_no_coincide_con_todo(self):
        self.equipo('COMO-0001')
        self.assertEqual(self.admin.get('/api/admin/equipos?busqueda=%25').json()['total'], 0)
        self.assertEqual(self.admin.get('/api/admin/equipos?busqueda=_').json()['total'], 0)

    def test_detalle_con_historial(self):
        equipo = self.equipo_vinculado(identificador='DET-0001')
        detalle = self.admin.get(f'/api/admin/equipos/{equipo.pk}').json()
        self.assertEqual((detalle['device']['state'], detalle['device']['owner']), ('vinculado', 'dueno-admin@example.test'))
        self.assertIn('vinculado', [evento['type'] for evento in detalle['events']['items']])
        self.assertEqual(self.admin.get('/api/admin/equipos/999999').status_code, 404)

    def test_desvincular(self):
        suelto = self.equipo()
        rechazo = self.post(self.admin, f'/api/admin/equipos/{suelto.pk}/desvincular')
        self.assertEqual((rechazo.status_code, rechazo.json()['code']), (409, 'equipo-no-vinculado'))
        vinculado = self.equipo_vinculado()
        self.assertEqual(self.post(self.admin, f'/api/admin/equipos/{vinculado.pk}/desvincular').status_code, 200)
        vinculado.refresh_from_db()
        self.assertEqual((vinculado.estado, vinculado.huerto_id), ('disponible', None))
        self.assertEqual(Auditoria.objects.filter(accion='desvincular_dispositivo').count(), 1, 'la función de la base ya audita: Django no la duplica')

    def test_rotar_credencial(self):
        equipo = self.equipo()
        antes = equipo.credencial_hash
        nueva = self.post(self.admin, f'/api/admin/equipos/{equipo.pk}/rotar').json()['credential']
        equipo.refresh_from_db()
        self.assertTrue(check_password(nueva, equipo.credencial_hash))
        self.assertNotEqual(equipo.credencial_hash, antes)
        self.assertTrue(Auditoria.objects.filter(accion='rotar_credencial').exists())
        self.assertEqual(self.post(self.admin, f'/api/admin/equipos/{equipo.pk}/retirar').status_code, 200)
        retirado = self.post(self.admin, f'/api/admin/equipos/{equipo.pk}/rotar')
        self.assertEqual((retirado.status_code, retirado.json()['code']), (409, 'equipo-retirado'))

    def test_retirar_solo_si_esta_disponible(self):
        vinculado = self.equipo_vinculado()
        rechazo = self.post(self.admin, f'/api/admin/equipos/{vinculado.pk}/retirar')
        self.assertEqual((rechazo.status_code, rechazo.json()['code']), (409, 'equipo-no-disponible'))
        libre = self.equipo()
        self.assertEqual(self.post(self.admin, f'/api/admin/equipos/{libre.pk}/retirar').json()['device']['state'], 'retirado')
        self.assertIsNotNone(Dispositivo.objects.get(pk=libre.pk).retirado_en)
        self.assertTrue(Auditoria.objects.filter(accion='retirar_equipo').exists())

    def test_acciones_sobre_un_equipo_inexistente(self):
        for accion in ('desvincular', 'rotar', 'retirar'):
            with self.subTest(accion=accion):
                self.assertEqual(self.post(self.admin, f'/api/admin/equipos/999999/{accion}').status_code, 404)


class Administradores(BaseAdmin):
    def setUp(self):
        super().setUp()
        self.jefe = cuenta('jefe-admin@example.test', 'gestionar_administradores')
        self.sesion = self.cliente(self.jefe)
        self.otra = cuenta('otra-cuenta@example.test')

    def cambiar(self, capacidades, correo='otra-cuenta@example.test', motivo='Atiende las ventas'):
        return self.post(self.sesion, '/api/admin/administradores/cuenta', {'email': correo, 'capabilities': capacidades, 'reason': motivo})

    def capacidades_de(self, usuario):
        return set(usuario.user_permissions.filter(content_type__app_label='cuentas').values_list('codename', flat=True))

    def test_dar_y_quitar_con_motivo_en_el_historial(self):
        respuesta = self.cambiar(['gestionar_ventas', 'ver_flota'])
        self.assertEqual((respuesta.status_code, respuesta.json()['granted']), (200, ['gestionar_ventas', 'ver_flota']))
        self.assertEqual(self.capacidades_de(self.otra), {'gestionar_ventas', 'ver_flota'})
        historial = self.sesion.get('/api/admin/administradores/historial?cuenta=otra-cuenta').json()
        self.assertEqual({(fila['capability'], fila['action'], fila['reason'], fila['by']) for fila in historial['items']},
                         {('gestionar_ventas', 'concedida', 'Atiende las ventas', 'jefe-admin@example.test'), ('ver_flota', 'concedida', 'Atiende las ventas', 'jefe-admin@example.test')})
        quitar = self.cambiar(['ver_flota'], motivo='Ya no vende').json()
        self.assertEqual((quitar['granted'], quitar['revoked']), ([], ['gestionar_ventas']))
        self.assertEqual(self.capacidades_de(self.otra), {'ver_flota'})
        lista = self.sesion.get('/api/admin/administradores').json()
        self.assertIn(('otra-cuenta@example.test', ('ver_flota',)), [(fila['email'], tuple(fila['capabilities'])) for fila in lista['items']])
        self.assertNotIn('gestionar_administradores', lista['editable'])
        self.assertTrue(Auditoria.objects.filter(accion='cambiar_capacidades', actor=self.jefe).exists())
        self.assertFalse(Auditoria.objects.filter(detalle__icontains='Ya no vende').exists(), 'el motivo vive en el historial, no en la auditoría')

    def test_no_deja_dar_gestionar_administradores(self):
        respuesta = self.cambiar(['gestionar_administradores'])
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'capacidad-reservada'))
        self.assertEqual(self.capacidades_de(self.otra), set())

    def test_no_deja_cambiar_las_propias_capacidades(self):
        respuesta = self.cambiar(['gestionar_ventas'], correo='JEFE-ADMIN@example.test')
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'capacidad-propia'))
        self.assertEqual(self.capacidades_de(self.jefe), {'gestionar_administradores'})

    def test_validacion(self):
        for datos in ({'capabilities': ['otra']}, {'capabilities': 'ver_flota'}, {'capabilities': ['ver_flota', 'ver_flota']}, {'capabilities': []},
                      {'capabilities': ['ver_flota'], 'motivo': ''}, {'capabilities': [5]}):
            with self.subTest(datos=datos):
                motivo = datos.get('motivo', 'x')
                self.assertEqual(self.cambiar(datos['capabilities'], motivo=motivo).status_code, 400)
        self.assertEqual(self.cambiar(['ver_flota'], motivo='x' * 301).status_code, 400)
        self.assertEqual(self.cambiar(['ver_flota'], correo='no-es-correo').status_code, 400)
        desconocida = self.cambiar(['ver_flota'], correo='nadie@example.test')
        self.assertEqual((desconocida.status_code, desconocida.json()['code']), (409, 'cuenta-no-encontrada'))

    def test_cuenta_sin_correo_verificado_no_recibe_nada(self):
        sin_verificar = cuenta('sin-verificar-admin@example.test', verificada=False)
        respuesta = self.cambiar(['gestionar_ventas', 'ver_flota'], correo='sin-verificar-admin@example.test')
        self.assertEqual(self.capacidades_de(sin_verificar), set(), 'ni una de las altas queda a medias')
        self.assertIn(respuesta.status_code, (400, 409))

    def test_actividad_por_administrador(self):
        self.cambiar(['ver_flota'])
        actividad = self.sesion.get('/api/admin/administradores/actividad?cuenta=jefe-admin@example.test').json()
        self.assertIn('cambiar_capacidades', [fila['action'] for fila in actividad['items']])
        self.assertEqual(self.sesion.get('/api/admin/administradores/actividad?cuenta=otra-cuenta@example.test').json()['total'], 0)

    def test_filtros_del_historial(self):
        self.cambiar(['ver_flota'])
        self.assertEqual(self.sesion.get('/api/admin/administradores/historial?capacidad=ver_flota').json()['total'], 1)
        self.assertEqual(self.sesion.get('/api/admin/administradores/historial?capacidad=gestionar_ventas').json()['total'], 0)
        hoy = timezone.localdate().isoformat()
        self.assertEqual(self.sesion.get(f'/api/admin/administradores/historial?cuenta=otra-cuenta&desde={hoy}&hasta={hoy}').json()['total'], 1)
        for consulta in ('?capacidad=otra', '?desde=ayer', '?desde=2026-02-01&hasta=2026-01-01', '?x=1'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.sesion.get(f'/api/admin/administradores/historial{consulta}').status_code, 400)


class Ventas(BaseAdmin):
    def setUp(self):
        super().setUp()
        self.admin = self.cliente(cuenta('ventas-admin@example.test', 'gestionar_ventas'))
        self.equipo_libre = self.equipo('VEN-0001')

    def datos(self, **cambios):
        return {'device': str(self.equipo_libre.pk), 'buyer': 'Ana Pérez', 'email': 'ana@example.test', 'municipality': 'Mérida', 'price': '3500.00',
                'received': '1000', 'reference': 'Transferencia 123', 'method': 'domicilio', 'soldAt': timezone.localdate().isoformat(), 'note': '', **cambios}

    def registrar(self, **cambios):
        return self.post(self.admin, '/api/admin/ventas', self.datos(**cambios))

    def test_los_106_municipios(self):
        self.assertEqual((len(ventas.MUNICIPIOS_YUCATAN), len(set(ventas.MUNICIPIOS_YUCATAN))), (106, 106))
        self.assertIn('Mérida', ventas.MUNICIPIOS_YUCATAN)

    def test_registrar_y_ciclo_completo(self):
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        venta = respuesta.json()['sale']
        self.assertEqual((venta['payment'], venta['delivery'], venta['price'], venta['received'], venta['state']), ('parcial', 'por_entregar', '3500.00', '1000.00', 'vigente'))
        ruta = f"/api/admin/ventas/{venta['id']}"
        pagado = self.post(self.admin, f'{ruta}/pago', {'received': '3500.00', 'reference': 'Efectivo'}).json()['sale']
        self.assertEqual((pagado['payment'], pagado['reference']), ('completo', 'Efectivo'))
        entregada = self.post(self.admin, f'{ruta}/entrega', {'deliveredAt': timezone.localdate().isoformat()}).json()['sale']
        self.assertEqual(entregada['delivery'], 'entregada')
        self.assertEqual(self.post(self.admin, f'{ruta}/nota', {'note': 'Se entregó en persona'}).json()['sale']['note'], 'Se entregó en persona')
        acciones = set(Auditoria.objects.values_list('accion', flat=True))
        self.assertTrue({'registrar_venta', 'registrar_pago', 'entregar_venta', 'editar_nota_venta'} <= acciones)
        cancelada = self.post(self.admin, f'{ruta}/cancelar').json()['sale']
        self.assertEqual((cancelada['state'], bool(cancelada['cancelledAt'])), ('cancelada', True))
        otra = self.post(self.admin, f'{ruta}/nota', {'note': 'tarde'})
        self.assertEqual((otra.status_code, otra.json()['code']), (409, 'venta-cancelada'))

    def test_enlaza_la_cuenta_del_comprador(self):
        self.assertFalse(self.registrar().json()['sale']['accountLinked'])
        cuenta('ana@example.test')
        segundo = self.equipo('VEN-0002')
        self.assertTrue(self.registrar(device=str(segundo.pk), buyer='Ana').json()['sale']['accountLinked'])

    def test_datos_no_validos(self):
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        for cambios in ({'municipality': 'Nowhere'}, {'price': '0'}, {'price': '10.999'}, {'price': 'abc'}, {'price': 3500}, {'received': '4000'}, {'received': '-1'},
                        {'soldAt': manana}, {'soldAt': 'ayer'}, {'method': 'dron'}, {'email': 'sin-arroba'}, {'buyer': ''}, {'buyer': 'x' * 121},
                        {'plannedDelivery': '2000-01-01'}, {'device': '999999'}, {'device': 'uno'}, {'reference': 'dos\nlineas'}, {'note': 'x' * 501}):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.registrar(**cambios).status_code, 400)
        self.assertEqual(self.post(self.admin, '/api/admin/ventas', {'buyer': 'x'}).status_code, 400)
        self.assertEqual(Venta.objects.count(), 0)

    def test_equipo_retirado_o_ya_vendido(self):
        self.assertEqual(self.registrar().status_code, 200)
        repetida = self.registrar()
        self.assertEqual((repetida.status_code, repetida.json()['code']), (409, 'equipo-vendido'))
        retirado = self.equipo('VEN-RETIRADO')
        Dispositivo.objects.filter(pk=retirado.pk).update(estado='retirado', retirado_en=timezone.now())
        self.assertEqual(self.registrar(device=str(retirado.pk)).status_code, 400)

    def test_pago_no_baja_ni_supera_el_precio(self):
        ruta = f"/api/admin/ventas/{self.registrar().json()['sale']['id']}/pago"
        for importe in ('500', '3500.01', 'mil'):
            with self.subTest(importe=importe):
                self.assertEqual(self.post(self.admin, ruta, {'received': importe}).status_code, 409 if importe != 'mil' else 400)
        self.assertEqual(self.post(self.admin, ruta, {'received': '2000'}).json()['sale']['received'], '2000.00')

    def test_entrega_entre_la_venta_y_hoy_y_una_sola_vez(self):
        ruta = f"/api/admin/ventas/{self.registrar().json()['sale']['id']}/entrega"
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        for fecha in ('2000-01-01', manana):
            with self.subTest(fecha=fecha):
                rechazo = self.post(self.admin, ruta, {'deliveredAt': fecha})
                self.assertEqual((rechazo.status_code, rechazo.json()['code']), (409, 'fecha-no-valida'))
        self.assertEqual(self.post(self.admin, ruta, {'deliveredAt': timezone.localdate().isoformat()}).status_code, 200)
        doble = self.post(self.admin, ruta, {'deliveredAt': timezone.localdate().isoformat()})
        self.assertEqual((doble.status_code, doble.json()['code']), (409, 'venta-entregada'))

    def test_el_equipo_vuelve_a_ser_vendible_al_cancelar(self):
        venta = self.registrar().json()['sale']
        self.assertNotIn('VEN-0001', [e['identifier'] for e in self.admin.get('/api/admin/ventas').json()['sellable']])
        self.post(self.admin, f"/api/admin/ventas/{venta['id']}/cancelar")
        self.assertIn('VEN-0001', [e['identifier'] for e in self.admin.get('/api/admin/ventas').json()['sellable']])

    def test_listar_con_filtros(self):
        segundo = self.equipo('VEN-0002')
        self.registrar()
        self.registrar(device=str(segundo.pk), buyer='Luis', email='luis@example.test', municipality='Valladolid', received='3500')
        lista = self.admin.get('/api/admin/ventas').json()
        self.assertEqual((lista['total'], len(lista['municipalities'])), (2, 106))
        total = lambda consulta: self.admin.get(f'/api/admin/ventas{consulta}').json()['total']
        self.assertEqual((total('?pago=completo'), total('?pago=parcial'), total('?entrega=entregada'), total('?entrega=por_entregar')), (1, 1, 0, 2))
        self.assertEqual((total('?municipio=Valladolid'), total('?busqueda=luis'), total('?busqueda=VEN-0001'), total('?estado=cancelada')), (1, 1, 1, 0))
        for consulta in ('?pago=otro', '?municipio=Nowhere', '?entrega=x', '?desde=ayer', '?x=1', '?page=0'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.admin.get(f'/api/admin/ventas{consulta}').status_code, 400)

    def test_resumen_por_periodo_y_municipio(self):
        segundo, tercero = self.equipo('VEN-0002'), self.equipo('VEN-0003')
        self.registrar()
        self.registrar(device=str(segundo.pk), municipality='Valladolid', price='1000', received='1000')
        cancelada = self.registrar(device=str(tercero.pk), price='9999').json()['sale']
        self.post(self.admin, f"/api/admin/ventas/{cancelada['id']}/cancelar")
        resumen = self.admin.get('/api/admin/ventas/resumen').json()
        self.assertEqual((resumen['sales'], resumen['sold'], resumen['collected'], resumen['pending']), (2, '4500.00', '2000.00', '2500.00'))
        self.assertEqual([(m['municipality'], m['sold']) for m in resumen['byMunicipality']], [('Mérida', '3500.00'), ('Valladolid', '1000.00')])
        self.assertEqual(self.admin.get('/api/admin/ventas/resumen?desde=2000-01-01&hasta=2000-12-31').json()['sales'], 0)
        self.assertEqual(self.admin.get('/api/admin/ventas/resumen?desde=2030-01-01&hasta=2000-01-01').status_code, 400)
        self.assertEqual(Venta.objects.get(pk=cancelada['id']).precio_mxn, Decimal('9999.00'))

    def test_venta_inexistente(self):
        for accion, datos in (('pago', {'received': '1'}), ('entrega', {'deliveredAt': '2026-01-01'}), ('nota', {'note': 'x'}), ('cancelar', {})):
            with self.subTest(accion=accion):
                self.assertEqual(self.post(self.admin, f'/api/admin/ventas/999999/{accion}', datos).status_code, 404)


class Flota(BaseAdmin):
    def setUp(self):
        super().setUp()
        self.admin = self.cliente(cuenta('flota-admin@example.test', 'ver_flota'))

    def test_sin_equipos_ni_datos_no_inventa_nada(self):
        flota = self.admin.get('/api/admin/flota').json()
        self.assertEqual(flota['totals'], {'linked': 0, 'online': 0, 'offline': 0, 'problems': 0})
        self.assertEqual((flota['trends'], flota['problems'], flota['items'], flota['total']), ({'moisture': [], 'temperature': []}, [], [], 0))

    def test_totales_tendencias_tabla_y_problemas(self):
        equipo = self.equipo_vinculado('flota-dueno@example.test', 'FLO-0001')
        self.equipo('FLO-0002')
        hora = datetime.combine(datetime.now(ZONA_MERIDA).date() - timedelta(days=2), time(12), ZONA_MERIDA).astimezone(UTC)
        ResumenHoraHuerto.objects.create(huerto_id=equipo.huerto_id, hora=hora, muestras=4, temperatura_prom=30, temperatura_min=28, temperatura_max=32)
        ResumenHoraHuerto.objects.create(huerto_id=equipo.huerto_id, hora=hora - timedelta(hours=1), muestras=12, temperatura_prom=26, temperatura_min=24, temperatura_max=28)
        ResumenHoraPlanta.objects.create(huerto_id=equipo.huerto_id, hora=hora, planta_numero=1, muestras=4, humedad_prom=40, humedad_min=38, humedad_max=42)
        persona = self.cliente(get_user_model().objects.get(email='flota-dueno@example.test'))
        orden = self.post(persona, f'/api/huertos/{equipo.huerto_id}/comandos', {'type': 'regar', 'plant': 1, 'duration': 5}).json()['command']['id']
        Comando.objects.filter(pk=orden).update(estado='fallido', detalle_error='bomba')
        flota = self.admin.get('/api/admin/flota').json()
        self.assertEqual(flota['totals']['linked'], 1)
        self.assertEqual(flota['totals']['problems'], 1)
        self.assertEqual([problema['type'] for problema in flota['problems']], ['order'])
        self.assertEqual([punto['value'] for punto in flota['trends']['moisture']], [40.0])
        # Ponderado por muestras, no promedio de promedios: (30*4 + 26*12) / 16 = 27.
        self.assertEqual([punto['value'] for punto in flota['trends']['temperature']], [27.0])
        self.assertEqual({fila['identifier'] for fila in flota['items']}, {'FLO-0001', 'FLO-0002'})
        self.assertEqual(self.admin.get('/api/admin/flota?busqueda=flota-dueno').json()['total'], 1)
        for consulta in ('?estado=otro', '?conexion=x', '?x=1', '?page=0'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.admin.get(f'/api/admin/flota{consulta}').status_code, 400)

    def test_equipo_desconectado_mas_de_24_horas_cuenta_como_problema(self):
        equipo = self.equipo_vinculado('flota-ausente@example.test', 'FLO-0003')
        Dispositivo.objects.filter(pk=equipo.pk).update(conexion='desconectado', ultima_conexion_en=timezone.now() - timedelta(hours=30))
        flota = self.admin.get('/api/admin/flota').json()
        self.assertEqual((flota['totals']['offline'], flota['totals']['problems'], flota['problems'][0]['type']), (1, 1, 'offline'))


class Consola(BaseAdmin):
    """Consola remota sin token: atiende una cuenta, solo ella se conecta y opera, y cada orden revalida la autorización."""
    def setUp(self):
        super().setUp()
        self.ana = cuenta('soporte-ana@example.test', 'atender_soporte')
        self.beto = cuenta('soporte-beto@example.test', 'atender_soporte')
        self.admin_ana, self.admin_beto = self.cliente(self.ana), self.cliente(self.beto)
        equipo = self.equipo_vinculado('soporte-persona@example.test', 'SOP-0001')
        self.huerto = equipo.huerto_id
        self.persona = self.cliente(get_user_model().objects.get(email='soporte-persona@example.test'))
        respuesta = self.post(self.persona, f'/api/huertos/{self.huerto}/soporte', {'incident': 'bomba', 'note': 'No riega', 'consent': True})
        self.caso = respuesta.json()['case']['id']
        self.folio = respuesta.json()['case']['folio']

    def conectar(self, cliente=None):
        cliente = cliente or self.admin_ana
        self.assertEqual(self.post(cliente, f'/api/admin/soporte/{self.caso}/atender').status_code, 200)
        respuesta = self.post(cliente, f'/api/admin/soporte/{self.caso}/conectar')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()['session']['id']

    def vencer_autorizacion(self):
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
            cursor.execute('ALTER TABLE soporte_caso DISABLE TRIGGER caso_reglas')
            cursor.execute("UPDATE soporte_caso SET autorizada_en = now() - interval '25 hours', autorizacion_vence_en = now() - interval '1 hour' WHERE id = %s", [self.caso])
            cursor.execute('ALTER TABLE soporte_caso ENABLE TRIGGER caso_reglas')

    def codigo(self, respuesta):
        return (respuesta.status_code, respuesta.json()['code'])

    def test_bandeja_por_estado_con_detalle_y_conteos(self):
        bandeja = self.admin_ana.get('/api/admin/soporte').json()
        self.assertEqual(bandeja['counts'], {'abierto': 1, 'en_atencion': 0, 'resuelto': 0})
        caso = bandeja['items'][0]
        self.assertEqual((caso['id'], caso['folio'][:3], caso['email'], caso['device'], caso['authorization'], caso['mine']),
                         (self.caso, 'CS-', 'soporte-persona@example.test', 'SOP-0001', 'vigente', False))
        detalle = self.admin_ana.get(f'/api/admin/soporte/{self.folio}').json()
        self.assertEqual((detalle['case']['note'], detalle['diagnostic'], detalle['session']), ('No riega', None, None))
        self.assertEqual(self.admin_ana.get('/api/admin/soporte?estado=en_atencion').json()['total'], 0)
        for consulta in ('?estado=cancelado', '?x=1', '?page=0'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.admin_ana.get(f'/api/admin/soporte{consulta}').status_code, 400)

    def test_flujo_completo_con_auditoria(self):
        sesion = self.conectar()
        estado = self.admin_ana.get(f'/api/admin/sesiones/{sesion}').json()
        self.assertEqual((estado['session']['state'], estado['readings'], estado['orders']), ('open', None, []))
        self.assertEqual(estado['device']['identifier'], 'SOP-0001')
        orden = self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', {'type': 'probar_bomba', 'plant': 2, 'duration': 3})
        self.assertEqual((orden.status_code, orden.json()['order']['state']), (200, 'pendiente'))
        self.assertEqual(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', {'type': 'reiniciar'}).status_code, 200)
        comando = Comando.objects.get(pk=orden.json()['order']['id'])
        self.assertEqual((comando.origen, str(comando.sesion_id), comando.solicitado_por_id), ('soporte', sesion, self.ana.pk))
        self.assertEqual(len(self.admin_ana.get(f'/api/admin/sesiones/{sesion}').json()['orders']), 2)
        visto = self.persona.get(f'/api/huertos/{self.huerto}/soporte').json()
        self.assertEqual(sorted(orden['type'] for orden in visto['orders']), ['probar_bomba', 'reiniciar'])
        self.assertEqual(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/cerrar').status_code, 200)
        self.assertEqual(SoporteSesion.objects.get(pk=sesion).motivo_cierre, 'manual')
        resuelto = self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/resolver', {'result': 'otro', 'note': 'Cambié la manguera'})
        self.assertEqual((resuelto.status_code, resuelto.json()['case']['state']), (200, 'resuelto'))
        self.assertEqual(self.persona.get(f'/api/huertos/{self.huerto}/soporte').json()['history'][0]['result'], 'otro')
        acciones = list(Auditoria.objects.filter(actor=self.ana).order_by('id').values_list('accion', flat=True))
        self.assertEqual(acciones, ['atender_caso', 'conectar_sesion', 'crear_comando', 'crear_comando', 'cerrar_sesion_tecnica', 'resolver_caso'])
        self.assertNotIn('manguera', json.dumps(list(Auditoria.objects.filter(actor=self.ana).values_list('detalle', flat=True))))

    def test_conectar_es_repetible_y_una_sesion_cerrada_no_recibe_ordenes(self):
        sesion = self.conectar()
        self.assertEqual(self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/conectar').json()['session']['id'], sesion)
        self.assertEqual(SoporteSesion.objects.count(), 1)
        self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/cerrar')
        self.assertEqual(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/cerrar').status_code, 200)
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', {'type': 'reiniciar'})), (409, 'sesion-cerrada'))

    def test_ordenes_validadas_en_el_servidor(self):
        sesion = self.conectar()
        casos = [{'type': 'regar', 'plant': 1, 'duration': 5}, {'type': 'probar_bomba'}, {'type': 'probar_bomba', 'plant': 4, 'duration': 3},
                 {'type': 'probar_bomba', 'plant': 1, 'duration': 6}, {'type': 'probar_bomba', 'plant': 1, 'duration': 0},
                 {'type': 'reiniciar', 'plant': 1}, {'type': 'ventilador_encender', 'duration': 2}, {}]
        for datos in casos:
            with self.subTest(datos=datos):
                self.assertEqual(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', datos).status_code, 400)
        self.assertEqual(Comando.objects.filter(origen='soporte').count(), 0)

    def test_el_segundo_admin_no_conecta_ni_opera_ni_resuelve_el_caso_del_primero(self):
        sesion = self.conectar()
        self.assertEqual(self.codigo(self.post(self.admin_beto, f'/api/admin/soporte/{self.caso}/atender')), (409, 'caso-ya-atendido'))
        self.assertEqual(self.codigo(self.post(self.admin_beto, f'/api/admin/soporte/{self.caso}/conectar')), (409, 'caso-no-tuyo'))
        self.assertEqual(self.codigo(self.post(self.admin_beto, f'/api/admin/soporte/{self.caso}/resolver', {'result': 'solucionado'})), (409, 'caso-no-tuyo'))
        self.assertEqual(self.admin_beto.get(f'/api/admin/sesiones/{sesion}').status_code, 404)
        self.assertEqual(self.post(self.admin_beto, f'/api/admin/sesiones/{sesion}/accion', {'type': 'reiniciar'}).status_code, 404)
        self.assertEqual(self.post(self.admin_beto, f'/api/admin/sesiones/{sesion}/cerrar').status_code, 404)
        self.assertIsNone(SoporteSesion.objects.get(pk=sesion).cerrada_en)
        self.assertEqual(self.admin_beto.get(f'/api/admin/soporte/{self.folio}').json()['session'], None)
        self.assertEqual(self.admin_ana.get(f'/api/admin/soporte/{self.folio}').json()['session']['id'], sesion)

    def test_sin_atender_no_se_conecta_ni_se_resuelve(self):
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/conectar')), (409, 'caso-no-tuyo'))
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/resolver', {'result': 'solucionado'})), (409, 'caso-no-tuyo'))

    def test_resolver_valida_resultado_y_nota(self):
        self.conectar()
        for datos in ({'result': 'otro'}, {'result': 'otro', 'note': '   '}, {'result': 'nada'}, {'result': 'solucionado', 'note': 'x' * 501}, {}):
            with self.subTest(datos=datos):
                self.assertEqual(self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/resolver', datos).status_code, 400)
        self.assertEqual(self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/resolver', {'result': 'sin_falla'}).status_code, 200)

    def test_resolver_cierra_la_sesion_tecnica(self):
        sesion = self.conectar()
        self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/resolver', {'result': 'solucionado'})
        self.assertEqual(SoporteSesion.objects.get(pk=sesion).motivo_cierre, 'caso_cerrado')
        self.assertEqual(self.admin_ana.get(f'/api/admin/sesiones/{sesion}').json()['session']['reason'], 'caso_cerrado')

    def test_la_revocacion_durante_la_sesion_cierra_y_la_siguiente_orden_falla(self):
        sesion = self.conectar()
        self.assertEqual(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', {'type': 'lectura_inmediata'}).status_code, 200)
        self.assertEqual(self.post(self.persona, f'/api/soporte/{self.caso}/revocar').status_code, 200)
        estado = self.admin_ana.get(f'/api/admin/sesiones/{sesion}').json()
        self.assertEqual((estado['session']['state'], estado['session']['reason']), ('closed', 'revocada'))
        self.assertNotIn('readings', estado)
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', {'type': 'reiniciar'})), (409, 'sesion-cerrada'))
        self.assertEqual(Comando.objects.filter(sesion_id=sesion).count(), 1)

    def test_autorizacion_vencida_no_permite_conectar(self):
        self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/atender')
        self.vencer_autorizacion()
        self.assertEqual(self.admin_ana.get('/api/admin/soporte?estado=en_atencion').json()['items'][0]['authorization'], 'vencida')
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/conectar')), (409, 'autorizacion-no-vigente'))
        self.assertEqual(SoporteSesion.objects.count(), 0)

    def test_autorizacion_vencida_durante_la_sesion_bloquea_ordenes_y_la_marca_cerrada(self):
        sesion = self.conectar()
        self.vencer_autorizacion()
        estado = self.admin_ana.get(f'/api/admin/sesiones/{sesion}').json()
        self.assertEqual((estado['session']['state'], estado['session']['reason']), ('closed', 'vencida'))
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', {'type': 'reiniciar'})), (409, 'sesion-cerrada'))

    def test_el_vencimiento_tambien_lo_rechaza_la_base(self):
        sesion = self.conectar()
        self.vencer_autorizacion()
        with self.assertRaises(Exception) as fallo:
            Comando.objects.create(huerto_id=self.huerto, dispositivo_id=SoporteCaso.objects.get(pk=self.caso).dispositivo_id, tipo='reiniciar',
                                   origen='soporte', solicitado_por=self.ana, sesion_id=sesion)
        self.assertIn('Orden fuera de una sesión técnica autorizada', str(fallo.exception))

    def test_cerrar_la_sesion_de_la_cuenta_cierra_la_sesion_tecnica(self):
        sesion = self.conectar()
        self.admin_ana.delete('/_allauth/browser/v1/auth/session')
        cerrada = SoporteSesion.objects.get(pk=sesion)
        self.assertEqual((cerrada.motivo_cierre, cerrada.cerrada_en is not None), ('cierre_sesion', True))
        self.assertTrue(Auditoria.objects.filter(actor=self.ana, accion='cerrar_sesion_tecnica', detalle={'motivo': 'cierre_sesion'}).exists())

    def test_una_sola_sesion_abierta_por_administrador(self):
        self.conectar()
        self.numero += 1
        otro = self.equipo_vinculado('soporte-otra@example.test', 'SOP-0002')
        persona = self.cliente(get_user_model().objects.get(email='soporte-otra@example.test'))
        caso = self.post(persona, f'/api/huertos/{otro.huerto_id}/soporte', {'incident': 'otro', 'consent': True}).json()['case']['id']
        self.post(self.admin_ana, f'/api/admin/soporte/{caso}/atender')
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/soporte/{caso}/conectar')), (409, 'sesion-abierta'))

    def test_al_volver_se_retoma_la_misma_sesion_con_todas_las_ordenes_del_caso(self):
        sesion = self.conectar()
        self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', {'type': 'probar_bomba', 'plant': 1, 'duration': 2})
        # Salir de la pantalla ya no cierra nada: el detalle trae la sesión abierta y la orden pendiente.
        detalle = self.admin_ana.get(f'/api/admin/soporte/{self.folio}').json()
        self.assertEqual(detalle['session']['id'], sesion)
        self.assertEqual([(orden['type'], orden['state']) for orden in detalle['orders']], [('probar_bomba', 'pendiente')])
        self.assertEqual(self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/conectar').json()['session']['id'], sesion)
        self.assertEqual(SoporteSesion.objects.filter(caso_id=self.caso).count(), 1)
        self.assertIsNone(SoporteSesion.objects.get(pk=sesion).cerrada_en)

    def test_las_ordenes_de_una_sesion_cerrada_siguen_en_el_caso(self):
        primera = self.conectar()
        self.post(self.admin_ana, f'/api/admin/sesiones/{primera}/accion', {'type': 'reiniciar'})
        self.post(self.admin_ana, f'/api/admin/sesiones/{primera}/cerrar')
        self.assertIsNone(self.admin_ana.get(f'/api/admin/soporte/{self.folio}').json()['session'])
        segunda = self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/conectar').json()['session']['id']
        self.assertNotEqual(segunda, primera)
        self.post(self.admin_ana, f'/api/admin/sesiones/{segunda}/accion', {'type': 'lectura_inmediata'})
        tipos = [orden['type'] for orden in self.admin_ana.get(f'/api/admin/sesiones/{segunda}').json()['orders']]
        self.assertEqual(sorted(tipos), ['lectura_inmediata', 'reiniciar'])
        self.assertEqual(len(self.admin_ana.get(f'/api/admin/soporte/{self.folio}').json()['orders']), 2)

    def test_otro_admin_no_retoma_la_sesion(self):
        sesion = self.conectar()
        detalle = self.admin_beto.get(f'/api/admin/soporte/{self.folio}').json()
        self.assertEqual((detalle['session'], detalle['case']['mine']), (None, False))
        self.assertEqual(self.codigo(self.post(self.admin_beto, f'/api/admin/soporte/{self.caso}/conectar')), (409, 'caso-no-tuyo'))
        self.assertEqual(self.admin_beto.get(f'/api/admin/sesiones/{sesion}').status_code, 404)
        self.assertEqual(SoporteSesion.objects.count(), 1)

    def test_revocar_con_la_sesion_abierta_no_deja_retomarla(self):
        sesion = self.conectar()
        self.post(self.persona, f'/api/soporte/{self.caso}/revocar')
        self.assertEqual(self.admin_ana.get(f'/api/admin/sesiones/{sesion}').json()['session']['state'], 'closed')
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/soporte/{self.caso}/conectar')), (409, 'autorizacion-no-vigente'))
        self.assertEqual(self.codigo(self.post(self.admin_ana, f'/api/admin/sesiones/{sesion}/accion', {'type': 'reiniciar'})), (409, 'sesion-cerrada'))

    def test_casos_o_sesiones_inexistentes(self):
        for metodo, ruta in (('get', f'/api/admin/soporte/{FOLIO_AJENO}'), ('get', f'/api/admin/soporte/{UUID_AJENO}'),
                             ('get', f'/api/admin/soporte/{self.folio.lower()}'), ('post', f'/api/admin/soporte/{UUID_AJENO}/atender'),
                             ('get', f'/api/admin/sesiones/{UUID_AJENO}')):
            with self.subTest(ruta=ruta):
                respuesta = self.admin_ana.get(ruta) if metodo == 'get' else self.post(self.admin_ana, ruta)
                self.assertEqual(respuesta.status_code, 404)


class Mantenimientos(BaseAdmin):
    def setUp(self):
        super().setUp()
        self.editor = cuenta('mant-editor@example.test', 'gestionar_mantenimientos')
        self.admin = self.cliente(self.editor)
        equipo = self.equipo_vinculado('mant-dueno@example.test', 'MAN-0001')
        self.dueno = get_user_model().objects.get(email='mant-dueno@example.test')
        self.huerto = equipo.huerto_id
        self.persona = self.cliente(self.dueno)

    def cuidado(self, tipo='rellenar_deposito', planta=None):
        return Cuidado.objects.create(huerto_id=self.huerto, tipo=tipo, planta_numero=planta, registrado_por=self.dueno)

    def corregir(self, cuidado, revision, **cambios):
        datos = {'revision': revision, 'type': 'cosecha', 'plant': 2, 'chiles': 5, 'reason': 'Era cosecha', **cambios}
        return self.post(self.admin, f'/api/admin/mantenimientos/{cuidado.pk}/corregir', datos)

    def test_lista_todos_los_huertos_con_paginacion_busqueda_y_filtros(self):
        for _ in range(27):     # inspecciones de todo el huerto: las recargas tienen su propio límite
            self.cuidado('inspeccion')
        self.cuidado('sustrato', 1)
        pagina1 = self.admin.get('/api/admin/mantenimientos').json()
        self.assertEqual((pagina1['total'], len(pagina1['items']), pagina1['page']), (28, 25, 1))
        self.assertEqual(len(self.admin.get('/api/admin/mantenimientos?page=2').json()['items']), 3)
        primero = pagina1['items'][0]
        self.assertEqual((primero['owner'], primero['gardenId'], primero['revision']), ('mant-dueno@example.test', str(self.huerto), 0))
        total = lambda consulta: self.admin.get(f'/api/admin/mantenimientos{consulta}').json()['total']
        self.assertEqual((total('?busqueda=mant-dueno'), total('?busqueda=Mi%20huerto'), total('?busqueda=nadie')), (28, 28, 0))
        self.assertEqual((total('?tipo=sustrato'), total('?planta=1'), total('?planta=huerto'), total(f'?huerto={self.huerto}'), total('?huerto=999999')), (1, 1, 27, 28, 0))
        self.assertEqual((total('?estado=vigente'), total('?estado=anulado'), total('?desde=2000-01-01&hasta=2000-12-31')), (28, 0, 0))
        for consulta in ('?estado=x', '?tipo=x', '?planta=9', '?huerto=abc', '?desde=ayer', '?desde=2026-02-01&hasta=2026-01-01', '?x=1', '?page=0'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.admin.get(f'/api/admin/mantenimientos{consulta}').status_code, 400)

    def test_corregir_con_motivo_y_numero_de_revision(self):
        cuidado = self.cuidado()
        respuesta = self.corregir(cuidado, 0)
        registro = respuesta.json()['record']
        self.assertEqual((respuesta.status_code, registro['type'], registro['plant'], registro['chiles'], registro['corrected'], registro['revision']),
                         (200, 'cosecha', 2, 5, True, 1))
        visto = self.persona.get(f'/api/huertos/{self.huerto}/cuidados').json()['items'][0]
        self.assertEqual((visto['corrected'], visto['type'], visto['reason']), (True, 'cosecha', 'Era cosecha'))
        self.assertEqual(self.corregir(cuidado, 0).json()['code'], 'stale-record')
        segunda = self.corregir(cuidado, 1, reason='Fueron 7', chiles=7)
        self.assertEqual((segunda.status_code, segunda.json()['record']['chiles'], segunda.json()['record']['revision']), (200, 7, 2))
        historial = self.admin.get(f'/api/admin/mantenimientos/{cuidado.pk}').json()['revisions']
        self.assertEqual([(revision['number'], revision['type']) for revision in historial], [(1, 'correccion'), (2, 'correccion')])

    def test_anular_y_no_admite_mas_cambios(self):
        cuidado = self.cuidado()
        anulado = self.post(self.admin, f'/api/admin/mantenimientos/{cuidado.pk}/anular', {'revision': 0, 'reason': 'Duplicado'})
        self.assertEqual((anulado.status_code, anulado.json()['record']['voided']), (200, True))
        self.assertTrue(self.persona.get(f'/api/huertos/{self.huerto}/cuidados').json()['items'][0]['voided'])
        for ruta, datos in (('anular', {'revision': 1, 'reason': 'Otra vez'}), ('corregir', {'revision': 1, 'type': 'inspeccion', 'reason': 'x'})):
            with self.subTest(ruta=ruta):
                respuesta = self.post(self.admin, f'/api/admin/mantenimientos/{cuidado.pk}/{ruta}', datos)
                self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'cuidado-anulado'))
        self.assertEqual(self.admin.get('/api/admin/mantenimientos?estado=anulado').json()['total'], 1)

    def test_validacion_de_la_correccion(self):
        cuidado = self.cuidado()
        for cambios in ({'reason': ''}, {'reason': '   '}, {'reason': 'x' * 501}, {'type': 'sustrato', 'plant': None}, {'type': 'rellenar_deposito', 'plant': 1, 'chiles': None},
                        {'type': 'sustrato', 'plant': 1, 'chiles': 3}, {'plant': 4}, {'chiles': -1}, {'type': 'nada'}):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.corregir(cuidado, 0, **cambios).status_code, 400)
        for revision in ('0', None, -1, 1.5):
            with self.subTest(revision=revision):
                self.assertEqual(self.corregir(cuidado, revision).status_code, 400)
        self.assertEqual(self.post(self.admin, f'/api/admin/mantenimientos/{cuidado.pk}/anular', {'revision': 0}).status_code, 400)
        self.assertEqual(self.post(self.admin, f'/api/admin/mantenimientos/{cuidado.pk}/corregir', {'revision': 0, 'type': 'inspeccion', 'otro': 1, 'reason': 'x'}).status_code, 400)
        self.assertEqual(self.admin.get('/api/admin/mantenimientos').json()['items'][0]['revision'], 0)

    def test_registrar_en_un_huerto_ajeno(self):
        respuesta = self.post(self.admin, '/api/admin/mantenimientos', {'garden': str(self.huerto), 'type': 'sustrato', 'plant': 3})
        self.assertEqual((respuesta.status_code, respuesta.json()['record']['owner']), (200, 'mant-dueno@example.test'))
        self.assertEqual(Cuidado.objects.get(pk=respuesta.json()['record']['id']).registrado_por_id, self.editor.pk)
        self.assertEqual(self.post(self.admin, '/api/admin/mantenimientos', {'garden': '999999', 'type': 'sustrato', 'plant': 3}).status_code, 404)
        for datos in ({'garden': 'abc', 'type': 'sustrato', 'plant': 3}, {'type': 'sustrato', 'plant': 3}, {'garden': str(self.huerto), 'type': 'sustrato'}):
            with self.subTest(datos=datos):
                self.assertEqual(self.post(self.admin, '/api/admin/mantenimientos', datos).status_code, 400)

    def test_auditoria_sin_el_motivo(self):
        cuidado = self.cuidado()
        self.corregir(cuidado, 0, reason='Dato personal en el motivo')
        self.post(self.admin, f'/api/admin/mantenimientos/{cuidado.pk}/anular', {'revision': 1, 'reason': 'Otro dato personal'})
        filas = Auditoria.objects.filter(actor=self.editor)
        self.assertEqual(list(filas.order_by('id').values_list('accion', flat=True)), ['corregir_cuidado', 'anular_cuidado'])
        self.assertNotIn('personal', json.dumps(list(filas.values_list('detalle', flat=True))))

    def test_cuidado_inexistente(self):
        self.assertEqual(self.admin.get(f'/api/admin/mantenimientos/{UUID_AJENO}').status_code, 404)
        self.assertEqual(self.post(self.admin, f'/api/admin/mantenimientos/{UUID_AJENO}/anular', {'revision': 0, 'reason': 'x'}).status_code, 404)
