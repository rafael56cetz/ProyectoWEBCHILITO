"""Contraseñas filtradas (auditoría B-8, ASVS 5.0 V6.2): consulta k-anónima a Have I Been Pwned.

Solo salen del servidor los 5 primeros caracteres del SHA-1 de la contraseña; la comparación del resto se hace aquí.
La cabecera `Add-Padding` hace que todas las respuestas pesen parecido. Si el servicio no responde en 2 s, la contraseña
se acepta y se registra el fallo: la disponibilidad del registro no depende de un tercero.

Se activa con CHILITO_VERIFICAR_FILTRADAS (1 por defecto en despliegue; 0 en local y en pruebas, que no salen a la red).
"""
import hashlib
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger('cuentas')

URL = 'https://api.pwnedpasswords.com/range/'
ESPERA_SEGUNDOS = 2


def _consultar(prefijo):
    peticion = urllib.request.Request(URL + prefijo, headers={'User-Agent': 'password-check', 'Add-Padding': 'true'})
    with urllib.request.urlopen(peticion, timeout=ESPERA_SEGUNDOS) as respuesta:  # noqa: S310 (URL fija https)
        return respuesta.read(1_000_000).decode('ascii', 'replace')


def veces_filtrada(password, consultar=None):
    """Veces que aparece la contraseña en filtraciones conocidas. None si no se pudo consultar."""
    resumen = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()  # noqa: S324 (lo exige el protocolo)
    prefijo, resto = resumen[:5], resumen[5:]
    try:
        cuerpo = (consultar or _consultar)(prefijo)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        logger.warning('contrasenas-filtradas-no-disponible')
        return None
    for linea in cuerpo.splitlines():
        sufijo, _, veces = linea.strip().partition(':')
        if sufijo == resto:
            try:
                return int(veces)
            except ValueError:
                return None
    return 0


class ContrasenaFiltrada:
    def __init__(self, consultar=None):
        self.consultar = consultar

    def validate(self, password, user=None):
        if not getattr(settings, 'CHILITO_VERIFICAR_FILTRADAS', False):
            return
        if veces_filtrada(password, self.consultar):
            raise ValidationError('Esta contraseña aparece en filtraciones conocidas. Elige otra.', code='password_pwned')

    def get_help_text(self):
        return 'No uses una contraseña que haya aparecido en filtraciones conocidas.'
