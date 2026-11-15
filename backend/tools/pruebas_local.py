"""Pruebas contra PostgreSQL local, sin mostrar valores de los archivos de entorno.

suite   Todas las pruebas, en una base temporal que se borra. Usa el dueño de la base (CHILITO_TEST_DB_*).
flujos  Flujos HTTP con el rol limitado, solo en una base temporal que se borra. Usa ambos usuarios.

Todo sale del único .env del proyecto.
"""
import os
import subprocess
import sys
from pathlib import Path

from entorno_local import RAIZ, leer

BACKEND = RAIZ / 'backend'
TEMPORAL = 'test_chilito_integracion_sinteticos'
HERRAMIENTAS = Path(__file__).resolve().parent
UNA_PRUEBA = 'tests.test_web.Sesion.test_rol_y_capacidades_las_deriva_el_servidor'
# Sin textos legales publicados nadie puede registrarse; solo el propietario de la base los publica.
PUBLICAR = ('from django.db import connection\n'
            'with connection.cursor() as k:\n'
            '    for tipo in ("terminos", "aviso_privacidad", "politica_cookies"):\n'
            '        k.execute("SELECT chilito_publicar_documento_legal(%s, %s, %s, %s)", [tipo, "1.0", tipo, "<p>Texto de prueba.</p>"])')
BORRAR = ('from django.db import connection as c\n'
          'with c._nodb_cursor() as k:\n'
          f'    k.execute("DROP DATABASE IF EXISTS {TEMPORAL}")')


def entorno_pruebas(base=None):
    archivo = leer('.env')
    valores = {**os.environ, **archivo, 'CHILITO_ENV': 'testing', 'DJANGO_SETTINGS_MODULE': 'config.testing',
               'CHILITO_DB_USER': archivo.get('CHILITO_TEST_DB_USER', ''),
               'CHILITO_DB_PASSWORD': archivo.get('CHILITO_TEST_DB_PASSWORD', ''),
               'CHILITO_DB_NAME': base or 'chilito_integracion_sinteticos', 'PYTHONDONTWRITEBYTECODE': '1'}
    for clave in ('CHILITO_SMTP_CONFIG', 'CHILITO_CONTACTO_SOPORTE', 'CHILITO_TEST_DB_USER', 'CHILITO_TEST_DB_PASSWORD'):
        valores.pop(clave, None)     # las pruebas no usan el correo real ni el contacto real
    if valores['CHILITO_DB_USER'] != 'chilito_pkg_owner':
        sys.exit('CHILITO_TEST_DB_USER del .env debe ser chilito_pkg_owner')
    return valores


def entorno_runtime(base=None):
    valores = {**os.environ, **leer('.env'), 'DJANGO_SETTINGS_MODULE': 'config.settings', 'PYTHONDONTWRITEBYTECODE': '1'}
    if valores.get('CHILITO_DB_USER') != 'chilito_pkg_runtime':
        sys.exit('.env debe usar chilito_pkg_runtime')
    if base:
        valores['CHILITO_DB_NAME'] = base
    if valores.get('CHILITO_PRUEBAS_CLAVE_RUNTIME'):
        valores['CHILITO_DB_PASSWORD'] = valores['CHILITO_PRUEBAS_CLAVE_RUNTIME']   # la clave del rol en la base de pruebas
    return valores


def correr(argumentos, entorno):
    return subprocess.run([sys.executable, *argumentos], cwd=BACKEND, env=entorno).returncode


def suite():
    return correr(['manage.py', 'test', '--noinput'], entorno_pruebas())


def flujos():
    """Flujos HTTP con el rol limitado, SOLO en la base temporal (nunca en la oficial).

    Crea la base temporal con las migraciones (que ya traen los privilegios), publica los textos legales
    como propietario y ejecuta cada flujo con chilito_pkg_runtime apuntando explícitamente a ella. Cada script vuelve a
    comprobar el destino efectivo antes de escribir (destino_temporal.py). Al final se borra.
    """
    propietario = entorno_pruebas()
    correr(['manage.py', 'shell', '-c', BORRAR], propietario)
    try:
        estado = correr(['manage.py', 'test', UNA_PRUEBA, '--noinput', '--keepdb'], propietario)
        estado = estado or correr(['manage.py', 'shell', '-c', PUBLICAR], entorno_pruebas(TEMPORAL))
        if estado:
            return estado
        resultados = [correr([str(HERRAMIENTAS / f'{n}.py')], entorno_runtime(TEMPORAL))
                      for n in ('probar_seguridad', 'probar_mfa', 'probar_privacidad')]
        return max(resultados)
    finally:
        correr(['manage.py', 'shell', '-c', BORRAR], propietario)


if __name__ == '__main__':
    modos = {'suite': suite, 'flujos': flujos}
    if len(sys.argv) != 2 or sys.argv[1] not in modos:
        sys.exit(__doc__)
    sys.exit(modos[sys.argv[1]]())
