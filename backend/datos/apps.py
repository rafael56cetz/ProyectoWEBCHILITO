from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_out


class DatosConfig(AppConfig):
    default_auto_field='django.db.models.BigAutoField'
    name='datos'

    def ready(self):
        from datos.services import cerrar_sesion_tecnica_al_salir
        user_logged_out.connect(cerrar_sesion_tecnica_al_salir, dispatch_uid='datos.sesion_tecnica.salida')
