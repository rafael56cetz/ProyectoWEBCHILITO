"""Cuotas e idempotencia de escrituras. No decide permisos: repite los de datos.services."""
import hashlib
import hmac
import json

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection, transaction
from django.utils import timezone

from datos import services as s

from .models import Idempotencia


class Conflicto(Exception):
    pass


def _bloqueo(texto):
    return int.from_bytes(hashlib.sha256(texto.encode()).digest()[:8], signed=True)


def _esperar(texto):
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)', [_bloqueo(texto)])


def dentro_de_cuota(actor, ruta):
    tramo = int(timezone.now().timestamp()) // 60
    alcance = 'technical' if '/soporte/' in ruta or '/sesiones/' in ruta else 'write'
    clave = f'web-rate:{actor.pk}:{alcance}:{tramo}'
    with transaction.atomic():
        _esperar(clave)
        total = cache.get(clave, 0) + 1
        cache.set(clave, total, 120)
    return total <= (15 if alcance == 'technical' else 60)


def _sin_secretos(valor):
    if isinstance(valor, dict):
        return {k: (None if k in {'token', 'verificador', 'password', 'data', 'code'} else _sin_secretos(v)) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_sin_secretos(v) for v in valor]
    return valor


def ejecutar_idempotente(actor, clave, ruta, huella, trabajo):
    """Ejecuta una sola vez. Un recibo guardado nunca alarga un acceso ya perdido."""
    with transaction.atomic():
        _esperar(f'{actor.pk}:{clave}')
        previo = Idempotencia.objects.filter(actor=actor, clave=clave).first()
        if previo:
            if previo.ruta != ruta or not hmac.compare_digest(previo.huella, huella):
                raise Conflicto
            return previo.respuesta
        resultado = trabajo()
        Idempotencia.objects.create(actor=actor, clave=clave, ruta=ruta, huella=huella, respuesta=_sin_secretos(resultado))
    return resultado


def huella_de(datos):
    texto = json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hmac.new(settings.CHILITO_SUPPORT_KEY.encode(), texto.encode(), hashlib.sha256).hexdigest()



def _texto_contacto(valor, maximo, *, multilinea=False):
    if not isinstance(valor, str):
        raise ValidationError('Texto no válido')
    limpio = valor.strip()
    permitido = limpio.replace('\n', '').replace('\r', '') if multilinea else limpio
    if len(limpio) > maximo or (permitido and not permitido.isprintable()):
        raise ValidationError('Texto no válido')
    return limpio


def enviar_contacto(datos):
    """Consulta del producto: se guarda en el buzón administrativo; el aviso por correo lo encola la base.
    Un fallo del correo no pierde la consulta: el aviso queda como fallido y se reintenta."""
    nombre = _texto_contacto(datos.get('name', ''), 100)
    correo = _texto_contacto(datos.get('email'), 254)
    mensaje = _texto_contacto(datos.get('message'), 2000, multilinea=True)
    validate_email(correo)
    if not mensaje:
        raise ValidationError('Mensaje requerido')
    return s.record_inquiry(nombre, correo, mensaje)
