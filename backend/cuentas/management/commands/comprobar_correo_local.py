"""Send only a harmless connectivity message to the privately authorized local test account."""
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from cuentas.email import mail_configuration, MailUnavailable

class Command(BaseCommand):
    help = "Comprueba SMTP con el destinatario privado autorizado; no crea cuentas ni códigos."
    def handle(self, *args, **options):
        try:
            sender, recipients, _ = mail_configuration()
            if sender not in recipients:
                raise MailUnavailable
            sent = send_mail(
                "El Chilito: comprobación de correo local",
                "Esta es una comprobación autorizada del envío de correo de El Chilito. "
                "No crea una cuenta, no verifica una dirección y no contiene enlaces ni códigos de acceso.",
                None, [sender], fail_silently=False)
            if sent != 1:
                raise MailUnavailable
        except MailUnavailable:
            raise CommandError("No se pudo completar el envío. Revisa la configuración privada de Gmail.") from None
        self.stdout.write("El servidor SMTP aceptó un correo de prueba. La recepción debe confirmarse en Gmail.")
