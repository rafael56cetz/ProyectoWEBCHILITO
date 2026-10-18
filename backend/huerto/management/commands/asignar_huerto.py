from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from huerto.models import Huerto
from huerto.services import assign_membership
class Command(BaseCommand):
    help = "Asigna o desactiva explicitamente membresia. Solo para operador local autorizado."
    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--huerto", type=int, required=True)
        parser.add_argument("--desactivar", action="store_true")
    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get_by_natural_key(options["email"])
            garden = Huerto.objects.get(pk=options["huerto"])
        except (get_user_model().DoesNotExist, Huerto.DoesNotExist):
            raise CommandError("Cuenta o huerto no disponibles.") from None
        assign_membership(user, garden, active=not options["desactivar"])
        self.stdout.write("Membresia actualizada; la verificacion del correo sigue siendo independiente.")
