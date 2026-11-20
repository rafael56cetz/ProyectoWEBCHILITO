"""Tareas periódicas en una sola orden, para el programador de tareas de la nube (auditoría B-1 y D-6).

1. `chilito_mantenimiento_periodico()`: depuración, caducidad de órdenes y códigos y limpieza de cuotas expiradas.
   Sigue anonimizando las solicitudes de eliminación antiguas que aún estén pendientes (anteriores a web.0010); las
   nuevas se borran físicamente al momento con `chilito_eliminar_cuenta`.
2. `revisar_recomendaciones`: recomendaciones de las plantas por el paso del tiempo (p. ej. más de 21 días en
   germinación). Desde B-1, abrir «Mi huerto» (GET) ya no las genera; las de humedad siguen saliendo con cada lectura.
3. `enviar_avisos_pendientes`: reintento de los avisos por correo.

Cada paso es independiente: si uno falla, se informa y se siguen los demás; el código de salida es 1 si alguno falló.
Ejemplo (cron, cada 15 minutos):  */15 * * * *  cd /ruta/backend && python manage.py tareas_periodicas
"""
import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction

logger = logging.getLogger('datos')


class Command(BaseCommand):
    help = 'Mantenimiento de la base, recomendaciones de las plantas y reintento de avisos por correo.'

    def handle(self, *args, **options):
        fallos = []

        def paso(nombre, accion):
            try:
                accion()
            except (DatabaseError, CommandError, OSError):
                logger.exception('tarea-periodica-fallida')
                fallos.append(nombre)
                self.stderr.write(f'Falló: {nombre}')

        def mantenimiento():
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute('SELECT chilito_mantenimiento_periodico()')
                self.stdout.write(f'Mantenimiento: {cursor.fetchone()[0]}')

        paso('mantenimiento', mantenimiento)
        paso('recomendaciones', lambda: call_command('revisar_recomendaciones', stdout=self.stdout))
        paso('avisos', lambda: call_command('enviar_avisos_pendientes', stdout=self.stdout))
        if fallos:
            raise CommandError(f'Tareas con fallo: {", ".join(fallos)}')
