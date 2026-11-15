"""Guías de cuidado sobre PostgreSQL temporal: contenido compartido, permisos, validación y carga inicial."""
import importlib
import json
import secrets
import uuid
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import Client, TransactionTestCase

from datos import guias, services
from datos.models import Auditoria, GuiaCuidado
from datos.tests.test_vinculacion import en_paralelo
from huerto.models import Huerto, Membresia

CARGA = importlib.import_module('datos.migrations.0012_guias_iniciales')
PREGUNTAS = ['¿Cómo comienzo a germinar mis semillas de habanero?', '¿Cuánto puede tardar en brotar y qué debo observar?',
             '¿Cómo reconozco que la plántula está lista para trasplantar?', '¿Para qué sirve la perlita y cómo reviso el sustrato?',
             '¿Cuándo debo revisar el riego de mis plantas?', '¿Qué significa rellenar el depósito y registrar la recarga?',
             '¿Cómo reviso las mangueras y los goteros?', '¿Cómo identifico y registro una cosecha?',
             '¿Qué hago si no hay lecturas o el dispositivo está desconectado?']


def contenido(**cambios):
    return {'question': '¿Qué reviso?', 'answer': 'Primero.\n\nDespués.', 'order': 10, 'sourceName': '', 'sourceUrl': '', **cambios}


class Base(TransactionTestCase):
    def setUp(self):
        if not str(connection.settings_dict['NAME']).startswith('test_chilito_integracion_sinteticos'):
            raise RuntimeError('Solo en la base temporal de pruebas.')
        cache.clear()
        with connection.cursor() as cursor:     # quita la carga inicial que dejó la migración
            cursor.execute('TRUNCATE datos_guiacuidado CASCADE')
        self.admin = self.cuenta('guias-a@example.test', capacidad=True)
        self.admin2 = self.cuenta('guias-b@example.test', capacidad=True)
        self.usuaria = self.cuenta('usuaria@example.test')

    def cuenta(self, email, capacidad=False, factor=None, **campos):
        user = get_user_model().objects.create_user(email, secrets.token_urlsafe(24), **campos)
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
        if capacidad:
            user.user_permissions.add(Permission.objects.get(content_type__app_label='datos', codename='gestionar_guias'))
        if capacidad if factor is None else factor:
            Authenticator.objects.create(user=user, type='totp', data={})
        return user

    def sesion(self, user, **opciones):
        cliente = Client(**opciones)
        cliente.force_login(user)
        return cliente

    def post(self, cliente, ruta, datos, clave=None):
        return cliente.post(ruta, json.dumps(datos), content_type='application/json', HTTP_IDEMPOTENCY_KEY=str(clave or uuid.uuid4()))

    def crear(self, cliente=None, **cambios):
        r = self.post(cliente or self.sesion(self.admin), '/api/admin/guias', contenido(**cambios))
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()['guide']

    def accion(self, cliente, guia, accion, datos=None):
        return self.post(cliente, f"/api/admin/guias/{guia['id']}/{accion}", {'version': guia['version'], **(datos or {})})

    def publicadas(self, user=None):
        r = self.sesion(user or self.usuaria).get('/api/guias')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()['guides']

    def panel(self, cliente):
        return {g['id']: g for g in cliente.get('/api/admin/guias').json()['guides']}


class CicloDeVida(Base):
    def test_crear_consultar_editar_ordenar_publicar_retirar_y_republicar(self):
        c = self.sesion(self.admin)
        g = self.crear(c, question='¿Primera?', order=20)
        self.assertEqual(g['state'], 'borrador')
        self.assertEqual(self.publicadas(), [])
        self.assertEqual(self.panel(c)[g['id']]['question'], '¿Primera?')
        r = self.accion(c, g, 'editar', contenido(question='¿Editada?', answer='Texto nuevo.', order=5, sourceName='Fuente', sourceUrl='https://example.test/a'))
        self.assertEqual(r.status_code, 200, r.content)
        g = r.json()['guide']
        self.assertEqual(g['version'], 2)
        self.assertEqual(g['state'], 'borrador', 'editar no publica')
        self.assertEqual(self.publicadas(), [])
        g = self.accion(c, g, 'publicar').json()['guide']
        self.assertEqual(g['state'], 'publicada')
        visible = self.publicadas()
        self.assertEqual([x['question'] for x in visible], ['¿Editada?'])
        self.assertEqual(visible[0]['source'], {'name': 'Fuente', 'url': 'https://example.test/a'})
        self.assertNotIn('id', visible[0]); self.assertNotIn('updatedBy', visible[0])
        g = self.accion(c, g, 'retirar').json()['guide']
        self.assertEqual(g['state'], 'retirada')
        self.assertEqual(self.publicadas(), [])
        self.assertEqual(GuiaCuidado.objects.count(), 1, 'baja lógica')
        self.assertEqual(self.panel(c)[g['id']]['state'], 'retirada')
        g = self.accion(c, g, 'publicar').json()['guide']
        self.assertEqual(len(self.publicadas()), 1)
        self.assertEqual(g['version'], 5)

    def test_orden_configurado(self):
        c = self.sesion(self.admin)
        tres = [self.crear(c, question=q, order=o) for q, o in [('¿C?', 30), ('¿A?', 10), ('¿B?', 20)]]
        for g in tres:
            self.accion(c, g, 'publicar')
        self.assertEqual([x['question'] for x in self.publicadas()], ['¿A?', '¿B?', '¿C?'])
        primero = GuiaCuidado.objects.get(pregunta='¿C?')
        self.post(c, f'/api/admin/guias/{primero.pk}/editar', {**contenido(question='¿C?', order=1), 'version': primero.version})
        self.assertEqual([x['question'] for x in self.publicadas()], ['¿C?', '¿A?', '¿B?'])

    def test_transiciones_no_permitidas(self):
        c = self.sesion(self.admin)
        g = self.crear(c)
        self.assertEqual(self.accion(c, g, 'retirar').json()['code'], 'stale-record')
        g = self.accion(c, g, 'publicar').json()['guide']
        self.assertEqual(self.accion(c, g, 'publicar').json()['code'], 'stale-record')

    def test_persiste_tras_recargar_y_volver_a_iniciar_sesion(self):
        g = self.crear(question='¿Persiste?')
        self.accion(self.sesion(self.admin), g, 'publicar')
        c = self.sesion(self.admin)
        c.logout()
        self.assertEqual(c.get('/api/admin/guias').status_code, 401)
        self.assertEqual(self.sesion(self.admin).get('/api/admin/guias').json()['guides'][0]['question'], '¿Persiste?')
        self.assertEqual(self.publicadas()[0]['question'], '¿Persiste?')

    def test_dos_administradores_gestionan_el_mismo_contenido(self):
        g = self.crear(self.sesion(self.admin))
        otro = self.sesion(self.admin2)
        g = self.accion(otro, g, 'editar', contenido(question='¿Del segundo?')).json()['guide']
        fila = self.panel(otro)[g['id']]
        self.assertEqual((fila['createdBy'], fila['updatedBy']), (self.admin.email, self.admin2.email))
        self.assertEqual(self.accion(self.sesion(self.admin), g, 'publicar').status_code, 200)
        fila = GuiaCuidado.objects.get()
        self.assertEqual((fila.creado_por, fila.actualizado_por), (self.admin, self.admin))
        self.assertEqual(list(Auditoria.objects.filter(guia=fila).order_by('creada_en').values_list('actor__email', 'accion')),
                         [(self.admin.email, 'guide-created'), (self.admin2.email, 'guide-updated'), (self.admin.email, 'guide-published')])

    def test_independiente_del_correo_y_de_quien_la_creo(self):
        g = self.crear(self.sesion(self.admin))
        get_user_model().objects.filter(pk=self.admin.pk).update(email='correo-nuevo@example.test')
        EmailAddress.objects.filter(user=self.admin).update(email='correo-nuevo@example.test')
        self.admin.refresh_from_db()
        c = self.sesion(self.admin)
        self.assertEqual(self.panel(c)[g['id']]['createdBy'], 'correo-nuevo@example.test')
        self.assertEqual(self.accion(c, g, 'publicar').status_code, 200, 'la misma cuenta sigue gestionando')
        # Autorizar a otra cuenta y retirar la capacidad a la creadora no toca el contenido.
        self.admin.user_permissions.clear()
        nueva = self.cuenta('guias-c@example.test', capacidad=True)
        self.assertEqual(len(self.panel(self.sesion(nueva))), 1)
        self.assertEqual(self.sesion(self.admin).get('/api/admin/guias').status_code, 403)
        self.assertEqual(len(self.publicadas()), 1)


class Autorizacion(Base):
    def rutas(self, g):
        return [('/api/admin/guias', contenido()), (f"/api/admin/guias/{g['id']}/editar", {**contenido(), 'version': 1}),
                (f"/api/admin/guias/{g['id']}/publicar", {'version': 1}), (f"/api/admin/guias/{g['id']}/retirar", {'version': 1})]

    def test_rechazo_por_api_directa(self):
        g = self.crear()
        sin_capacidad = {'usuaria': self.usuaria, 'staff': self.cuenta('staff@example.test', factor=True, is_staff=True),
                         'superusuario': self.cuenta('root@example.test', factor=True, is_staff=True, is_superuser=True)}
        for nombre, user in sin_capacidad.items():
            c = self.sesion(user)
            with self.subTest(nombre):
                self.assertEqual(c.get('/api/admin/guias').status_code, 403)
                for ruta, datos in self.rutas(g):
                    self.assertEqual(self.post(c, ruta, datos).status_code, 403, ruta)
        fila = GuiaCuidado.objects.get()
        self.assertEqual((fila.estado, fila.version), ('borrador', 1))

    def test_capacidad_sin_segundo_factor(self):
        user = self.cuenta('sinfactor@example.test', capacidad=True, factor=False)
        c = self.sesion(user)
        r = c.get('/api/admin/guias')
        self.assertEqual((r.status_code, r.json()['code']), (403, 'mfa-required'))
        self.assertEqual(self.post(c, '/api/admin/guias', contenido()).status_code, 403)
        self.assertFalse(GuiaCuidado.objects.exists())

    def test_capacidad_otorgada_a_is_staff_no_se_deduce(self):
        for actor in (self.usuaria, self.cuenta('s2@example.test', factor=True, is_staff=True, is_superuser=True)):
            with self.assertRaises(PermissionDenied):
                guias.panel(actor)

    def test_sin_sesion_y_csrf(self):
        g = self.crear()
        anonimo = Client()
        self.assertEqual(anonimo.get('/api/guias').status_code, 401)
        self.assertEqual(self.post(anonimo, f"/api/admin/guias/{g['id']}/publicar", {'version': 1}).status_code, 401)
        estricto = self.sesion(self.admin, enforce_csrf_checks=True)
        self.assertEqual(self.post(estricto, f"/api/admin/guias/{g['id']}/publicar", {'version': 1}).status_code, 403)
        self.assertEqual(GuiaCuidado.objects.get().estado, 'borrador')

    def test_usuario_solo_lee_publicadas(self):
        c = self.sesion(self.admin)
        borrador, retirada, publicada = (self.crear(c, question=q) for q in ('¿Borrador?', '¿Retirada?', '¿Publicada?'))
        r = self.accion(c, retirada, 'publicar').json()['guide']
        self.accion(c, r, 'retirar')
        self.accion(c, publicada, 'publicar')
        self.assertEqual([x['question'] for x in self.publicadas()], ['¿Publicada?'])

    def test_sin_huerto_lee_pero_no_habilita_acciones(self):
        c = self.sesion(self.admin)
        self.accion(c, self.crear(c), 'publicar')
        self.assertFalse(Membresia.objects.filter(usuario=self.usuaria).exists())
        s = self.sesion(self.usuaria)
        self.assertEqual(len(s.get('/api/guias').json()['guides']), 1)
        r = self.post(s, '/api/huertos/actual/mantenimiento', {'type': 'refill'})
        self.assertEqual((r.status_code, r.json()['code']), (403, 'garden-unassigned'))
        self.assertEqual(s.get('/api/huertos/actual/mantenimiento').status_code, 403)

    def test_con_huerto_ajeno_no_cambia_la_lectura(self):
        Membresia.objects.create(usuario=self.usuaria, huerto=Huerto.objects.create(clave='g-1', nombre='G'))
        self.assertEqual(self.publicadas(), [])


class Validacion(Base):
    def rechazado(self, **cambios):
        r = self.post(self.sesion(self.admin), '/api/admin/guias', contenido(**cambios))
        self.assertEqual(r.status_code, 400, f'{cambios}: {r.content}')

    def test_tipos_longitudes_y_orden(self):
        for cambios in ({'question': ''}, {'question': '   '}, {'question': 7}, {'question': None}, {'question': 'x' * 201}, {'question': 'a\nb'},
                        {'answer': ''}, {'answer': ['x']}, {'answer': 'x' * 4001}, {'answer': 'a\u0000b'},
                        {'order': 0}, {'order': 10000}, {'order': -1}, {'order': '10'}, {'order': 1.5}, {'order': True}, {'order': None},
                        {'sourceName': 'x' * 121}, {'sourceName': 3}):
            with self.subTest(cambios):
                self.rechazado(**cambios)
        self.assertFalse(GuiaCuidado.objects.exists())

    def test_campos_no_permitidos(self):
        c = self.sesion(self.admin)
        for extra in ({'state': 'publicada'}, {'estado': 'publicada'}, {'key': 'otra'}, {'creado_por': 1}, {'version': 9}):
            with self.subTest(extra):
                self.assertEqual(self.post(c, '/api/admin/guias', {**contenido(), **extra}).status_code, 400)
        self.assertFalse(GuiaCuidado.objects.exists())

    def test_version_y_estado_invalidos(self):
        c = self.sesion(self.admin)
        g = self.crear(c)
        for version in ('1', None, 1.0, True, 0):
            with self.subTest(version):
                self.assertEqual(self.post(c, f"/api/admin/guias/{g['id']}/publicar", {'version': version}).status_code, 400)
        self.assertEqual(self.post(c, f'/api/admin/guias/{uuid.uuid4()}/publicar', {'version': 1}).status_code, 403)

    def test_enlaces_solo_http_y_https(self):
        for url in ('javascript:alert(1)', 'JAVASCRIPT:alert(1)', ' javascript:alert(1)', 'data:text/html,x', 'ftp://example.test/a', 'file:///etc/passwd',
                    'vbscript:x', '//example.test/a', 'example.test', 'https://', 'https:///ruta', 'https://exa mple.test/', 'https://u:p@example.test/', 'https:\\\\example.test',
                    'HTTPS://example.test/', 'https://example.test/' + 'a' * 500):
            with self.subTest(url):
                self.rechazado(sourceName='Fuente', sourceUrl=url)
        self.rechazado(sourceUrl='https://example.test/a')
        for url in ('https://example.test/a?b=1#c', 'http://example.test', 'https://example.test:8443/x'):
            self.assertEqual(self.crear(sourceName='Fuente', sourceUrl=url)['state'], 'borrador', url)
        self.assertEqual(self.crear(sourceName='Libro impreso')['state'], 'borrador')

    def test_html_se_conserva_como_texto(self):
        c = self.sesion(self.admin)
        malicioso = '<script>alert(1)</script> <img src=x onerror=alert(1)> & "c"\n\nPárrafo <b>dos</b>'
        self.accion(c, self.crear(c, question='<b>¿HTML?</b>', answer=malicioso), 'publicar')
        r = self.sesion(self.usuaria).get('/api/guias')
        self.assertEqual(r['Content-Type'], 'application/json')
        self.assertEqual(r.json()['guides'][0]['answer'], malicioso)
        self.assertEqual(r.json()['guides'][0]['question'], '<b>¿HTML?</b>')

    def test_clave_valida_con_cualquier_pregunta(self):
        for pregunta in ('¿qué__pasa_si?', '<b>__x__</b>', '¿¿¿???', 'a' * 200, '-_-', 'año ñandú'):
            with self.subTest(pregunta):
                self.assertRegex(self.crear(question=pregunta)['key'], r'^[a-z0-9]+(-[a-z0-9]+)*$')

    def test_saltos_de_linea_y_espacios(self):
        g = self.crear(answer='  uno\r\n\r\ndos tres\t ')
        self.assertEqual(GuiaCuidado.objects.get(pk=g['id']).respuesta, 'uno\n\ndos tres')

    def test_error_de_base_es_generico(self):
        with patch('web.api.guias.publicadas', side_effect=DatabaseError('detalle-interno')):
            r = self.sesion(self.usuaria).get('/api/guias')
        self.assertEqual(r.status_code, 503)
        self.assertNotIn(b'detalle-interno', r.content)


class Concurrencia(Base):
    def test_no_sobrescribe_una_edicion_simultanea(self):
        a, b = self.sesion(self.admin), self.sesion(self.admin2)
        g = self.crear(a)
        self.assertEqual(self.accion(a, g, 'editar', contenido(question='¿De A?')).status_code, 200)
        r = self.accion(b, g, 'editar', contenido(question='¿De B?'))
        self.assertEqual((r.status_code, r.json()['code']), (409, 'stale-record'))
        fila = GuiaCuidado.objects.get()
        self.assertEqual((fila.pregunta, fila.version), ('¿De A?', 2))

    def test_publicar_exige_la_version_vista(self):
        a, b = self.sesion(self.admin), self.sesion(self.admin2)
        g = self.crear(a)
        self.accion(a, g, 'editar', contenido(question='¿Cambiada?'))
        self.assertEqual(self.accion(b, g, 'publicar').json()['code'], 'stale-record')
        self.assertEqual(GuiaCuidado.objects.get().estado, 'borrador')

    def test_ediciones_en_paralelo_solo_gana_una(self):
        g = self.crear()
        def editar(actor, texto):
            return lambda: guias.editar(actor, g['id'], 1, pregunta=texto, respuesta='r', orden=1, fuente_nombre='', fuente_url='')
        resultados = en_paralelo(editar(self.admin, '¿A?'), editar(self.admin2, '¿B?'))
        self.assertEqual(sum(isinstance(r, dict) for r in resultados), 1, resultados)
        self.assertEqual(sum(isinstance(r, services.RegistroDesactualizado) for r in resultados), 1, resultados)
        self.assertEqual(GuiaCuidado.objects.get().version, 2)

    def test_reintento_y_doble_pulsacion_no_duplican(self):
        c = self.sesion(self.admin)
        clave = uuid.uuid4()
        uno, dos = (self.post(c, '/api/admin/guias', contenido(), clave) for _ in range(2))
        self.assertEqual(uno.json(), dos.json())
        self.assertEqual(GuiaCuidado.objects.count(), 1)
        self.assertEqual(Auditoria.objects.filter(accion='guide-created').count(), 1)
        self.assertEqual(self.post(c, '/api/admin/guias', contenido(question='¿Otra?'), clave).status_code, 409)

    def test_reintento_de_edicion_y_publicacion(self):
        c = self.sesion(self.admin)
        g = self.crear(c)
        clave = uuid.uuid4()
        ruta, datos = f"/api/admin/guias/{g['id']}/publicar", {'version': 1}
        self.assertEqual(self.post(c, ruta, datos, clave).status_code, 200)
        self.assertEqual(self.post(c, ruta, datos, clave).json()['guide']['version'], 2)
        self.assertEqual(GuiaCuidado.objects.get().version, 2)

    def test_recibo_no_guarda_texto_ni_actores(self):
        from web.models import Idempotencia
        self.crear(answer='Texto que no debe repetirse.')
        recibo = Idempotencia.objects.get().respuesta
        self.assertEqual(set(recibo['guide']), {'id', 'key', 'state', 'version'})

    def test_auditoria_sin_texto_libre(self):
        c = self.sesion(self.admin)
        g = self.crear(c, question='¿Secreto?')
        fila = Auditoria.objects.get(guia_id=g['id'])
        self.assertEqual((fila.actor, fila.accion, fila.resultado), (self.admin, 'guide-created', 'recorded'))
        self.assertNotIn('Secreto', str(Auditoria.objects.filter(pk=fila.pk).values().first()))

    def test_recibo_repite_la_autorizacion(self):
        c = self.sesion(self.admin)
        clave = uuid.uuid4()
        self.post(c, '/api/admin/guias', contenido(), clave)
        self.admin.user_permissions.clear()
        self.assertEqual(self.post(c, '/api/admin/guias', contenido(), clave).status_code, 403)


class Base_de_datos(Base):
    def fila(self):
        g = self.crear()
        return GuiaCuidado.objects.get(pk=g['id'])

    def negado(self, sentencia, parametros=()):
        with self.assertRaises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sentencia, parametros)

    def test_no_se_borra_ni_cambia_identidad(self):
        g = self.fila()
        self.negado('DELETE FROM datos_guiacuidado WHERE id=%s', [g.pk])
        self.negado("UPDATE datos_guiacuidado SET clave='otra',version=version+1 WHERE id=%s", [g.pk])
        self.negado('UPDATE datos_guiacuidado SET creado_por_id=NULL,version=version+1 WHERE id=%s', [g.pk])
        self.negado("UPDATE datos_guiacuidado SET pregunta='sin version' WHERE id=%s", [g.pk])
        self.negado('UPDATE datos_guiacuidado SET version=version+1,actualizado_por_id=NULL WHERE id=%s', [g.pk])

    def test_restricciones(self):
        g = self.fila()
        for campo, valor in (('fuente_url', 'javascript:alert(1)'), ('estado', 'otro'), ('orden', 0), ('orden', 10000), ('pregunta', '   '), ('respuesta', 'x' * 4001)):
            with self.subTest(campo):
                self.negado(f'UPDATE datos_guiacuidado SET {campo}=%s,version=version+1 WHERE id=%s', [valor, g.pk])

    def test_auditoria_de_guia_exige_referencia(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Auditoria.objects.create(actor=self.admin, accion='guide-updated')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Auditoria.objects.create(actor=self.admin, accion='maintenance', guia=self.fila())


class CargaInicial(Base):
    def cargar(self):
        with transaction.atomic(), connection.cursor() as cursor:
            for sentencia, parametros in CARGA.sentencias():
                cursor.execute(sentencia, parametros)

    def test_nueve_preguntas_en_orden_sin_cuentas(self):
        cuentas = get_user_model().objects.count()
        self.cargar()
        self.assertEqual([x['question'] for x in self.publicadas()], PREGUNTAS)
        self.assertEqual(get_user_model().objects.count(), cuentas + 0)
        self.assertFalse(GuiaCuidado.objects.exclude(creado_por=None).exists())
        self.assertFalse(Auditoria.objects.filter(accion__startswith='guide-').exists())
        self.assertTrue(GuiaCuidado.objects.filter(clave='sustrato-perlita', estado='publicada').exists())

    def test_repetir_no_duplica_ni_sobrescribe(self):
        self.cargar()
        c = self.sesion(self.admin)
        por_clave = {g['key']: g for g in self.panel(c).values()}
        editada = self.accion(c, por_clave['riego-revision'], 'editar', contenido(question='¿Riego editado?'))
        self.assertEqual(editada.status_code, 200)
        self.accion(c, por_clave['sin-lecturas'], 'retirar')
        self.cargar()
        self.assertEqual(GuiaCuidado.objects.count(), 9)
        self.assertEqual(GuiaCuidado.objects.get(clave='riego-revision').pregunta, '¿Riego editado?')
        self.assertEqual(GuiaCuidado.objects.get(clave='sin-lecturas').estado, 'retirada')

    def test_identificadores_reproducibles(self):
        self.assertEqual([p[0] for _, p in CARGA.sentencias()], [p[0] for _, p in CARGA.sentencias()])

    def test_aclaraciones_y_limites_del_contenido(self):
        textos = {clave: respuesta for clave, _, _, respuesta, _ in CARGA.GUIAS}
        self.assertIn('declara una acción que ya realizaste físicamente', textos['deposito-recarga'])
        self.assertIn('El flotador detecta nivel bajo', textos['deposito-recarga'])
        self.assertIn('No mide los litros restantes ni confirma que el depósito esté lleno', textos['deposito-recarga'])
        self.assertIn('Sin lecturas válidas no puede deducirse el estado de la planta', textos['sin-lecturas'])
        for clave, _, pregunta, respuesta, (fuente, enlace) in CARGA.GUIAS:
            with self.subTest(clave):
                self.assertNotRegex(respuesta, r'\d+\s*(%|°|ml|L\b|litros|días|semanas\s+exactas)')
                self.assertLessEqual(len(respuesta), guias.MAX_RESPUESTA)
                self.assertEqual(guias._fuente(fuente, enlace), (fuente, enlace))

    def test_el_servicio_valida_igual_que_la_carga(self):
        with self.assertRaises(ValidationError):
            guias._fuente('Sin esquema', 'extension.umd.edu')
