"""Pruebas HTTP de la frontera JSON, en el mismo origen y sobre PostgreSQL con cuentas sintéticas.

No ejercitan la interfaz, el SMTP ni el hardware. Usan las guías y el buzón como escrituras de ejemplo."""
import json
import logging
import uuid
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase

from datos.models import Auditoria, ConsultaProducto, GuiaCuidado
from tests import aceptar_vigentes, cuenta, publicar_textos
from web.middleware import ActorDeBase


class BaseWeb(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        cache.clear()
        self.usuaria = cuenta('web-usuaria@example.test')
        self.admin = cuenta('web-admin@example.test', 'gestionar_guias')
        self.buzon = cuenta('web-buzon@example.test', 'atender_consultas')
        self.client = self.cliente(self.usuaria)

    def cliente(self, usuario=None, csrf=False):
        cliente = Client(enforce_csrf_checks=csrf, HTTP_HOST='127.0.0.1')
        if usuario is not None:
            cliente.force_login(usuario, backend='django.contrib.auth.backends.ModelBackend')
        if csrf:
            self.assertEqual(cliente.get('/api/acceso/configuracion').status_code, 200)
        return cliente

    def post(self, ruta, datos, *, cliente=None, clave=None, csrf=True):
        cliente = cliente or self.client
        cabeceras = {'HTTP_IDEMPOTENCY_KEY': str(clave or uuid.uuid4())}
        if csrf and 'csrftoken' in cliente.cookies:
            cabeceras['HTTP_X_CSRFTOKEN'] = cliente.cookies['csrftoken'].value
        return cliente.post(ruta, json.dumps(datos), content_type='application/json', **cabeceras)


def guia(**cambios):
    return {'question': '¿Qué reviso?', 'answer': 'Primero.', 'order': 10, 'sourceName': '', 'sourceUrl': '', **cambios}


class Sesion(BaseWeb):
    def test_rutas_privadas_y_de_administracion_exigen_sesion(self):
        anonimo = self.cliente()
        for ruta in ['/api/cuenta', '/api/guias', '/api/admin/guias', '/api/admin/consultas', '/api/admin/flota', '/api/admin/soporte', '/api/admin/mantenimientos']:
            with self.subTest(ruta=ruta):
                self.assertEqual(anonimo.get(ruta).status_code, 401)

    def test_rol_y_capacidades_las_deriva_el_servidor(self):
        perfil = self.client.get('/api/cuenta').json()
        self.assertEqual((perfil['role'], perfil['capabilities']), ('user', []))
        self.assertEqual((perfil['pendingLegal'], perfil['gardenAssigned']), ([], False))
        perfil = self.cliente(self.admin).get('/api/cuenta').json()
        self.assertEqual((perfil['role'], perfil['capabilities'], perfil['mfaRequired']), ('admin', ['gestionar_guias'], False))

    def test_cuenta_sin_correo_verificado_no_entra(self):
        sin_verificar = cuenta('web-sin-verificar@example.test', verificada=False)
        respuesta = self.cliente(sin_verificar).get('/api/cuenta')
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (403, 'verification-required'))

    def test_textos_nuevos_quedan_pendientes_hasta_aceptarlos(self):
        publicar_textos('1.1')
        pendientes = self.client.get('/api/cuenta').json()['pendingLegal']
        self.assertEqual(sorted(p['type'] for p in pendientes), ['aviso_privacidad', 'terminos'])
        self.assertEqual({p['version'] for p in pendientes}, {'1.1'})
        for usuario in (self.usuaria, self.admin, self.buzon):
            aceptar_vigentes(usuario)
        self.assertEqual(self.client.get('/api/cuenta').json()['pendingLegal'], [])

    def test_las_capacidades_son_independientes(self):
        for ruta in ('/api/admin/guias', '/api/admin/consultas'):
            self.assertEqual(self.client.get(ruta).status_code, 403, ruta)
        self.assertEqual(self.cliente(self.admin).get('/api/admin/guias').status_code, 200)
        self.assertEqual(self.cliente(self.admin).get('/api/admin/consultas').status_code, 403)
        self.assertEqual(self.cliente(self.buzon).get('/api/admin/consultas').status_code, 200)


class Escrituras(BaseWeb):
    def test_rechaza_falta_de_clave_campos_extra_y_tipos_no_validos(self):
        cliente = self.cliente(self.admin)
        sin_clave = cliente.post('/api/admin/guias', json.dumps(guia()), content_type='application/json')
        self.assertEqual(sin_clave.status_code, 400)
        self.assertEqual(self.post('/api/admin/guias', guia(), cliente=cliente, clave='no-es-uuid').status_code, 400)
        for cuerpo in ([], None, guia(question=[]), {**guia(), 'actor': '1'}, {**guia(), 'status': 'publicada'}):
            with self.subTest(cuerpo=type(cuerpo).__name__):
                self.assertEqual(self.post('/api/admin/guias', cuerpo, cliente=cliente).status_code, 400)
        self.assertFalse(GuiaCuidado.objects.exclude(estado='publicada').exists())

    def test_exige_json(self):
        respuesta = self.cliente(self.admin).post('/api/admin/guias', guia(), HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertIn(respuesta.status_code, [400, 415])

    def test_clave_repetida_devuelve_lo_mismo_sin_duplicar_y_cuerpo_distinto_choca(self):
        cliente, clave = self.cliente(self.admin), uuid.uuid4()
        primera = self.post('/api/admin/guias', guia(), cliente=cliente, clave=clave)
        segunda = self.post('/api/admin/guias', guia(), cliente=cliente, clave=clave)
        self.assertEqual((primera.status_code, primera.json()), (200, segunda.json()))
        self.assertEqual(GuiaCuidado.objects.filter(estado='borrador').count(), 1)
        self.assertEqual(Auditoria.objects.filter(accion='crear_guia').count(), 1)
        distinta = self.post('/api/admin/guias', guia(question='Otra'), cliente=cliente, clave=clave)
        self.assertEqual(distinta.status_code, 409)

    def test_csrf_es_obligatorio(self):
        estricto = self.cliente(self.admin, csrf=True)
        self.assertEqual(self.post('/api/admin/guias', guia(), cliente=estricto, csrf=False).status_code, 403)
        self.assertEqual(self.post('/api/admin/guias', guia(), cliente=estricto).status_code, 200)

    def test_un_get_no_escribe(self):
        guia_id = GuiaCuidado.objects.first().pk
        respuesta = self.cliente(self.admin).get(f'/api/admin/guias/{guia_id}/publicar')
        self.assertEqual(respuesta.status_code, 405)

    def test_paginacion_acotada_y_pagina_invalida_rechazada(self):
        for pagina in ['0', '-1', 'x', '10001']:
            self.assertEqual(self.cliente(self.buzon).get('/api/admin/consultas', {'page': pagina}).status_code, 400)
        for numero in range(3):
            ConsultaProducto.objects.create(correo='a@example.test', mensaje=f'Hola {numero}', huella=f'{numero:064x}')
        cuerpo = self.cliente(self.buzon).get('/api/admin/consultas', {'page': '1'}).json()
        self.assertEqual((cuerpo['total'], cuerpo['page'], len(cuerpo['items'])), (3, 1, 3))
        mas_alla = self.cliente(self.buzon).get('/api/admin/consultas', {'page': '5'}).json()
        self.assertEqual((mas_alla['items'], mas_alla['total']), ([], 3))

    def test_la_capa_http_delega_el_conteo_a_la_paginacion(self):
        import inspect
        from web import api
        fuente = inspect.getsource(api.page)
        self.assertIn('paginar(', fuente)
        self.assertNotIn('.count(', fuente)

    def test_respuestas_no_cacheables_y_con_proteccion_del_navegador(self):
        for ruta in ['/api/cuenta', '/api/huertos', '/api/admin/flota']:
            respuesta = self.client.get(ruta)
            self.assertIn('no-store', respuesta.get('Cache-Control', ''))
            self.assertEqual(respuesta.get('X-Frame-Options'), 'DENY')
            politica = respuesta.get('Content-Security-Policy', '')
            for regla in ("script-src 'self'", "object-src 'none'", "frame-ancestors 'none'"):
                self.assertIn(regla, politica)


class ActorEnLaTransaccion(BaseWeb):
    """ASVS V8: la base exige saber quién escribe; el servidor lo fija desde la sesión, nunca desde la petición."""

    def actor_visto(self, usuario):
        def vista(request):
            with connection.cursor() as cursor:
                cursor.execute('SELECT chilito_actor()')
                return HttpResponse(str(cursor.fetchone()[0]))
        peticion = RequestFactory().get('/')
        peticion.user = usuario
        return ActorDeBase(vista)(peticion).content.decode()

    def test_con_sesion_fija_la_cuenta(self):
        self.assertEqual(self.actor_visto(self.usuaria), str(self.usuaria.pk))

    def test_sin_sesion_no_fija_nada(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertEqual(self.actor_visto(AnonymousUser()), 'None')

    def test_la_peticion_no_puede_elegir_el_actor(self):
        respuesta = self.post('/api/admin/guias', {**guia(), 'actor': str(self.usuaria.pk)}, cliente=self.cliente(self.admin))
        self.assertEqual(respuesta.status_code, 400)


class ReglasDeLaBase(BaseWeb):
    def test_error_23514_responde_409_generico_y_el_detalle_va_solo_al_registro(self):
        def rechazar(*args, **kwargs):
            with connection.cursor() as cursor:
                cursor.execute("SELECT chilito_rechazar('detalle-interno-de-prueba')")
        with patch('datos.guias.crear', rechazar), self.assertLogs('web.respuestas', 'WARNING') as registro:
            respuesta = self.post('/api/admin/guias', guia(), cliente=self.cliente(self.admin))
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'regla-de-datos'))
        self.assertNotIn('detalle-interno-de-prueba', respuesta.content.decode())
        self.assertIn('detalle-interno-de-prueba', registro.output[0])

    def test_otro_error_de_integridad_sigue_siendo_conflicto_de_operacion(self):
        from django.db import IntegrityError

        def duplicar(*args, **kwargs):
            raise IntegrityError('unique')
        with patch('datos.guias.crear', duplicar):
            respuesta = self.post('/api/admin/guias', guia(), cliente=self.cliente(self.admin))
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'operation-conflict'))
