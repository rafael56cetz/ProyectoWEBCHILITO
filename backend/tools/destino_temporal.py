"""Guardián de destino: las herramientas de flujos solo pueden escribir en la base temporal de pruebas.

Se llama después de `django.setup()` y antes de cualquier escritura. Comprueba dos cosas:
1. La base configurada, sin conectar: si no es la temporal, aborta sin abrir conexión.
2. La base efectiva (`current_database()`), con una sola lectura, por si la configuración dice una cosa y la conexión llega a otra.
Solo lee la configuración del proceso; no toca la de la aplicación."""
import sys

TEMPORAL = 'test_chilito_integracion_sinteticos'
OFICIAL = 'chilito_integracion_sinteticos'


def motivo(configurada, efectiva=None):
    """Texto del motivo para abortar, o None si el destino es la base temporal."""
    for nombre in (configurada, efectiva):
        if nombre == OFICIAL:
            return 'apunta a la base oficial'
    if configurada != TEMPORAL:
        return 'la base configurada no es la temporal'
    if efectiva is not None and efectiva != TEMPORAL:
        return 'la base efectiva no es la temporal'
    return None


def exigir():
    from django.db import connection
    configurada = connection.settings_dict['NAME']
    problema = motivo(configurada)
    if problema is None:
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            problema = motivo(configurada, cursor.fetchone()[0])
    if problema:
        sys.exit(f'Abortado antes de escribir: {problema}. Estas pruebas solo usan {TEMPORAL}.')
    print(f'destino comprobado: {TEMPORAL}')
