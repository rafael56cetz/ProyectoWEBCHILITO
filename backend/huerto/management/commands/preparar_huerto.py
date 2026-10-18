from django.core.management.base import BaseCommand
from huerto.services import provision_garden
class Command(BaseCommand):
    help = "Inicializa el huerto y tres zonas; no crea cuentas, sensores ni lecturas."
    def handle(self, *args, **options):
        garden = provision_garden()
        self.stdout.write(f"Huerto preparado: id={garden.pk}; zonas={garden.zona_set.count()}.")
