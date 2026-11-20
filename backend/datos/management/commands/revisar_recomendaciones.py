"""Revisa las recomendaciones de las plantas de todos los huertos activos (más de 21 días en germinación, sustrato
saturado, seca a pesar de los riegos). Cada una se avisa una sola vez por ciclo y situación (web.0007).

Las de humedad también se revisan con cada lectura del equipo; esta tarea cubre los huertos sin equipo y el paso del
tiempo. Hoy se ejecuta a mano; en la nube la lanzará un programador de tareas, como enviar_avisos_pendientes.
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Revisa las recomendaciones de las plantas y avisa a sus dueños.'

    def handle(self, *args, **options):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SELECT chilito_revisar_recomendaciones()')
            self.stdout.write(f'Recomendaciones nuevas: {cursor.fetchone()[0]}')
