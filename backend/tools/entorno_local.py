"""Carga el .env del proyecto en este proceso, sin mostrar sus valores. Solo perfil local."""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def leer(nombre):
    """Variables de un archivo de entorno del proyecto."""
    archivo = RAIZ / nombre
    if not archivo.is_file():
        sys.exit(f'Falta el archivo {nombre} en la carpeta web-integracion')
    valores = {}
    for linea in archivo.read_text(encoding='utf8').splitlines():
        linea = linea.strip()
        if linea and not linea.startswith('#') and '=' in linea:
            clave, valor = linea.split('=', 1)
            valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def cargar():
    os.environ.update(leer('.env'))
    if os.environ.get('CHILITO_ENV') != 'local':
        sys.exit('Esta herramienta solo sirve con CHILITO_ENV=local')
    smtp = os.environ.get('CHILITO_SMTP_CONFIG')
    if smtp:
        # La contraseña vive fuera del repositorio, en un archivo 0600 indicado expresamente.
        from correo_config import load_smtp_file
        os.environ.update(load_smtp_file(smtp))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    sys.path.insert(0, str(RAIZ / 'backend'))
