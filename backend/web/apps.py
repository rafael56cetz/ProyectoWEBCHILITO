from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_in


class WebConfig(AppConfig):
    name = 'web'

    def ready(self):
        from web.sesion import registrar_autenticacion
        user_logged_in.connect(registrar_autenticacion, dispatch_uid='web.sesion.inicio')
