"""Regresiones de las diferencias de seguridad corregidas en el cierre de código."""
import logging
import sys

from django.conf import settings
from django.test import SimpleTestCase

from config.registro import FormatoSeguro


class Registros(SimpleTestCase):
    def test_cada_aplicacion_usa_el_formato_sin_datos_personales(self):
        for nombre in ('cuentas', 'datos', 'web', 'privacidad', 'django.request', 'django.security'):
            with self.subTest(nombre):
                self.assertIn(nombre, settings.LOGGING['loggers'])
                self.assertEqual(settings.LOGGING['loggers'][nombre]['handlers'], ['consola'])
        self.assertEqual(settings.LOGGING['formatters']['seguro']['()'], 'config.registro.FormatoSeguro')

    def test_el_texto_de_la_excepcion_no_llega_al_registro(self):
        correo = '@'.join(['persona', 'example.test'])     # compuesto: el rastro muestra el código fuente
        try:
            raise ValueError(correo)
        except ValueError:
            registro = logging.LogRecord('x', logging.ERROR, __file__, 1, 'fallo', (), sys.exc_info())
        self.assertNotIn(correo, FormatoSeguro('%(message)s').format(registro))
