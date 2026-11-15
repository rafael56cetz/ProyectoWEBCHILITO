"""Soporte: retira los métodos de una cuenta que los perdió todos.

Solo tras verificar la identidad fuera de banda. Lo ejecuta el equipo en el servidor;
no existe ninguna ruta web equivalente. Recuperar la contraseña no quita un factor.
"""
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from datos.services import auditar


class Command(BaseCommand):
    help = 'Retira el segundo factor de una cuenta, con auditoría'

    def add_arguments(self, parser):
        parser.add_argument('correo')
        parser.add_argument('--operador', required=True, help='Cuenta de quien atiende el caso')
        parser.add_argument('--identidad-verificada', action='store_true')

    @transaction.atomic
    def handle(self, *args, correo, operador, identidad_verificada, **options):
        if not identidad_verificada:
            raise CommandError('Verifica la identidad fuera de banda y usa --identidad-verificada')
        usuarios = get_user_model().objects
        try:
            cuenta, responsable = usuarios.get(email__iexact=correo), usuarios.get(email__iexact=operador)
        except usuarios.model.DoesNotExist:
            raise CommandError('Cuenta no encontrada') from None
        if cuenta.pk == responsable.pk:
            raise CommandError('El operador no puede atender su propia cuenta')
        borrados, _ = Authenticator.objects.filter(user=cuenta).delete()
        auditar(responsable, 'retirar_segundo_factor', entidad='cuenta', entidad_id=cuenta.pk)
        self.stdout.write(f'Métodos retirados: {borrados}')
