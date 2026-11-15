"""Validación offline del contrato de modelos, no prueba de PostgreSQL ni ARCO.

No crea personas, filas ni conexiones. Los disparadores y GRANT requieren ensayos
posteriores en PostgreSQL; estas pruebas no los ejecutan ni acreditan su eficacia.
"""
import unittest
import uuid

from django.core.exceptions import ValidationError
from django.db.models import NOT_PROVIDED
from django.db.models.functions import Now
from django.test import SimpleTestCase

from .models import (ConteoNavegacion, DecisionPrivacidad, DocumentoVersion, EventoPrivacidad,
                     FinalidadOpcional, PreferenciaFinalidad, SujetoPrivacidad)


class ContratoPrivacidadOffline(SimpleTestCase):
    databases = set()

    def test_lectura_no_se_confunde_con_finalidad_opcional(self):
        fila = DecisionPrivacidad(acto="lectura_aviso", decision=True)
        fila.clean()
        fila.finalidad_id = uuid.uuid4()
        with self.assertRaises(ValidationError):
            fila.clean()

    def test_terminos_no_admiten_finalidad_opcional(self):
        fila = DecisionPrivacidad(acto="aceptacion_terminos", decision=True)
        fila.clean()
        fila.finalidad_id = uuid.uuid4()
        with self.assertRaises(ValidationError):
            fila.clean()

    def test_consentimiento_exige_finalidad_y_admite_rechazo(self):
        fila = DecisionPrivacidad(acto="consentimiento", decision=False)
        with self.assertRaises(ValidationError):
            fila.clean()
        fila.finalidad_id = uuid.uuid4()
        fila.clean()
        self.assertIs(fila.decision, False)

    def test_acto_desconocido_rechazado(self):
        with self.assertRaises(ValidationError):
            DecisionPrivacidad(acto="aceptar_todo", decision=True).clean()

    def test_decision_no_tiene_aceptacion_por_defecto(self):
        campo = DecisionPrivacidad._meta.get_field("decision")
        self.assertIs(campo.default, NOT_PROVIDED)
        self.assertIs(campo.db_default, NOT_PROVIDED)
        self.assertFalse(campo.null)

    def test_rectificacion_restringe_campos_y_requiere_actor(self):
        for campo in ("first_name", "last_name", "alias"):
            EventoPrivacidad(accion="rectificacion", resultado="completado", actor_id=1, campo=campo).clean()
        for campo in ("password", "is_superuser", "email", ""):
            with self.subTest(campo=campo), self.assertRaises(ValidationError):
                EventoPrivacidad(accion="rectificacion", resultado="completado", actor_id=1, campo=campo).clean()
        with self.assertRaises(ValidationError):
            EventoPrivacidad(accion="rectificacion", resultado="completado", campo="first_name").clean()

    def test_rectificacion_no_mezcla_finalidades_ni_decisiones(self):
        for atributo in ("decision_id", "finalidad_id"):
            fila = EventoPrivacidad(accion="rectificacion", resultado="completado", actor_id=1, campo="first_name")
            setattr(fila, atributo, uuid.uuid4())
            with self.subTest(atributo=atributo), self.assertRaises(ValidationError):
                fila.clean()

    def test_oposicion_requiere_actor_finalidad_y_decision(self):
        datos = dict(accion="oposicion", resultado="completado", actor_id=1,
                     finalidad_id=uuid.uuid4(), decision_id=uuid.uuid4())
        EventoPrivacidad(**datos).clean()
        for atributo in ("actor_id", "finalidad_id", "decision_id"):
            invalido = {**datos, atributo: None}
            with self.subTest(atributo=atributo), self.assertRaises(ValidationError):
                EventoPrivacidad(**invalido).clean()

    def test_evento_decision_admite_visitante_sin_campo_personal(self):
        fila = EventoPrivacidad(accion="decision", resultado="completado", decision_id=uuid.uuid4())
        fila.clean()
        fila.campo = "first_name"
        with self.assertRaises(ValidationError):
            fila.clean()

    def test_resultado_no_admite_texto_libre(self):
        with self.assertRaises(ValidationError):
            EventoPrivacidad(accion="rectificacion", resultado="mi contraseña", actor_id=1, campo="first_name").clean()

    def test_documento_exige_huella_y_referencia(self):
        hash_field = DocumentoVersion._meta.get_field("contenido_sha256")
        for valor in ("", "abc", "G" * 64):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                hash_field.clean(valor, None)
        self.assertEqual(hash_field.clean("a" * 64, None), "a" * 64)
        with self.assertRaises(ValidationError):
            DocumentoVersion._meta.get_field("contenido_ref").clean("", None)

    def test_fechas_tienen_default_de_servidor_y_no_son_editables(self):
        for modelo, nombre in ((DocumentoVersion, "registrado_en"), (SujetoPrivacidad, "creado_en"),
                               (FinalidadOpcional, "creada_en"), (DecisionPrivacidad, "registrada_en"),
                               (PreferenciaFinalidad, "actualizada_en"), (EventoPrivacidad, "creado_en")):
            with self.subTest(modelo=modelo.__name__):
                campo = modelo._meta.get_field(nombre)
                self.assertIsInstance(campo.db_default, Now)
                self.assertTrue(callable(campo.default))
                self.assertFalse(campo.editable)

    def test_sujeto_anonimo_no_utiliza_sesion_y_ambito_es_explicito(self):
        a, b = SujetoPrivacidad(), SujetoPrivacidad()
        self.assertIsInstance(a.pk, uuid.UUID)
        self.assertNotEqual(a.pk, b.pk)
        self.assertIsNone(a.usuario_id)
        self.assertEqual(a.ambito, "cuenta")
        self.assertFalse(SujetoPrivacidad._meta.get_field("usuario").unique)
        constraint = next(c for c in SujetoPrivacidad._meta.constraints if c.name == "priv_sujeto_cuenta_unica")
        self.assertEqual(constraint.fields, ("usuario",))
        self.assertEqual(constraint.condition.children, [("ambito", "cuenta")])

    def test_politica_cookies_es_tipo_documental_separado(self):
        campo = DocumentoVersion._meta.get_field("tipo")
        self.assertEqual(campo.clean("politica_cookies", None), "politica_cookies")

    def test_cookies_exigen_finalidad_y_politica_versionada(self):
        datos = dict(acto="cookies", decision=True,
                     finalidad_id=uuid.uuid4(), politica_cookies_id=uuid.uuid4())
        DecisionPrivacidad(**datos).clean()
        for atributo in ("finalidad_id", "politica_cookies_id"):
            with self.subTest(atributo=atributo), self.assertRaises(ValidationError):
                DecisionPrivacidad(**{**datos, atributo: None}).clean()

    def test_rechazar_cookies_no_se_convierte_en_aceptacion(self):
        fila = DecisionPrivacidad(acto="cookies", decision=False,
                                  finalidad_id=uuid.uuid4(), politica_cookies_id=uuid.uuid4())
        fila.clean()
        self.assertIs(fila.decision, False)

    def test_cookies_no_reemplazan_la_referencia_al_aviso(self):
        aviso, politica = uuid.uuid4(), uuid.uuid4()
        fila = DecisionPrivacidad(acto="cookies", decision=True, documento_id=aviso,
                                  politica_cookies_id=politica, finalidad_id=uuid.uuid4())
        fila.clean()
        self.assertEqual(fila.documento_id, aviso)
        self.assertEqual(fila.politica_cookies_id, politica)
        self.assertFalse(DecisionPrivacidad._meta.get_field("documento").null)

    def test_otros_actos_no_admiten_politica_cookies(self):
        for acto in ("lectura_aviso", "aceptacion_terminos", "consentimiento"):
            fila = DecisionPrivacidad(acto=acto, decision=True,
                                      politica_cookies_id=uuid.uuid4())
            if acto == "consentimiento":
                fila.finalidad_id = uuid.uuid4()
            with self.subTest(acto=acto), self.assertRaises(ValidationError):
                fila.clean()


class EstadisticasYAmbitoOffline(SimpleTestCase):
    def test_dos_navegadores_de_una_cuenta_no_comparten_sujeto(self):
        uno = SujetoPrivacidad(ambito="navegador", usuario_id=1)
        otro = SujetoPrivacidad(ambito="navegador", usuario_id=1)
        self.assertNotEqual(uno.pk, otro.pk)
        self.assertEqual(uno.usuario_id, otro.usuario_id)

    def test_conteo_no_admite_secciones_libres_con_datos_personales(self):
        campo = ConteoNavegacion._meta.get_field("seccion")
        for valor in ("/cuenta/123", "correo@example.test", "admin", "inicio?token=x"):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                campo.clean(valor, None)
        self.assertEqual(campo.clean("huerto", None), "huerto")

    def test_conteo_no_persiste_identificadores_personales(self):
        self.assertEqual({f.name for f in ConteoNavegacion._meta.fields},
                         {"id", "dia", "seccion", "visitas"})

    def test_conteo_no_admite_valores_negativos(self):
        with self.assertRaises(ValidationError):
            ConteoNavegacion._meta.get_field("visitas").clean(-1, None)

    def test_politica_no_confunde_sesion_con_cookie_opcional(self):
        from privacidad import politicas as p
        self.assertEqual(p.VERIFICACION_CORREO_SEGUNDOS, 600)
        self.assertEqual(p.RECUPERACION_CONTRASENA_SEGUNDOS, 600)
        self.assertEqual(p.SESION_ABSOLUTA_SEGUNDOS, 28800)
        self.assertEqual(p.SESION_INACTIVA_USUARIO_SEGUNDOS, 1800)
        self.assertEqual(p.SESION_INACTIVA_ADMIN_SEGUNDOS, 900)
        self.assertEqual(p.PREFERENCIA_COOKIES_SEGUNDOS, 15552000)
        self.assertEqual(p.IDENTIFICADOR_ESTADISTICAS_SEGUNDOS, 1800)

    def test_acceso_admite_consulta_propia_sin_copia_del_perfil(self):
        fila = EventoPrivacidad(accion="acceso", resultado="completado", actor_id=1)
        fila.clean()
        self.assertEqual(fila.campo, "")
        self.assertIsNone(fila.decision_id)
        self.assertIsNone(fila.finalidad_id)

    def test_acceso_requiere_actor(self):
        with self.assertRaises(ValidationError):
            EventoPrivacidad(accion="acceso", resultado="completado").clean()

    def test_acceso_no_admite_campos_decisiones_ni_finalidades(self):
        for atributo, valor in (("campo", "first_name"), ("decision_id", uuid.uuid4()),
                                ("finalidad_id", uuid.uuid4())):
            fila = EventoPrivacidad(accion="acceso", resultado="completado", actor_id=1)
            setattr(fila, atributo, valor)
            with self.subTest(atributo=atributo), self.assertRaises(ValidationError):
                fila.clean()


if __name__ == "__main__":
    unittest.main()


class TextoLegalEnVivo(SimpleTestCase):
    """El texto se lee del archivo en cada petición; sin huella coincidente es borrador sin registrar."""
    databases = set()

    def _leer(self, contenido, huella=None):
        import hashlib
        import tempfile
        from pathlib import Path
        from unittest import mock
        from . import services
        with tempfile.TemporaryDirectory() as carpeta:
            Path(carpeta, 'terminos.html').write_bytes(contenido)
            registrado = DocumentoVersion(tipo='terminos', version='1.0', contenido_ref='x',
                                          contenido_sha256=huella or hashlib.sha256(b'otro').hexdigest())
            with mock.patch.object(services, 'CARPETA_HTML', Path(carpeta)), \
                 mock.patch.object(services, 'documento_vigente', return_value=registrado):
                return services.texto_vigente('terminos')

    def test_cambio_guardado_se_sirve_como_borrador(self):
        r = self._leer('<h3>Uso</h3><p>Texto nuevo</p>'.encode())
        self.assertEqual(r['text'], '## Uso\n\nTexto nuevo')
        self.assertFalse(r['registered'])
        self.assertTrue(r['draft'])
        self.assertIsNone(r['version'])

    def test_texto_igual_a_la_huella_es_version_registrada(self):
        import hashlib
        r = self._leer(b'Final', hashlib.sha256(b'Final').hexdigest())
        self.assertEqual((r['version'], r['registered'], r['draft']), ('1.0', True, False))

    def test_tipo_desconocido_no_se_sirve(self):
        from . import services
        self.assertIsNone(services.texto_vigente('../settings'))


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

    def test_html_se_lee_en_cada_peticion_y_usa_huella_de_la_fuente(self):
        import hashlib
        import tempfile
        from pathlib import Path
        from unittest import mock
        from . import services
        original = b'<p>Texto registrado</p>'
        registrado = DocumentoVersion(tipo='terminos', version='1.0', contenido_ref='frontend/legales/terminos.html',
                                      contenido_sha256=hashlib.sha256(original).hexdigest())
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta, 'terminos.html')
            ruta.write_bytes(original)
            with mock.patch.object(services, 'CARPETA_HTML', Path(carpeta)), \
                 mock.patch.object(services, 'documento_vigente', return_value=registrado):
                primero = services.texto_vigente('terminos')
                self.assertEqual((primero['html'], primero['text']), ('<p>Texto registrado</p>', 'Texto registrado'))
                self.assertEqual((primero['version'], primero['registered'], primero['draft']), ('1.0', True, False))
                ruta.write_text('<h3>Actualizado</h3><p>Texto nuevo</p>', encoding='utf-8')
                segundo = services.texto_vigente('terminos')
                self.assertEqual(segundo['text'], '## Actualizado\n\nTexto nuevo')
                self.assertEqual((segundo['version'], segundo['registered'], segundo['draft']), (None, False, True))

    def test_no_consulta_catalogo_para_nombres_fuera_de_la_lista(self):
        from unittest import mock
        from . import services
        with mock.patch.object(services, 'documento_vigente') as catalogo:
            for tipo in ('../settings', 'terminos.html', '/etc/passwd', 'aviso_privacidad'):
                self.assertIsNone(services.texto_vigente(tipo))
            catalogo.assert_not_called()

    def test_endpoint_conserva_campos_del_contrato(self):
        import json
        from unittest import mock
        from django.test import RequestFactory
        from . import api, services
        documento = {'version': None, 'registered': False, 'draft': True, 'text': 'Texto', 'html': '<p>Texto</p>'}
        with mock.patch.object(services, 'texto_vigente', return_value=documento):
            respuesta = api.document(RequestFactory().get('/api/privacidad/documentos/terminos'), 'terminos')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(json.loads(respuesta.content), {'status': 'ready', **documento})
