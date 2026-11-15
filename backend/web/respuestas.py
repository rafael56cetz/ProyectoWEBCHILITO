"""Contrato HTTP común: errores genéricos y JSON estricto. Una sola versión por proyecto."""
import json
import math

from django.http import JsonResponse
from django.http.request import RawPostDataException


class EntradaInvalida(ValueError):
    pass


def error(status, code):
    return JsonResponse({'status': status, 'code': code}, status=status)


def _sin_repetidas(pares):
    datos = {}
    for clave, valor in pares:
        if clave in datos:
            raise EntradaInvalida
        datos[clave] = valor
    return datos


def _sin_constante(_nombre):
    # NaN e Infinity no son JSON: json.loads los admite por compatibilidad con JavaScript.
    raise EntradaInvalida


def _numero_finito(texto):
    # 1e999 no pasa por parse_constant, pero también se convertiría en infinito.
    valor = float(texto)
    if not math.isfinite(valor):
        raise EntradaInvalida
    return valor


def leer_json(request, permitidos, *, vacio=False):
    """Objeto JSON con solo los campos permitidos. Rechaza claves repetidas y otros formatos.

    `vacio` admite una petición sin cuerpo. CSRF puede haber consumido un formulario:
    se comprueba el tipo antes de leer `request.body`.
    """
    if request.content_type != 'application/json':
        if vacio and request.META.get('CONTENT_LENGTH', '') in ('', '0'):
            return {}
        raise EntradaInvalida
    try:
        crudo = request.body
    except RawPostDataException:
        raise EntradaInvalida from None
    if not crudo:
        if vacio:
            return {}
        crudo = b'{}'
    datos = json.loads(crudo, object_pairs_hook=_sin_repetidas, parse_constant=_sin_constante,
                       parse_float=_numero_finito)
    if not isinstance(datos, dict) or set(datos) - set(permitidos):
        raise EntradaInvalida
    return datos
