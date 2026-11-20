"""Correcciones de AUDITORIA_SEGURIDAD_SSSLC.md y de los dos bugs funcionales (ver REGISTRO_CORRECCIONES.md).

M-2 reautenticación reciente · M-3 caché de cuotas sin desalojo · B-3 cuota global de vinculación · B-8 contraseñas
filtradas · BUG-2 arranque legal en la nube y superadministración sin bloqueo. Todo sobre la base temporal de pruebas.
"""
import json
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache, caches
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, SimpleTestCase, TestCase, override_settings

from cuentas.validadores import ContrasenaFiltrada, veces_filtrada
from privacidad.models import Decision, Sujeto
from tests import cuenta, publicar_textos

P = '/_allauth/browser/v1/'
CLAVE = 'Frase de prueba para confirmar acciones criticas 42!'
AJENO = '00000000-0000-4000-8000-000000000001'


def cliente(usuario=None, **extra):
    c = Client(HTTP_HOST='127.0.0.1', **extra)
    if usuario is not None:
        c.force_login(usuario, backend='django.contrib.auth.backends.ModelBackend')
    return c


def post(c, ruta, datos=None):
    return c.post(ruta, json.dumps(datos or {}), content_type='application/json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))


class ReautenticacionReciente(TestCase):
    """M-2: las cinco acciones críticas piden haber confirmado la contraseña en los últimos 5 minutos."""
    CRITICAS = (
        ('post', '/api/admin/administradores/cuenta', {'email': 'nadie@example.test', 'capabilities': [], 'reason': 'Prueba de reautenticación'}),
        ('post', '/api/admin/equipos/999999/rotar', {}),
        ('post', '/api/admin/equipos/999999/desvincular', {}),
        ('post', f'/api/admin/sesiones/{AJENO}/accion', {'type': 'regar', 'plant': 1, 'duration': 5}),
        ('get', '/api/admin/consentimientos/exportar', None),
    )

    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        cache.clear()
        self.admin = cuenta('critico@example.test', 'gestionar_administradores', 'gestionar_dispositivos', 'atender_soporte',
                            'ver_consentimientos', password=CLAVE)
        self.c = cliente(self.admin)

    def pedir(self, metodo, ruta, datos):
        return post(self.c, ruta, datos) if metodo == 'post' else self.c.get(ruta)

    def reautenticar(self, clave=CLAVE):
        return self.c.post(P + 'auth/reauthenticate', json.dumps({'password': clave}), content_type='application/json')

    def test_sin_reautenticar_responde_403_y_no_deja_recibo(self):
        from web.models import Idempotencia
        for metodo, ruta, datos in self.CRITICAS:
            with self.subTest(ruta=ruta):
                respuesta = self.pedir(metodo, ruta, datos)
                self.assertEqual((respuesta.status_code, respuesta.json()['code']), (403, 'reauthentication-required'))
        self.assertFalse(Idempotencia.objects.filter(actor=self.admin).exists())

    def test_contrasena_equivocada_no_abre_la_ventana(self):
        self.assertNotEqual(self.reautenticar('otra frase equivocada pero larga').status_code, 200)
        self.assertEqual(post(self.c, '/api/admin/equipos/999999/rotar').json()['code'], 'reauthentication-required')

    def test_tras_reautenticar_se_atiende(self):
        self.assertEqual(self.reautenticar().status_code, 200)
        for metodo, ruta, datos in self.CRITICAS:
            with self.subTest(ruta=ruta):
                respuesta = self.pedir(metodo, ruta, datos)
                codigo = respuesta.json().get('code') if respuesta['Content-Type'].startswith('application/json') else None
                self.assertNotEqual(codigo, 'reauthentication-required')
        exportado = self.c.get('/api/admin/consentimientos/exportar')
        self.assertEqual(exportado.status_code, 200)
        self.assertIn('text/csv', exportado['Content-Type'])

    def test_la_ventana_dura_cinco_minutos(self):
        self.assertEqual(self.reautenticar().status_code, 200)
        self.assertNotEqual(post(self.c, '/api/admin/equipos/999999/rotar').json().get('code'), 'reauthentication-required', 'dentro de la ventana')
        sesion = self.c.session                                  # el registro de allauth envejece 6 minutos
        registros = sesion['account_authentication_methods']
        for registro in registros:
            registro['at'] -= 360
        sesion['account_authentication_methods'] = registros
        sesion.save()
        self.assertEqual(post(self.c, '/api/admin/equipos/999999/rotar').json()['code'], 'reauthentication-required')

    def test_las_demas_rutas_del_panel_no_cambian(self):
        self.assertEqual(self.c.get('/api/admin/equipos').status_code, 200)
        self.assertEqual(self.c.get('/api/admin/consentimientos').status_code, 200)


class CuotasSinDesalojo(TestCase):
    """M-3: llenar la caché por encima de MAX_ENTRIES ya no borra contadores vigentes (solo los expirados)."""

    def test_un_contador_vigente_sobrevive_a_la_purga(self):
        ajustes = {'default': {'BACKEND': 'web.cache.CacheSinDesalojo', 'LOCATION': 'cuentas_cuotas_acceso', 'TIMEOUT': 3600,
                               'OPTIONS': {'MAX_ENTRIES': 5, 'CULL_FREQUENCY': 2}}}
        with override_settings(CACHES=ajustes):
            cuotas = caches['default']
            cuotas.clear()
            cuotas.set('fallos:cuenta-objetivo', 4, 600)
            cuotas.set('vencida', 1, -1)
            for numero in range(40):             # un atacante genera muchas claves distintas
                cuotas.set(f'relleno:{numero}', 1, 600)
            self.assertEqual(cuotas.get('fallos:cuenta-objetivo'), 4, 'el contador de fallos sigue en pie')
            self.assertIsNone(cuotas.get('vencida'))
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM cuentas_cuotas_acceso WHERE cache_key LIKE '%%vencida'")
                self.assertEqual(cursor.fetchone()[0], 0, 'la purga quita lo expirado')
            cuotas.clear()


class CuotaGlobalDeVinculacion(TestCase):
    """B-3: un tope global antes de PBKDF2, aunque cada intento use otra IP u otro identificador."""

    def setUp(self):
        cache.clear()

    def test_tope_global(self):
        limites = {**settings.ACCOUNT_RATE_LIMITS, 'vincular_dispositivo_global': '2/m/key'}
        with override_settings(ACCOUNT_RATE_LIMITS=limites):
            estados = []
            for numero in range(3):
                respuesta = Client(HTTP_HOST='127.0.0.1', REMOTE_ADDR=f'198.51.100.{numero + 1}').post(
                    '/api/dispositivos/vincular', json.dumps({'identifier': f'CHI-X{numero}', 'credential': 'x' * 20, 'code': 'ABCD1234'}),
                    content_type='application/json')
                estados.append(respuesta.status_code)
        self.assertEqual(estados, [200, 200, 429])


class ContrasenasFiltradas(SimpleTestCase):
    """B-8: consulta k-anónima; solo salen 5 caracteres del SHA-1 y un fallo del servicio no bloquea el registro."""
    # SHA-1 de «password»: 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8.
    RESPUESTA = '1E4C9B93F3F0682250B6CF8331B7EE68FD8:3861493\r\n0000000000000000000000000000000000A:0\r\n'

    def test_solo_envia_el_prefijo(self):
        pedidos = []
        self.assertEqual(veces_filtrada('password', lambda prefijo: pedidos.append(prefijo) or self.RESPUESTA), 3861493)
        self.assertEqual(pedidos, ['5BAA6'])

    def test_no_filtrada_y_servicio_caido(self):
        self.assertEqual(veces_filtrada('una frase que no aparece en la lista', lambda prefijo: self.RESPUESTA), 0)

        def caido(prefijo):
            raise TimeoutError

        self.assertIsNone(veces_filtrada('password', caido))

    def test_validador_con_interruptor(self):
        validador = ContrasenaFiltrada(consultar=lambda prefijo: self.RESPUESTA)
        with override_settings(CHILITO_VERIFICAR_FILTRADAS=False):
            validador.validate('password')              # apagado: no consulta
        with override_settings(CHILITO_VERIFICAR_FILTRADAS=True):
            with self.assertRaises(ValidationError) as rechazo:
                validador.validate('password')
            self.assertEqual(rechazo.exception.code, 'password_pwned')
            ContrasenaFiltrada(consultar=lambda prefijo: (_ for _ in ()).throw(OSError())).validate('password')   # caído: pasa


@override_settings(ELCHILITO_REGISTRATION_ENABLED=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ArranqueLegal(TestCase):
    """BUG-2: en una base vacía y sin textos publicados nadie podía registrarse, así que nunca había superadministración
    que publicara los textos. Sin textos publicados en esta clase (no llama a publicar_textos)."""

    def setUp(self):
        cache.clear()
        self.c = Client(enforce_csrf_checks=True, HTTP_HOST='127.0.0.1')
        self.c.get('/api/acceso/configuracion')

    def registrar(self, correo='primera@example.test'):
        token = self.c.cookies.get('csrftoken')
        return self.c.post(P + 'auth/signup', json.dumps({'email': correo, 'password': CLAVE, 'termsAccepted': True, 'privacyRead': True}),
                           content_type='application/json', HTTP_X_CSRFTOKEN=token.value if token else '')

    def confirmar(self):
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')

    def test_sin_variable_el_registro_explica_la_causa(self):
        respuesta = self.registrar()
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (503, 'legal-no-publicado'))
        self.assertFalse(get_user_model().objects.exists())

    def test_sin_variable_la_base_rechaza_incluso_la_primera_cuenta(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user('sola@example.test', CLAVE)     # sin la marca de arranque
            self.confirmar()
        with override_settings(CHILITO_BYPASS_LEGAL_CHECK=False), self.assertRaises(ValidationError), transaction.atomic():
            cuenta('sola@example.test')                                        # ni por la aplicación

    @override_settings(CHILITO_BYPASS_LEGAL_CHECK=True)
    def test_con_variable_se_crea_solo_la_primera_cuenta(self):
        self.assertEqual(self.registrar().status_code, 401, 'cuenta creada; falta verificar el correo')
        primera = get_user_model().objects.get()
        self.assertTrue(Sujeto.objects.filter(usuario=primera, ambito='cuenta').exists())
        self.assertFalse(Decision.objects.filter(usuario=primera).exists(), 'sin textos no hay actos que guardar')
        self.confirmar()                                        # la base (web.0008) la admite
        segunda = self.registrar('segunda@example.test')
        self.assertEqual((segunda.status_code, segunda.json()['code']), (503, 'legal-no-publicado'))
        self.assertEqual(get_user_model().objects.count(), 1)

    @override_settings(CHILITO_BYPASS_LEGAL_CHECK=True)
    def test_la_base_rechaza_una_segunda_cuenta_aunque_la_app_lo_pida(self):
        cuenta('primera@example.test')
        self.confirmar()
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user('segunda@example.test', CLAVE)
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('chilito.arranque_legal', 'on', true)")
            self.confirmar()

    @override_settings(CHILITO_BYPASS_LEGAL_CHECK=True)
    def test_con_textos_publicados_la_variable_no_tiene_efecto(self):
        publicar_textos()
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user('sin-aceptar@example.test', CLAVE)
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('chilito.arranque_legal', 'on', true)")
            self.confirmar()
        usuario = cuenta('normal@example.test')                 # el registro normal guarda sus dos actos
        self.assertEqual(Decision.objects.filter(usuario=usuario).count(), 2)

    @override_settings(CHILITO_BYPASS_LEGAL_CHECK=True)
    def test_superadministracion_publica_los_textos_y_no_queda_bloqueada(self):
        superadmin = cuenta('super@example.test', 'gestionar_administradores', 'gestionar_legales')
        self.confirmar()
        panel = cliente(superadmin)
        self.assertEqual(panel.get('/api/cuenta').json()['pendingLegal'], [], 'sin textos no hay nada pendiente')
        self.assertEqual(panel.get('/api/admin/legales?tipo=terminos').status_code, 200, 'entra al panel de textos')
        publicar_textos()
        perfil = panel.get('/api/cuenta').json()
        self.assertEqual({p['type'] for p in perfil['pendingLegal']}, {'terminos', 'aviso_privacidad'})
        self.assertEqual(panel.get('/api/admin/legales?tipo=terminos').status_code, 200, 'con textos pendientes sigue en el panel')
        aceptar = post(panel, '/api/legales/aceptar', {'documents': [p['documentId'] for p in perfil['pendingLegal']]})
        self.assertEqual(aceptar.status_code, 200, aceptar.content)
        self.assertEqual(panel.get('/api/cuenta').json()['pendingLegal'], [])


class NombreYouGarden(TestCase):
    """El proyecto se llama YouGarden: las guías publicadas (web.0007 + web.0009) y los correos ya no dicen «El Chilito»."""

    def test_guias_y_correos_con_el_nombre_nuevo(self):
        from datos.models import GuiaCuidado
        self.assertFalse(GuiaCuidado.objects.filter(respuesta__contains='El Chilito').exists())
        self.assertIn('En YouGarden, el ciclo', GuiaCuidado.objects.get(clave='ciclo-habanero-fin').respuesta)
        self.assertEqual(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, '[YouGarden] ')
        self.assertEqual(settings.MFA_TOTP_ISSUER, 'YouGarden')
