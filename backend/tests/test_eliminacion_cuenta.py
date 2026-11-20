"""Eliminación física e inmediata de la cuenta (web.0010) y padrón de cuentas para administración.

TestCase nunca confirma la transacción, así que las llaves foráneas diferidas no se comprobarían. Cada prueba fuerza esas
comprobaciones con `SET CONSTRAINTS ALL IMMEDIATE`: antes del borrado, para cerrar lo que dejó la preparación, y después,
para demostrar que no quedó ninguna fila apuntando a la cuenta borrada (lo mismo que comprueba el COMMIT real).
"""
import json
import time
import uuid
from datetime import timedelta
from urllib.parse import urlencode

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import IntegrityError, InternalError, connection, transaction
from django.test import Client
from django.utils import timezone

from datos.models import Auditoria, Cuidado, Dispositivo, Medicion, MedicionPlanta, Notificacion, Venta
from huerto.models import Huerto, Planta
from huerto.tests import BaseHuerto
from privacidad.models import Decision, Preferencia, Sujeto
from tests import cuenta, reautenticado
from web.models import Idempotencia

CLAVE = 'Clave-de-prueba-123'


def comprobar_llaves():
    """Lo que haría el COMMIT: comprobar ya las llaves foráneas y triggers diferidos."""
    with connection.cursor() as cursor:
        cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        cursor.execute('SET CONSTRAINTS ALL DEFERRED')


class Eliminacion(BaseHuerto):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.dueña = cuenta('eliminar-duena@example.test', password=CLAVE)
        self.otra = cuenta('eliminar-otra@example.test')
        self.client = self.cliente(self.dueña)
        self.admin = self.cliente(cuenta('eliminar-admin@example.test', 'ver_consentimientos', 'gestionar_ventas'))
        reautenticado(self.admin)

    def eliminar(self, clave=CLAVE, cliente=None):
        return self.post('/api/cuenta/eliminar', {'password': clave}, cliente)

    def test_contrasena_incorrecta_no_borra_nada(self):
        for clave in ('otra-clave', '', None, 5):
            with self.subTest(clave=clave):
                self.assertEqual(self.eliminar(clave).status_code, 400)
        self.assertEqual(self.post('/api/cuenta/eliminar', {}).status_code, 400)
        self.assertTrue(get_user_model().objects.filter(pk=self.dueña.pk).exists())

    def test_exige_idempotency_key_y_csrf(self):
        sin_clave = self.client.post('/api/cuenta/eliminar', json.dumps({'password': CLAVE}), content_type='application/json')
        self.assertEqual(sin_clave.status_code, 400)
        estricto = Client(HTTP_HOST='127.0.0.1', enforce_csrf_checks=True)
        estricto.force_login(self.dueña, backend='django.contrib.auth.backends.ModelBackend')
        sin_csrf = estricto.post('/api/cuenta/eliminar', json.dumps({'password': CLAVE}), content_type='application/json',
                                 HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertEqual(sin_csrf.status_code, 403)
        self.assertTrue(get_user_model().objects.filter(pk=self.dueña.pk).exists())

    def test_borrado_fisico_inmediato_de_todo_lo_suyo(self):
        huerto_id = self.huerto_vinculado('Huerto a borrar')
        equipo = Dispositivo.objects.get(huerto_id=huerto_id)
        Cuidado.objects.create(huerto_id=huerto_id, tipo='inspeccion', registrado_por=self.dueña)
        self.assertEqual(self.client.post('/api/privacidad/cookies', json.dumps({'statistics': True}),
                                          content_type='application/json').status_code, 200)
        Authenticator.objects.create(user=self.dueña, type='totp', data={})
        self.post('/api/cuenta/perfil', {'alias': 'Mi alias'})          # deja auditoría y un recibo de idempotencia
        vendido = Dispositivo.objects.create(identificador='CHI-VEN0', mac='02:00:00:09:00:00', credencial_hash='x' * 40)
        venta = self.post('/api/admin/ventas', {'device': str(vendido.pk), 'buyer': 'Dueña Pérez', 'email': self.dueña.email,
                                               'municipality': 'Mérida', 'price': '3500.00', 'received': '0', 'reference': '',
                                               'method': 'recogida', 'soldAt': timezone.localdate().isoformat(), 'note': ''},
                          self.admin).json()['sale']
        otro_navegador = self.cliente(self.dueña)
        usuario_id = self.dueña.pk
        # Una sesión ya caducada también guarda el id y la huella de la cuenta: debe borrarse igual.
        caducada = SessionStore()
        caducada[SESSION_KEY] = str(usuario_id)
        caducada.create()
        Session.objects.filter(pk=caducada.session_key).update(expire_date=timezone.now() - timedelta(days=1))
        self.assertTrue(Decision.objects.filter(usuario_id=usuario_id).exists())
        self.assertTrue(Idempotencia.objects.filter(actor_id=usuario_id).exists())
        self.assertTrue(Venta.objects.filter(comprador_usuario_id=usuario_id).exists())
        comprobar_llaves()

        inicio = time.monotonic()
        respuesta = self.eliminar()
        duracion = time.monotonic() - inicio
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()['status'], 'deleted')
        self.assertLess(duracion, 5)
        comprobar_llaves()

        self.assertFalse(get_user_model().objects.filter(pk=usuario_id).exists())
        for modelo, filtro in ((Huerto, {'propietario_id': usuario_id}), (Planta, {'huerto_id': huerto_id}),
                               (Cuidado, {'huerto_id': huerto_id}), (Sujeto, {'usuario_id': usuario_id}),
                               (Decision, {'usuario_id': usuario_id}), (Auditoria, {'actor_id': usuario_id}),
                               (Auditoria, {'huerto_id': huerto_id}), (Notificacion, {'destinatario_id': usuario_id}),
                               (Idempotencia, {'actor_id': usuario_id}), (EmailAddress, {'user_id': usuario_id}),
                               (Authenticator, {'user_id': usuario_id})):
            with self.subTest(modelo=modelo.__name__, filtro=filtro):
                self.assertFalse(modelo.objects.filter(**filtro).exists())
        self.assertFalse(Preferencia.objects.filter(sujeto__usuario_id=usuario_id).exists())
        equipo.refresh_from_db()
        self.assertEqual((equipo.estado, equipo.huerto_id), ('disponible', None))
        conservada = Venta.objects.get(pk=venta['id'])
        self.assertEqual((conservada.comprador_usuario_id, conservada.comprador_correo), (None, 'eliminar-duena@example.test'))
        self.assertEqual(list(Auditoria.objects.filter(accion='eliminar_cuenta').values_list('actor_id', 'entidad_id')), [(None, '')])

        # La sesión de este navegador y la de cualquier otro quedan cerradas; las cookies de privacidad se borran.
        self.assertEqual(self.client.get('/api/cuenta').status_code, 401)
        self.assertEqual(otro_navegador.get('/api/cuenta').status_code, 401)
        self.assertFalse(Session.objects.filter(pk=otro_navegador.session.session_key).exists())
        self.assertFalse(Session.objects.filter(pk=caducada.session_key).exists())
        self.assertFalse([s.pk for s in Session.objects.all() if s.get_decoded().get(SESSION_KEY) == str(usuario_id)])
        self.assertEqual(respuesta.cookies['chilito_preferencia'].value, '')
        # Repetir la petición ya no encuentra sesión: el resultado idempotente es 401.
        self.assertEqual(self.eliminar().status_code, 401)

        # Desaparece al instante de la bitácora y del padrón de cuentas.
        bitacora = self.admin.get('/api/admin/consentimientos?cuenta=eliminar-duena').json()
        self.assertEqual(bitacora['total'], 0)
        padron = self.admin.get('/api/admin/consentimientos/cuentas?busqueda=eliminar-duena').json()
        self.assertEqual((padron['total'], padron['totals']['total']), (0, 0))

    def test_cancelar_ya_no_existe(self):
        self.assertEqual(self.post('/api/cuenta/eliminar/cancelar').status_code, 404)

    def test_cuenta_con_capacidades_no_se_elimina(self):
        jefe = cuenta('eliminar-jefe@example.test', 'gestionar_administradores', password=CLAVE)
        for usuario in (jefe, cuenta('eliminar-cap@example.test', 'ver_flota', password=CLAVE)):
            with self.subTest(usuario=usuario.email):
                respuesta = self.eliminar(cliente=self.cliente(usuario))
                self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'cuenta-administrativa'))
                self.assertTrue(get_user_model().objects.filter(pk=usuario.pk).exists())

    def test_la_base_tambien_rechaza_una_cuenta_con_capacidades(self):
        jefe = cuenta('eliminar-jefe-bd@example.test', 'gestionar_administradores')
        with self.assertRaisesMessage(IntegrityError, 'Una cuenta con capacidades no se elimina'), transaction.atomic(), \
                connection.cursor() as cursor:
            cursor.execute('SELECT chilito_eliminar_cuenta(%s)', [jefe.pk])

    def test_historial_administrativo_ajeno_no_se_elimina(self):
        """Quien registró una venta (referencia obligatoria en un registro ajeno) no se borra, aunque ya no tenga capacidades."""
        vendedora = cuenta('eliminar-vendedora@example.test', 'gestionar_ventas', password=CLAVE)
        sesion = self.cliente(vendedora)
        equipo = Dispositivo.objects.create(identificador='CHI-VEN1', mac='02:00:00:09:00:01', credencial_hash='x' * 40)
        self.assertEqual(self.post('/api/admin/ventas', {'device': str(equipo.pk), 'buyer': 'Ana', 'email': 'ana@example.test',
                                                         'municipality': 'Mérida', 'price': '100.00', 'received': '0', 'reference': '',
                                                         'method': 'recogida', 'soldAt': timezone.localdate().isoformat(), 'note': ''},
                                   sesion).status_code, 200)
        vendedora.user_permissions.clear()
        respuesta = self.eliminar(cliente=self.cliente(vendedora))
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'cuenta-con-historial-administrativo'))
        self.assertTrue(get_user_model().objects.filter(pk=vendedora.pk).exists())

    def test_cuota_de_intentos(self):
        estados = [self.eliminar('mala-%d' % n).status_code for n in range(7)]
        self.assertEqual(estados[:5], [400] * 5)
        self.assertEqual(estados[5:], [429, 429])

    def test_menos_de_5_segundos_con_telemetria(self):
        huerto_id = self.huerto_vinculado()
        equipo = Dispositivo.objects.get(huerto_id=huerto_id)
        ahora = timezone.now()
        mediciones = Medicion.objects.bulk_create(
            Medicion(dispositivo=equipo, huerto_id=huerto_id, medida_en=ahora - timedelta(minutes=minuto), temperatura_c=25,
                     humedad_aire_pct=60) for minuto in range(1, 2001))
        MedicionPlanta.objects.bulk_create(MedicionPlanta(medicion=medicion, planta_numero=numero, humedad_sustrato_pct=50,
                                                          adc_crudo=2000) for medicion in mediciones for numero in (1, 2, 3))
        comprobar_llaves()
        inicio = time.monotonic()
        self.assertEqual(self.eliminar().status_code, 200)
        comprobar_llaves()
        self.assertLess(time.monotonic() - inicio, 5)
        self.assertFalse(Medicion.objects.filter(huerto_id=huerto_id).exists())


class ProteccionDeLaBase(BaseHuerto):
    """Fuera de chilito_eliminar_cuenta los historiales siguen siendo inmutables, incluso para el propietario."""

    def test_sin_marca_no_se_borra_ni_la_cuenta_ni_la_bitacora(self):
        usuaria = cuenta('proteccion@example.test')
        for sentencia in ('DELETE FROM privacidad_decision WHERE usuario_id=%s', 'DELETE FROM privacidad_sujeto WHERE usuario_id=%s',
                          'DELETE FROM cuentas_usuario WHERE id=%s'):
            with self.subTest(sentencia=sentencia):
                with self.assertRaises((IntegrityError, InternalError)), transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(sentencia, [usuaria.pk])
        self.assertTrue(Decision.objects.filter(usuario=usuaria).exists())

    def test_una_bandera_de_sesion_no_abre_la_excepcion(self):
        usuaria = cuenta('proteccion-bandera@example.test')
        with self.assertRaises((IntegrityError, InternalError)), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT set_config('chilito.borrar_cuenta', %s, true)", [str(usuaria.pk)])
            cursor.execute('DELETE FROM privacidad_decision WHERE usuario_id=%s', [usuaria.pk])

    def test_toda_funcion_que_impide_borrar_lleva_la_guarda(self):
        """Si una migración futura reemplaza una de estas funciones sin la guarda, el borrado de cuentas fallaría al confirmar."""
        with connection.cursor() as cursor:
            cursor.execute("""SELECT DISTINCT p.proname FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
                              WHERE NOT t.tgisinternal AND (t.tgtype & 2)<>0 AND (t.tgtype & 8)<>0
                                AND p.prosrc NOT LIKE '%%chilito:borrado-de-cuenta%%' ORDER BY 1""")
            self.assertEqual([fila[0] for fila in cursor.fetchall()], ['chilito_capacidad_reglas'])

    def test_marca_solo_del_propietario(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT has_table_privilege('chilito_pkg_runtime', 'cuenta_en_borrado', 'INSERT'), "
                           "has_table_privilege('chilito_pkg_runtime', 'privacidad_decision', 'DELETE'), "
                           "has_table_privilege('chilito_pkg_runtime', 'cuentas_usuario', 'DELETE'), "
                           "has_function_privilege('chilito_pkg_runtime', 'chilito_eliminar_cuenta(bigint)', 'EXECUTE'), "
                           "has_function_privilege('chilito_pkg_iot', 'chilito_eliminar_cuenta(bigint)', 'EXECUTE')")
            self.assertEqual(cursor.fetchone(), (False, False, False, True, False))


class PadronDeCuentas(BaseHuerto):
    RUTA = '/api/admin/consentimientos/cuentas'

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.admin = cuenta('padron-admin@example.test', 'ver_consentimientos')
        self.sesion = self.cliente(self.admin)
        self.activa = cuenta('padron-activa@example.test')
        self.sin_verificar = cuenta('padron-sin-verificar@example.test', verificada=False)
        self.inactiva = cuenta('padron-inactiva@example.test')
        get_user_model().objects.filter(pk=self.inactiva.pk).update(is_active=False)

    def leer(self, consulta=''):
        respuesta = self.sesion.get(self.RUTA + consulta)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def test_dto_estricto_sin_secretos(self):
        datos = self.leer('?busqueda=padron-activa')
        self.assertEqual(datos['total'], 1)
        fila = datos['items'][0]
        # Sin el id interno de la cuenta: la pantalla no lo usa (minimización de datos).
        self.assertEqual(set(fila), {'email', 'status', 'emailVerified', 'createdAt', 'lastLogin'})
        self.assertEqual((fila['email'], fila['status'], fila['emailVerified']), ('padron-activa@example.test', 'activa', True))
        self.assertEqual(fila['createdAt'], self.activa.date_joined.isoformat())
        self.assertNotIn('pbkdf2', json.dumps(datos))
        self.assertNotIn('argon2', json.dumps(datos))

    def test_estado_y_totales(self):
        datos = self.leer('?busqueda=padron-')
        self.assertEqual(datos['totals'], {'total': 4, 'activas': 2, 'inactivas': 2})
        activas = self.leer('?estado=activas&busqueda=padron-')
        self.assertEqual(sorted(f['email'] for f in activas['items']), ['padron-activa@example.test', 'padron-admin@example.test'])
        self.assertEqual(activas['totals'], datos['totals'])
        inactivas = self.leer('?estado=inactivas&busqueda=padron-')
        self.assertEqual(sorted((f['email'], f['emailVerified']) for f in inactivas['items']),
                         [('padron-inactiva@example.test', True), ('padron-sin-verificar@example.test', False)])
        self.assertTrue(all(f['status'] == 'inactiva' for f in inactivas['items']))

    def test_fechas_y_paginacion(self):
        hoy = timezone.localdate()
        self.assertEqual(self.leer(f'?busqueda=padron-&desde={hoy.isoformat()}&hasta={hoy.isoformat()}')['total'], 4)
        self.assertEqual(self.leer(f'?busqueda=padron-&desde={(hoy + timedelta(days=1)).isoformat()}')['total'], 0)
        self.assertEqual(self.leer(f'?busqueda=padron-&hasta={(hoy - timedelta(days=7)).isoformat()}')['total'], 0)
        for numero in range(26):
            cuenta(f'padron-lote-{numero:02d}@example.test')
        primera, segunda = self.leer('?busqueda=padron-lote'), self.leer('?busqueda=padron-lote&page=2')
        self.assertEqual((len(primera['items']), len(segunda['items']), primera['total']), (25, 1, 26))
        self.assertEqual(primera['items'][0]['email'], 'padron-lote-25@example.test')     # lo más reciente primero

    def test_parametros_no_validos(self):
        for consulta in ('?estado=otra', '?desde=ayer', '?desde=2026-02-01&hasta=2026-01-01', '?x=1', '?page=0',
                         '?busqueda=' + 'a' * 300, '?desde=2026-W47-1', '?desde=2026-02-30', '?desde=２０２６-11-20',
                         '?hasta=20261120', '?desde=2026-11-20T00:00', '?busqueda=a%00b'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.sesion.get(self.RUTA + consulta).status_code, 400)

    def test_busqueda_con_inyeccion_sql_es_solo_texto(self):
        for carga in ("' OR 1=1--", "%' OR '1'='1", '%'):   # % no es comodín: el ORM lo escapa
            with self.subTest(carga=carga):
                datos = self.leer('?' + urlencode({'busqueda': carga}))
                self.assertEqual((datos['total'], datos['totals']['total']), (0, 0))

    def test_usuario_normal_y_admin_sin_factor_reciben_403(self):
        normal = self.cliente(self.activa)
        respuesta = normal.get(self.RUTA)
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (403, 'access-denied'))
        sin_factor = self.cliente(cuenta('padron-sin-factor@example.test', 'ver_consentimientos', factor=False))
        respuesta = sin_factor.get(self.RUTA)
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (403, 'mfa-required'))
        self.assertEqual(self.cliente().get(self.RUTA).status_code, 401)
