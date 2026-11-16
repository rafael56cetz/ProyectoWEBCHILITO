"""Arranca la aplicación en http://localhost:8780 con el .env del proyecto.

Solo para el equipo local. No muestra los valores del .env.
"""
import os

from entorno_local import cargar

cargar()
os.environ['CHILITO_ORIGIN'] = 'http://localhost:8780'
print('Abre http://localhost:8780 (no 127.0.0.1). Detén con Ctrl+C.', flush=True)
from django.core.management import execute_from_command_line

execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8780', '--noreload'])
