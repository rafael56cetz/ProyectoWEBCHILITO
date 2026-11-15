"""Privacidad sobre PostgreSQL: textos legales, perfil, auditoría sin valores y estadísticas con consentimiento."""
import json
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, SimpleTestCase, TestCase

from datos.models import Auditoria
from huerto.models import Huerto
from tests import cuenta, publicar_textos

from . import services
from .models import ConteoNavegacion, Decision, DocumentoLegal


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
