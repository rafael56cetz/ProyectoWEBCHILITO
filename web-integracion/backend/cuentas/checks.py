from django.core.checks import Error, Tags, register
from cuentas.registration import configuration_problems

@register(Tags.security)
def check_local_registration(app_configs, **kwargs):
    return [Error(message, id="cuentas.E001") for message in configuration_problems()]
