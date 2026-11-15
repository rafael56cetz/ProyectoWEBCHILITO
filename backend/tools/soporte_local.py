"""Ejecuta el comando retirar_factores con el .env local. Ver su ayuda con --help."""
import sys

from entorno_local import cargar

cargar()
from django.core.management import execute_from_command_line

execute_from_command_line(['manage.py', 'retirar_factores', *sys.argv[1:]])
