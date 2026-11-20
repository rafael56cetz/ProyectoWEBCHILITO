"""Reglas de entrada compartidas por todos los endpoints. Son las mismas que aplica el navegador
(frontend/modelos/comun.js, «Campos»), pero el servidor no confía en él y las vuelve a exigir.

Un dato que no cumple su regla lanza `CampoInvalido`: el endpoint responde 400 con el campo, un código
estable («solo-letras», «solo-numeros», …) y el mensaje que se puede mostrar junto al campo.
"""
import re
import unicodedata
from decimal import Decimal

from django.core.exceptions import ValidationError

# Nombre de persona: letras de cualquier idioma (acentos, ñ, ü), espacios, apóstrofo y guion.
SEPARADORES_PERSONA = frozenset(" '’-")
# Nombre de cosa (huerto, planta, alias, llave): letras, números, espacios y guion.
SEPARADORES_COSA = frozenset(' -')
IMPORTE = re.compile(r'[0-9]{1,8}(\.[0-9]{1,2})?', re.ASCII)


class CampoInvalido(ValidationError):
    """Un campo que no cumple su regla: 400 con `field`, `code` y `message`."""

    def __init__(self, campo, codigo, mensaje):
        super().__init__(mensaje, code=codigo)
        self.campo, self.codigo, self.mensaje = campo, codigo, mensaje

    def respuesta(self):
        return {'status': 400, 'code': self.codigo, 'field': self.campo, 'message': self.mensaje}


def _vacio(valor):
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _texto(valor, campo):
    if not isinstance(valor, str):
        raise CampoInvalido(campo, 'texto-no-valido', 'Escribe un texto.')
    return unicodedata.normalize('NFC', valor.strip())


def _clase(caracter):
    return unicodedata.category(caracter)[0]


def nombre_persona(valor, campo, *, requerido=True, minimo=2, maximo=60):
    """Nombre, apellidos, comprador. Vacío solo si no es obligatorio (devuelve '')."""
    if _vacio(valor):
        if requerido:
            raise CampoInvalido(campo, 'campo-requerido', 'Escribe un nombre.')
        return ''
    texto = _texto(valor, campo)
    if not all(_clase(c) in 'LM' or c in SEPARADORES_PERSONA for c in texto) or _clase(texto[0]) != 'L':
        raise CampoInvalido(campo, 'solo-letras', 'Solo letras, espacios, apóstrofo y guion.')
    if not minimo <= len(texto) <= maximo:
        raise CampoInvalido(campo, 'largo-no-valido', f'Escribe entre {minimo} y {maximo} caracteres.')
    return texto


def nombre_cosa(valor, campo, *, maximo, requerido=True, minimo=1):
    """Huerto, planta, alias, llave de acceso. «Planta 1» y «Mi huerto» son válidos."""
    if _vacio(valor):
        if requerido:
            raise CampoInvalido(campo, 'campo-requerido', 'Escribe un nombre.')
        return ''
    texto = _texto(valor, campo)
    if not all(_clase(c) in 'LMN' or c in SEPARADORES_COSA for c in texto):
        raise CampoInvalido(campo, 'solo-letras-numeros', 'Solo letras, números, espacios y guion.')
    if not minimo <= len(texto) <= maximo:
        raise CampoInvalido(campo, 'largo-no-valido', f'Escribe entre {minimo} y {maximo} caracteres.')
    return texto


def entero(valor, campo, minimo, maximo):
    """Número entero del JSON (no texto, no decimal, no booleano) dentro de su rango."""
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise CampoInvalido(campo, 'solo-numeros', f'Solo números entre {minimo} y {maximo}.')
    return valor


def entero_texto(valor, campo, *, maximo_digitos):
    """Número que viaja como texto (identificador de huerto, búsqueda por número): solo dígitos ASCII."""
    if not isinstance(valor, str) or not valor.isascii() or not valor.isdecimal() or len(valor) > maximo_digitos:
        raise CampoInvalido(campo, 'solo-numeros', 'Solo números.')
    return valor


def dinero(valor, campo):
    """Importe en texto: hasta 8 enteros y 2 decimales, sin signo (≥ 0)."""
    if not isinstance(valor, str) or not IMPORTE.fullmatch(valor):
        raise CampoInvalido(campo, 'importe-no-valido', 'Escribe un importe como 3500 o 3500.50.')
    return Decimal(valor)


def formato(valor, campo, patron, mensaje, *, requerido=True):
    """Formatos fijos (identificador, MAC, firmware, versión): el patrón completo."""
    if _vacio(valor) and not requerido:
        return ''
    if not isinstance(valor, str) or not patron.fullmatch(valor.strip()):
        raise CampoInvalido(campo, 'formato-no-valido', mensaje)
    return valor.strip()


def texto_libre(valor, campo, *, maximo, multilinea=False, requerido=False):
    """Notas, motivos, mensajes y guías: cualquier carácter visible, sin caracteres de control y con largo máximo.
    Con `multilinea`, se admiten saltos de línea (\\r\\n se guarda como \\n) y el tabulador pasa a espacio."""
    if _vacio(valor):
        if requerido:
            raise CampoInvalido(campo, 'campo-requerido', 'Este campo es obligatorio.')
        return ''
    if not isinstance(valor, str):
        raise CampoInvalido(campo, 'texto-no-valido', 'Escribe un texto.')
    texto = valor.replace('\r\n', '\n').replace('\r', '\n').replace('\t', ' ').strip() if multilinea else valor.strip()
    revisable = texto.replace('\n', '') if multilinea else texto
    if not revisable.isprintable():
        raise CampoInvalido(campo, 'caracteres-no-validos', 'El texto tiene caracteres no permitidos.')
    if len(texto) > maximo:
        raise CampoInvalido(campo, 'largo-no-valido', f'Escribe como máximo {maximo} caracteres.')
    return texto
