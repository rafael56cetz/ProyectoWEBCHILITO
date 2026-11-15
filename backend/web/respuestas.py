"""Contrato HTTP común: errores genéricos y JSON estricto. Una sola versión por proyecto."""
import json
import logging
import math

from django.http import JsonResponse
from django.http.request import RawPostDataException


logger = logging.getLogger(__name__)
REGLA_DE_DATOS = '23514'
# Reglas de la base que la persona puede resolver; el resto sigue como `regla-de-datos`.
REGLAS_CON_CODIGO = (('Máximo 3 huertos activos', 'huerto-limite', 'Ya tienes 3 huertos. Archiva uno para crear otro.'),
                     ('Ya tienes un huerto sin equipo', 'huerto-sin-equipo',
                      'Ya tienes un huerto sin equipo. Vincúlalo antes de crear otro.'),
                     ('Desvincula el equipo antes de archivar', 'huerto-con-equipo',
                      'Desvincula el equipo antes de archivar este huerto.'),
                     ('Este huerto ya tiene equipo', 'huerto-con-equipo', 'Este huerto ya tiene un equipo vinculado.'),
                     ('El equipo no está vinculado', 'equipo-no-vinculado', 'Este huerto no tiene un equipo vinculado.'))


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


# Índices únicos que la persona puede provocar sin querer: un caso de soporte activo por huerto y una orden igual en curso.
UNICOS_CON_CODIGO = {'caso_uno_activo_por_huerto': ('caso-activo', 'Ya tienes una solicitud de soporte abierta.'),
                     'comando_uno_en_curso': ('orden-en-curso', 'Ya hay una orden igual esperando la respuesta de tu equipo.')}


def _unico_repetido(diagnostico):
    regla = UNICOS_CON_CODIGO.get(getattr(diagnostico, 'constraint_name', None))
    if regla is None:
        return None
    return JsonResponse({'status': 409, 'code': regla[0], 'message': regla[1]}, status=409)


def respuesta_de_base(fallo):
    """409 genérico si la base rechazó una regla de datos (23514); en otro caso, None.

    El detalle va solo al registro del servidor: tabla, regla y el mensaje fijo de la base, sin valores."""
    diagnostico = getattr(getattr(fallo, '__cause__', None), 'diag', None)
    if getattr(getattr(fallo, '__cause__', None), 'sqlstate', None) == '23505':
        return _unico_repetido(diagnostico)
    if getattr(getattr(fallo, '__cause__', None), 'sqlstate', None) != REGLA_DE_DATOS:
        return None
    logger.warning('regla-de-datos tabla=%s regla=%s mensaje=%s', diagnostico.table_name,
                   diagnostico.constraint_name, diagnostico.message_primary)
    code, message = next(((codigo, texto) for inicio, codigo, texto in REGLAS_CON_CODIGO
                          if diagnostico.message_primary.startswith(inicio)),
                         ('regla-de-datos', 'La operación no cumple una regla de los datos.'))
    return JsonResponse({'status': 409, 'code': code, 'message': message}, status=409)
