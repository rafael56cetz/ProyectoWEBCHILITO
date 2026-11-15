"""Reintenta los avisos por correo pendientes o fallidos (máximo 5 intentos, espera creciente).

Hoy se ejecuta a mano; en la nube lo lanzará un programador de tareas. No imprime destinatarios ni contenido.
"""
from django.core.management.base import BaseCommand

from datos.avisos_correo import reintentar_pendientes


class Command(BaseCommand):
    help = 'Reintenta los avisos por correo pendientes o fallidos.'

    def handle(self, *args, **options):
        self.stdout.write(f'Avisos aceptados por SMTP: {reintentar_pendientes()}')
