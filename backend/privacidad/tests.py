"""Privacidad sobre PostgreSQL: textos legales, perfil, auditoría sin valores y estadísticas con consentimiento."""
import csv
import hashlib
import io
import json
import uuid
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, SimpleTestCase, TestCase

from datos.models import Auditoria, Notificacion
from huerto.models import Huerto
from tests import aceptar_vigentes, cuenta, publicar_textos

from . import consentimientos, politicas, services
from .models import ConteoNavegacion, Decision, DocumentoLegal, Finalidad, Sujeto


class TextoLegalVigente(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def test_sirve_la_version_vigente_ya_saneada(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT chilito_publicar_documento_legal('terminos','1.1','Términos',"
                           "'<h2>Uso</h2><p onclick=\"x()\">Texto</p><script>alert(1)</script>')")
        documento = services.texto_vigente('terminos')
        self.assertEqual(documento['version'], '1.1')
        self.assertEqual(documento['html'], '<h3>Uso</h3><p>Texto</p>')
        self.assertTrue(documento['registered'] and not documento['draft'])

    def test_el_endpoint_conserva_los_campos_del_contrato(self):
        cuerpo = Client().get('/api/privacidad/documentos/privacidad').json()
        self.assertEqual(set(cuerpo), {'status', 'version', 'registered', 'text', 'html', 'draft'})
        self.assertEqual(cuerpo['version'], '1.0')

    def test_tipo_desconocido_o_sin_publicar_responde_404(self):
        for tipo in ('../settings', 'terminos.html', 'aviso_privacidad'):
            self.assertEqual(Client().get(f'/api/privacidad/documentos/{tipo}').status_code, 404, tipo)
        with patch.object(services, 'documento_vigente', return_value=None):
            self.assertEqual(Client().get('/api/privacidad/documentos/terminos').status_code, 404)

    def test_no_lee_archivos_del_frontend(self):
        self.assertFalse(hasattr(services, 'CARPETA_HTML'))


class Registro(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def test_cuenta_y_aceptaciones_con_la_version_vigente(self):
        usuario = cuenta('registro@example.test')
        actos = {d.acto: d for d in Decision.objects.filter(sujeto__usuario=usuario, sujeto__ambito='cuenta')}
        self.assertEqual(set(actos), {'aceptacion_terminos', 'lectura_aviso'})
        self.assertEqual(actos['aceptacion_terminos'].documento.tipo, 'terminos')
        self.assertEqual(actos['lectura_aviso'].documento.tipo, 'aviso_privacidad')

    def test_sin_textos_publicados_no_hay_registro(self):
        with patch.object(services, 'documento_vigente', return_value=None), self.assertRaises(ValidationError), transaction.atomic():
            cuenta('sin-textos@example.test')

    def test_la_base_rechaza_una_cuenta_sin_aceptaciones(self):
        from django.contrib.auth import get_user_model
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user('sin-aceptar@example.test', 'una frase suficientemente larga 12')
            with connection.cursor() as cursor:
                cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')

    def test_navegador_resumido_sin_user_agent_completo(self):
        casos = {
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0': 'Edge 130 · Windows',
            'Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0': 'Firefox 131 · Linux',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1': 'Safari 17 · iOS',
            '': 'Otro · Otro',
        }
        for agente, esperado in casos.items():
            with self.subTest(esperado=esperado):
                self.assertEqual(services.navegador_resumido(RequestFactory().get('/', HTTP_USER_AGENT=agente)), esperado)

    def test_ip_recortada(self):
        for ip, esperado in {'189.203.45.77': '189.203.45.0', '2001:db8:abcd:12::1': '2001:db8:abcd::', 'no-es-ip': ''}.items():
            with self.subTest(ip=ip):
                self.assertEqual(services.ip_recortada(RequestFactory().get('/', REMOTE_ADDR=ip)), esperado)


class PerfilYMisDatos(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        self.usuario = cuenta('perfil@example.test')

    def test_rectificar_audita_el_campo_y_nunca_el_valor(self):
        services.rectificar_perfil(self.usuario, {'firstName': 'Ana', 'alias': 'Mi huerto'})
        self.usuario.refresh_from_db()
        self.assertEqual((self.usuario.first_name, self.usuario.alias), ('Ana', 'Mi huerto'))
        registros = Auditoria.objects.filter(accion='rectificar_perfil', actor=self.usuario)
        self.assertEqual(sorted(r.detalle['campo'] for r in registros), ['alias', 'first_name'])
        self.assertNotIn('Ana', json.dumps([r.detalle for r in registros]))

    def test_sin_cambios_no_audita(self):
        services.rectificar_perfil(self.usuario, {'alias': ''})
        self.assertFalse(Auditoria.objects.filter(accion='rectificar_perfil').exists())

    def test_campos_no_permitidos_o_invalidos(self):
        for datos in ({'alias': 'x' * 65}, {'firstName': 3}, {'lastName': 'a\nb'}):
            with self.subTest(datos=datos), self.assertRaises(ValidationError):
                services.rectificar_perfil(self.usuario, datos)

    def test_bienvenida_se_cierra_una_vez_aun_sin_datos(self):
        services.atender_bienvenida(self.usuario, {})
        primera = self.usuario.__class__.objects.get(pk=self.usuario.pk).bienvenida_atendida_en
        self.assertIsNotNone(primera)
        services.atender_bienvenida(self.usuario, {})
        self.assertEqual(self.usuario.__class__.objects.get(pk=self.usuario.pk).bienvenida_atendida_en, primera)

    def test_mis_datos_audita_la_consulta_y_lista_solo_huertos_activos_propios(self):
        otra = cuenta('otra-persona@example.test')
        archivado = Huerto.objects.create(propietario=self.usuario, nombre='Archivado')
        Huerto.objects.filter(pk=archivado.pk).update(estado='archivado', archivado_en=archivado.creado_en)
        Huerto.objects.create(propietario=self.usuario, nombre='Activo')
        Huerto.objects.create(propietario=otra, nombre='Ajeno')
        datos = services.consultar_mis_datos(self.usuario)
        self.assertEqual(datos['gardens'], ['Activo'])
        self.assertEqual(Auditoria.objects.filter(accion='consultar_mis_datos', actor=self.usuario).count(), 1)


class Estadisticas(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def decidir(self, acepta):
        pedido = RequestFactory().get('/')
        from django.contrib.auth.models import AnonymousUser
        pedido.user = AnonymousUser()
        return services.decidir_cookies(pedido, None, acepta)

    def test_sin_consentimiento_no_cuenta(self):
        self.assertFalse(services.contar_seccion(None, self.decidir(False), 'id-1', 'inicio'))
        self.assertFalse(ConteoNavegacion.objects.exists())

    def test_con_consentimiento_cuenta_una_vez_por_identificador_y_seccion(self):
        valor = self.decidir(True)
        self.assertTrue(services.contar_seccion(None, valor, 'id-2', 'inicio'))
        self.assertFalse(services.contar_seccion(None, valor, 'id-2', 'inicio'))
        self.assertTrue(services.contar_seccion(None, valor, 'id-3', 'inicio'))
        self.assertEqual(ConteoNavegacion.objects.get(seccion='inicio').visitas, 2)

    def test_secciones_libres_se_rechazan(self):
        with self.assertRaises(ValidationError):
            services.contar_seccion(None, self.decidir(True), 'id-4', 'mi-correo@example.test')


class DocumentosHTML(SimpleTestCase):
    """Edición y representación del documento sin usar la base de datos."""
    databases = set()

    def test_solo_conserva_formato_y_enlaces_permitidos(self):
        from .documentos_html import sanear_html
        html, texto = sanear_html('<h2 id="x">Uso</h2><p onclick="alert(1)" style="color:red">'
                                 'Texto <strong>claro</strong> y <em>editable</em>. '
                                 '<a href="https://example.test/ayuda" target="_blank">Ayuda</a></p>')
        self.assertEqual(html, '<h3>Uso</h3><p>Texto <strong>claro</strong> y <em>editable</em>. '
                              '<a href="https://example.test/ayuda">Ayuda</a></p>')
        self.assertEqual(texto, '## Uso\n\nTexto claro y editable. Ayuda')

    def test_elimina_contenido_activo_y_enlaces_peligrosos(self):
        from .documentos_html import sanear_html
        html, texto = sanear_html('<script>alert(1)</script><style>body{display:none}</style>'
                                 '<svg><a href="javascript:alert(1)">Oculto</a></svg>'
                                 '<p><img src="x" onerror="alert(1)">Seguro '
                                 '<a href="jav&#97;script:alert(1)" onclick="alert(1)">enlace</a></p>')
        self.assertEqual(html, '<p>Seguro <a>enlace</a></p>')
        self.assertEqual(texto, 'Seguro enlace')

    def test_validacion_de_enlaces_no_admite_atajos_de_protocolo(self):
        from .documentos_html import sanear_html
        for enlace in ('data:text/html,x', '//example.test/x', '/\\example.test', 'java\nscript:alert(1)', 'https://['):
            with self.subTest(enlace=enlace):
                html, _ = sanear_html(f'<a href="{enlace}">Texto</a>')
                self.assertEqual(html, '<a>Texto</a>')
        for enlace in ('#privacidad', '/ayuda', 'https://example.test', 'http://example.test', 'mailto:soporte@example.test'):
            with self.subTest(enlace=enlace):
                html, _ = sanear_html(f'<a href="{enlace}">Texto</a>')
                self.assertIn('href=', html)

    def test_comentarios_no_se_convierten_en_texto_visible(self):
        from .documentos_html import sanear_html
        html, texto = sanear_html('<!-- Instrucciones de edición: <p>Ejemplo</p> -->\n')
        self.assertFalse(html.strip())
        self.assertEqual(texto, '')


class EliminarCuenta(TestCase):
    CLAVE = 'Clave-de-prueba-123'

    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        from django.core.cache import cache
        import uuid
        cache.clear()
        self.usuaria = cuenta('eliminar-usuaria@example.test', password=self.CLAVE)
        self.client = Client(HTTP_HOST='127.0.0.1')
        self.client.force_login(self.usuaria, backend='django.contrib.auth.backends.ModelBackend')
        self.nueva_clave = lambda: {'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}

    def post(self, ruta, datos=None):
        return self.client.post(ruta, json.dumps(datos or {}), content_type='application/json', **self.nueva_clave())

    def test_documentos_que_acepto(self):
        datos = self.client.get('/api/cuenta/aceptaciones').json()
        self.assertEqual(sorted(item['type'] for item in datos['items']), ['aviso_privacidad', 'terminos'])
        self.assertTrue(all(item['version'] == '1.0' and item['at'] for item in datos['items']))
        otra = Client(HTTP_HOST='127.0.0.1')
        otra.force_login(cuenta('eliminar-otra@example.test'), backend='django.contrib.auth.backends.ModelBackend')
        self.assertEqual(len(otra.get('/api/cuenta/aceptaciones').json()['items']), 2)

    def test_exige_la_contrasena(self):
        for clave in ('otra-clave', '', None, 5):
            with self.subTest(clave=clave):
                self.assertEqual(self.post('/api/cuenta/eliminar', {'password': clave}).status_code, 400)
        self.usuaria.refresh_from_db()
        self.assertIsNone(self.usuaria.anonimizacion_solicitada_en)
        self.assertEqual(self.post('/api/cuenta/eliminar', {}).status_code, 400)

    def test_solicitar_y_cancelar(self):
        respuesta = self.post('/api/cuenta/eliminar', {'password': self.CLAVE})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        cuerpo = respuesta.json()
        self.assertTrue(cuerpo['deletionRequestedAt'] and cuerpo['deletionDate'])
        perfil = self.client.get('/api/cuenta').json()
        self.assertEqual((perfil['deletionRequestedAt'], perfil['deletionDate']), (cuerpo['deletionRequestedAt'], cuerpo['deletionDate']))
        self.assertEqual(self.post('/api/cuenta/eliminar/cancelar').status_code, 200)
        despues = self.client.get('/api/cuenta').json()
        self.assertEqual((despues['deletionRequestedAt'], despues['deletionDate']), (None, None))
        self.assertEqual(self.post('/api/cuenta/eliminar/cancelar').status_code, 400)
        acciones = list(Auditoria.objects.filter(actor=self.usuaria).values_list('accion', flat=True))
        self.assertIn('solicitar_eliminacion', acciones)
        self.assertIn('cancelar_eliminacion', acciones)
        self.assertFalse(Auditoria.objects.filter(detalle__icontains=self.CLAVE).exists())

    def test_cuota_de_intentos(self):
        estados = [self.post('/api/cuenta/eliminar', {'password': 'mala-%d' % n}).status_code for n in range(7)]
        self.assertEqual(estados[:5], [400] * 5)
        self.assertEqual(estados[5:], [429, 429])


class AdminBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def setUp(self):
        cache.clear()

    def cliente(self, usuario):
        cliente = Client(HTTP_HOST='127.0.0.1')
        cliente.force_login(usuario, backend='django.contrib.auth.backends.ModelBackend')
        return cliente

    def post(self, cliente, ruta, datos=None):
        return cliente.post(ruta, json.dumps(datos or {}), content_type='application/json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))


class TextosLegales(AdminBase):
    def setUp(self):
        super().setUp()
        self.admin = cuenta('legales-admin@example.test', 'gestionar_legales')
        self.usuaria = cuenta('legales-usuaria@example.test')
        self.sesion = self.cliente(self.admin)

    def borrador(self, **cambios):
        datos = {'type': 'terminos', 'version': '1.1', 'title': 'Términos y condiciones', 'content': '<h2>Uso</h2><p>Texto nuevo.</p>', **cambios}
        return self.post(self.sesion, '/api/admin/legales', datos)

    def publicar_en_pantalla(self):
        # La base exige las aceptaciones vigentes de toda cuenta al cerrar la transacción de la prueba.
        for usuario in (self.admin, self.usuaria):
            self.addCleanup(aceptar_vigentes, usuario)

    def test_por_tipo_muestra_vigente_borradores_e_historial(self):
        datos = self.sesion.get('/api/admin/legales?tipo=terminos').json()
        self.assertEqual((datos['current']['version'], datos['drafts'], [d['version'] for d in datos['history']]), ('1.0', [], ['1.0']))
        self.borrador()
        datos = self.sesion.get('/api/admin/legales?tipo=terminos').json()
        self.assertEqual([d['version'] for d in datos['drafts']], ['1.1'])
        for consulta in ('?tipo=otro', '', '?tipo=terminos&x=1'):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.sesion.get(f'/api/admin/legales{consulta}').status_code, 400)

    def test_crear_editar_y_eliminar_borrador(self):
        creado = self.borrador().json()['document']
        self.assertEqual((creado['state'], creado['sha256']), ('borrador', hashlib.sha256(creado['content'].encode()).hexdigest()))
        editado = self.post(self.sesion, f"/api/admin/legales/{creado['id']}/editar",
                            {'expectedAt': creado['updatedAt'], 'version': '1.2', 'title': 'Nuevo título', 'content': '<p>Otro texto</p>'})
        self.assertEqual(editado.status_code, 200, editado.content)
        nuevo = editado.json()['document']
        self.assertEqual((nuevo['version'], nuevo['title'], nuevo['html']), ('1.2', 'Nuevo título', '<p>Otro texto</p>'))
        self.assertEqual(nuevo['sha256'], hashlib.sha256(b'<p>Otro texto</p>').hexdigest())
        obsoleta = self.post(self.sesion, f"/api/admin/legales/{creado['id']}/editar",
                             {'expectedAt': '2000-01-01T00:00:00+00:00', 'version': '1.3', 'title': 'x', 'content': '<p>y</p>'})
        self.assertEqual((obsoleta.status_code, obsoleta.json()['code']), (409, 'stale-record'))
        self.assertEqual(self.post(self.sesion, f"/api/admin/legales/{creado['id']}/eliminar", {'expectedAt': nuevo['updatedAt']}).status_code, 200)
        self.assertFalse(DocumentoLegal.objects.filter(pk=creado['id']).exists())
        acciones = set(Auditoria.objects.filter(actor=self.admin).values_list('accion', flat=True))
        self.assertTrue({'crear_borrador_legal', 'editar_borrador_legal', 'eliminar_borrador_legal'} <= acciones)

    def test_publicar_avisa_a_las_cuentas_y_exige_aceptar(self):
        self.publicar_en_pantalla()
        borrador = self.borrador().json()['document']
        publicada = self.post(self.sesion, f"/api/admin/legales/{borrador['id']}/publicar", {'expectedAt': borrador['updatedAt']})
        self.assertEqual(publicada.status_code, 200, publicada.content)
        self.assertEqual(publicada.json()['document']['state'], 'publicada')
        self.assertEqual(publicada.json()['notified'], 2)
        for correo in ('legales-admin@example.test', 'legales-usuaria@example.test'):
            aviso = Notificacion.objects.get(destinatario__email=correo, origen='legal')
            self.assertIn('1.1', aviso.titulo)
        pendientes = self.cliente(self.usuaria).get('/api/cuenta').json()['pendingLegal']
        self.assertEqual([(p['type'], p['version']) for p in pendientes], [('terminos', '1.1')])
        self.assertTrue(Auditoria.objects.filter(accion='publicar_legal').exists())

    def test_version_menor_o_igual_se_rechaza(self):
        antes = self.borrador(version='0.9').json()['document']
        rechazo = self.post(self.sesion, f"/api/admin/legales/{antes['id']}/publicar", {'expectedAt': antes['updatedAt']})
        self.assertEqual((rechazo.status_code, rechazo.json()['code']), (409, 'version-no-mayor'))
        self.assertEqual(DocumentoLegal.objects.get(pk=antes['id']).estado, 'borrador')
        repetida = self.borrador(version='1.0')
        self.assertEqual((repetida.status_code, repetida.json()['code']), (409, 'version-existente'))

    def test_una_version_publicada_no_se_edita_ni_se_borra(self):
        vigente = DocumentoLegal.objects.get(tipo='terminos', version='1.0')
        esperado = vigente.actualizado_en.isoformat()
        edicion = self.post(self.sesion, f'/api/admin/legales/{vigente.pk}/editar', {'expectedAt': esperado, 'version': '1.5', 'title': 'x', 'content': '<p>y</p>'})
        borrado = self.post(self.sesion, f'/api/admin/legales/{vigente.pk}/eliminar', {'expectedAt': esperado})
        self.assertEqual([(r.status_code, r.json()['code']) for r in (edicion, borrado)], [(409, 'documento-publicado')] * 2)

    def test_vista_previa_y_detalle_traen_html_saneado_del_servidor(self):
        sucio = '<h2>Uso</h2><p onclick="x()">Texto</p><script>alert(1)</script><a href="javascript:alert(1)">malo</a><a href="https://ejemplo.mx">bueno</a>'
        vista = self.post(self.sesion, '/api/admin/legales/vista-previa', {'content': sucio}).json()['html']
        for peligro in ('<script', 'onclick', 'javascript:'):
            self.assertNotIn(peligro, vista)
        self.assertIn('<h3>Uso</h3>', vista)
        self.assertIn('href="https://ejemplo.mx"', vista)
        creado = self.borrador(content=sucio).json()['document']
        self.assertEqual(self.sesion.get(f"/api/admin/legales/{creado['id']}").json()['document']['html'], vista)
        self.assertEqual(self.sesion.get(f'/api/admin/legales/{uuid.uuid4()}').status_code, 404)

    def test_validacion(self):
        for cambios in ({'type': 'otro'}, {'version': 'abc'}, {'version': '1'}, {'version': '1.2.3.4'}, {'title': ' '}, {'title': 'x' * 121}, {'content': ' '},
                        {'content': 'x' * 28001}, {'content': 'con\x00nulo'}, {'content': 5}):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.borrador(**cambios).status_code, 400)
        self.assertEqual(DocumentoLegal.objects.filter(estado='borrador').count(), 0)


class BitacoraDeConsentimientos(AdminBase):
    def setUp(self):
        super().setUp()
        self.admin = cuenta('consent-admin@example.test', 'ver_consentimientos')
        self.usuaria = cuenta('consent-usuaria@example.test')
        self.sesion = self.cliente(self.admin)

    def navegador(self, acepta, agente='Mozilla/5.0 (Linux; Android 14) Chrome/130.0 Mobile Safari/537.36'):
        peticion = RequestFactory().get('/', HTTP_USER_AGENT=agente, REMOTE_ADDR='189.203.45.77')
        peticion.user = AnonymousUser()
        return services.decidir_cookies(peticion, None, acepta)

    def test_bitacora_con_filtros_y_paginacion(self):
        lista = self.sesion.get('/api/admin/consentimientos?cuenta=consent-usuaria').json()
        self.assertEqual({(f['what'], f['version'], f['decision']) for f in lista['items']}, {('Términos y condiciones', '1.0', 'Aceptó'), ('Aviso de privacidad', '1.0', 'Aceptó')})
        total = lambda consulta: self.sesion.get(f'/api/admin/consentimientos{consulta}').json()['total']
        self.assertEqual((total('?cuenta=consent-usuaria&documento=terminos'), total('?cuenta=consent-usuaria&decision=rechazo'), total('?version=9.9')), (1, 0, 0))
        self.navegador(False)
        anonimo = self.sesion.get('/api/admin/consentimientos?documento=cookies&decision=rechazo').json()['items']
        self.assertEqual([(f['account'], f['what'], f['purpose'], f['ip']) for f in anonimo], [('Visitante anónimo', 'Cookies', politicas.FINALIDAD_ESTADISTICAS, '189.203.45.0')])
        self.assertEqual(self.sesion.get('/api/admin/consentimientos?page=2').json()['items'], [])
        self.assertEqual(self.sesion.get('/api/admin/consentimientos').json()['exportLimit'], consentimientos.MAXIMO_FILAS_CSV)
        for consulta in ('?documento=otro', '?decision=quiza', '?version=x', '?desde=ayer', '?desde=2026-02-01&hasta=2026-01-01', '?x=1', '?page=0', '?cuenta=' + 'a' * 61):
            with self.subTest(consulta=consulta):
                self.assertEqual(self.sesion.get(f'/api/admin/consentimientos{consulta}').status_code, 400)

    def test_resumen(self):
        resumen = self.sesion.get('/api/admin/consentimientos/resumen').json()
        self.assertEqual((resumen['terms'], resumen['privacy']), ({'version': '1.0', 'accepted': 2, 'accounts': 2}, {'version': '1.0', 'accepted': 2, 'accounts': 2}))
        self.assertEqual(resumen['statistics'], {'browsers': 0, 'accepted': 0, 'percent': None})
        self.navegador(True)
        self.navegador(False, agente='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Safari/604.1')
        self.assertEqual(self.sesion.get('/api/admin/consentimientos/resumen').json()['statistics'], {'browsers': 2, 'accepted': 1, 'percent': 50.0})

    def test_exportar_csv_sin_inyeccion_de_formulas_y_con_auditoria(self):
        sujeto = Sujeto.objects.create(ambito='navegador')
        Decision.objects.create(sujeto=sujeto, acto='cookies', decision=True, documento=services.documento_vigente('politica_cookies'),
                                finalidad=Finalidad.objects.get(codigo=politicas.FINALIDAD_ESTADISTICAS), ip_recortada='201.141.12.0', navegador='=HYPERLINK("http://x")')
        respuesta = self.sesion.get('/api/admin/consentimientos/exportar?documento=cookies')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta['Content-Type'].startswith('text/csv'))
        self.assertIn('attachment', respuesta['Content-Disposition'])
        texto = respuesta.content.decode('utf-8')
        self.assertTrue(texto.startswith('\ufeff'))
        filas = list(csv.reader(io.StringIO(texto.lstrip('\ufeff'))))
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0][:3], ['Fecha y hora (Mérida)', 'Cuenta', 'Ámbito'])
        self.assertEqual(filas[1][-1], "'=HYPERLINK(\"http://x\")")
        self.assertFalse(any(celda.startswith(consentimientos.PELIGROSAS) for fila in filas[1:] for celda in fila))
        auditoria = Auditoria.objects.get(accion='exportar_consentimientos')
        self.assertEqual((auditoria.actor_id, auditoria.detalle), (self.admin.pk, {'filas': 1}))

    def test_celda_neutraliza_cada_caracter_peligroso(self):
        for peligro in ('=1+1', '+1', '-1', '@suma', '\tTAB', '\rCR'):
            self.assertEqual(consentimientos._celda(peligro), "'" + peligro)
        self.assertEqual(consentimientos._celda('Chrome 130'), 'Chrome 130')
        self.assertEqual(consentimientos._celda(None), '')

    def test_exportacion_demasiado_grande(self):
        with patch.object(consentimientos, 'MAXIMO_FILAS_CSV', 1):
            rechazo = self.sesion.get('/api/admin/consentimientos/exportar')
        self.assertEqual((rechazo.status_code, rechazo.json()['code']), (409, 'exportacion-grande'))
        self.assertFalse(Auditoria.objects.filter(accion='exportar_consentimientos').exists())

    def test_exportar_exige_ver_consentimientos(self):
        sin_capacidad = self.cliente(cuenta('consent-otra@example.test', 'gestionar_legales'))
        self.assertEqual(sin_capacidad.get('/api/admin/consentimientos/exportar').status_code, 403)
        self.assertFalse(Auditoria.objects.filter(accion='exportar_consentimientos').exists())
