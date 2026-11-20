"""Soporte: retira los métodos de una cuenta que los perdió todos.

Solo tras verificar la identidad fuera de banda. Lo ejecuta el equipo en el servidor;
no existe ninguna ruta web equivalente. Recuperar la contraseña no quita un factor.

Endurecido (auditoría B-9):
- `--operador` debe ser una cuenta activa y verificada con `gestionar_administradores` y un segundo factor fuerte, para
  que la auditoría no quede a nombre de un tercero cualquiera.
- `--caso <folio>` es obligatorio y se guarda en la auditoría.
- Si la cuenta objetivo tiene capacidades de administración, hay que repetir su correo con `--confirmar`.
- Si la cuenta no tenía métodos, no se registra nada y el comando falla.
"""
import re

from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from datos import services as s
from datos.services import auditar

CAPACIDAD_OPERADOR = 'gestionar_administradores'
FORMATO_CASO = re.compile(r'^[A-Za-z0-9][A-Za-z0-9-]{2,39}$')


class Command(BaseCommand):
    help = 'Retira el segundo factor de una cuenta, con auditoría'

    def add_arguments(self, parser):
        parser.add_argument('correo')
        parser.add_argument('--operador', required=True, help='Cuenta de quien atiende el caso (con gestionar_administradores y segundo factor)')
        parser.add_argument('--caso', required=True, help='Folio del caso de soporte que respalda el retiro')
        parser.add_argument('--confirmar', default='', help='Repite el correo de la cuenta si tiene capacidades de administración')
        parser.add_argument('--identidad-verificada', action='store_true')

    @transaction.atomic
    def handle(self, *args, correo, operador, caso, confirmar, identidad_verificada, **options):
        if not identidad_verificada:
            raise CommandError('Verifica la identidad fuera de banda y usa --identidad-verificada')
        if not FORMATO_CASO.match(caso or ''):
            raise CommandError('Indica el folio del caso con --caso (letras, números y guiones)')
        usuarios = get_user_model().objects
        try:
            cuenta, responsable = usuarios.get(email__iexact=correo), usuarios.get(email__iexact=operador)
        except usuarios.model.DoesNotExist:
            raise CommandError('Cuenta no encontrada') from None
        if cuenta.pk == responsable.pk:
            raise CommandError('El operador no puede atender su propia cuenta')
        try:
            s.require_cap(responsable, CAPACIDAD_OPERADOR)
        except PermissionDenied:
            raise CommandError('El operador debe ser una cuenta verificada con gestionar_administradores y segundo factor') from None
        try:
            administra = bool(s.capabilities(cuenta))
        except PermissionDenied:     # cuenta sin verificar o inactiva: no puede tener capacidades vigentes
            administra = False
        if administra and (confirmar or '').strip().lower() != cuenta.email.lower():
            raise CommandError('La cuenta tiene capacidades de administración: repite su correo con --confirmar')
        borrados, _ = Authenticator.objects.filter(user=cuenta).delete()
        if not borrados:
            raise CommandError('La cuenta no tenía métodos que retirar')
        auditar(responsable, 'retirar_segundo_factor', entidad='cuenta', entidad_id=cuenta.pk, detalle={'caso': caso})
        self.stdout.write(f'Métodos retirados: {borrados}')
