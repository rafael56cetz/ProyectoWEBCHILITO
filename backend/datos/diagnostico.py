"""Resumen de la tarjeta del huerto. Valida y proyecta; hoy no existe ningún productor.

Contrato (README.md, sección API): `diagnosis` es dato hermano de `garden` y vale null sin productor.
- `rule` es el mensaje principal, determinado por reglas. Sin una regla válida no hay resumen.
- `explanation` es opcional y nunca sustituye a `rule`. Solo sale con texto si está disponible y vigente.
- `readings` y `explanation` tienen vigencias independientes: caducar una no altera la otra.

Un candidato inválido o un productor que falla no rompen la pantalla: el resumen queda en null.
"""
import logging
from datetime import UTC, datetime

from django.utils import timezone

from . import services as s

logger = logging.getLogger(__name__)

MAX_TITULO = 120
MAX_MENSAJE = 600
MAX_ACCION = 200
MAX_EXPLICACION = 1200
ESTADOS_LECTURA = {'missing', 'stale', 'current'}
SIN_EXPLICACION = {'status': 'unavailable', 'text': None, 'source': None, 'generatedAt': None, 'expiresAt': None}


def _texto(valor, maximo, *, multilinea=False):
    if not isinstance(valor, str):
        raise ValueError('texto')
    limpio = valor.strip()
    revisable = limpio.replace('\n', '') if multilinea else limpio
    if not limpio or len(limpio) > maximo or not revisable.isprintable():
        raise ValueError('texto')
    return limpio


def _fecha(valor):
    if not isinstance(valor, str):
        raise ValueError('fecha')
    fecha = datetime.fromisoformat(valor)
    if fecha.tzinfo is None:
        raise ValueError('fecha')
    try:
        return fecha.astimezone(UTC)
    except OverflowError as error:  # fecha en el límite del calendario al pasarla a UTC
        raise ValueError('fecha') from error


def _canonica(fecha):
    """Salida única, con T y zona, que el adaptador del navegador acepta tal cual."""
    return fecha.isoformat(timespec='milliseconds')


def _lecturas(crudo):
    estado = crudo['state']
    if estado not in ESTADOS_LECTURA:
        raise ValueError('lecturas')
    if estado == 'missing':
        if crudo.get('at') is not None:
            raise ValueError('lecturas')
        return {'state': 'missing', 'at': None}
    return {'state': estado, 'at': _canonica(_fecha(crudo['at']))}


def _regla(crudo):
    if crudo['source'] != 'rules':
        raise ValueError('origen')
    generada = _canonica(_fecha(crudo['generatedAt']))
    siguiente = crudo.get('next')
    return {'source': 'rules', 'title': _texto(crudo['title'], MAX_TITULO), 'message': _texto(crudo['message'], MAX_MENSAJE),
            'next': None if siguiente is None else _texto(siguiente, MAX_ACCION), 'generatedAt': generada}


def _explicacion(crudo, ahora):
    """Vacía, bloqueada, truncada o fallida salen igual: no disponible y sin texto."""
    if crudo is None:
        return None
    try:
        if crudo['status'] != 'available' or crudo['source'] != 'ai':
            return dict(SIN_EXPLICACION)
        generada, vence = _fecha(crudo['generatedAt']), _fecha(crudo['expiresAt'])
        texto = _texto(crudo['text'], MAX_EXPLICACION, multilinea=True)
        if vence <= generada:
            return dict(SIN_EXPLICACION)
    except (KeyError, TypeError, ValueError):
        return dict(SIN_EXPLICACION)
    fechas = {'source': 'ai', 'generatedAt': _canonica(generada), 'expiresAt': _canonica(vence)}
    if vence <= ahora:
        return {'status': 'expired', 'text': None, **fechas}
    return {'status': 'available', 'text': texto, **fechas}


def validar(candidato, ahora=None):
    """Reconstruye el resumen solo con los campos del contrato. Lanza si la regla no es válida."""
    return {'rule': _regla(candidato['rule']), 'readings': _lecturas(candidato['readings']),
            'explanation': _explicacion(candidato.get('explanation'), ahora or timezone.now())}


def _productor(garden_id):
    """Punto de conexión de la integración real, pendiente de definir junto con su persistencia."""
    return None


def proyeccion(actor, garden_id):
    s.member(actor, garden_id)
    try:
        candidato = _productor(garden_id)
        return None if candidato is None else validar(candidato)
    except Exception as error:
        # Solo el tipo: el contenido descartado no va a los registros.
        logger.warning('diagnostico-descartado %s', type(error).__name__)
        return None
