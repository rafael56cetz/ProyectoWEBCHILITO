"""Formato de logs sin datos personales: el texto de una excepción de base puede incluir un correo."""
import logging
import traceback


class FormatoSeguro(logging.Formatter):
    def formatException(self, exc_info):
        tipo, _, pila = exc_info
        lineas = ''.join(traceback.format_tb(pila))
        return f'{lineas}{tipo.__module__}.{tipo.__qualname__}'
