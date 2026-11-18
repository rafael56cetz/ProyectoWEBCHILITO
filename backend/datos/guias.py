"""Guías de cuidado: contenido compartido del sitio. Lógica, validación y autorización.

Reglas:
- Leer exige una cuenta activa y verificada; no exige huerto, porque no expone datos de ninguno.
- Gestionar exige la capacidad explícita `gestionar_guias` y TOTP o WebAuthn (`require_cap`).
- Una ficha nueva siempre es borrador. Solo `publicar` la hace visible.
- Retirar es una baja lógica; no hay borrado físico.
- Cada escritura indica la versión que vio quien edita: si otra persona cambió la ficha, se rechaza.
- El contenido es texto plano. Se conserva tal cual: la vista lo inserta siempre como texto.
"""
import re
import secrets

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from web import validacion as v

from . import services as s
from .models import GuiaCuidado

MAX_PREGUNTA = 200
MAX_RESPUESTA = 4000
MAX_FUENTE_NOMBRE = 120
MAX_FUENTE_URL = 500
MAX_ORDEN = 9999
MAX_LISTA = 500
CAPACIDAD = 'gestionar_guias'
URL_RE = re.compile(r'https?://([^\s/?#@:]+)(:[0-9]{1,5})?([/?#]\S*)?', re.ASCII | re.IGNORECASE)
URL_ESQUEMA_RE = re.compile(r'https?://')


# --- Validación ---------------------------------------------------------------------------------
def _texto(valor, maximo, campo, *, multilinea=False, requerido=True):
    """Texto libre: el tabulador y el espacio duro pasan a espacio; sin caracteres de control y con largo máximo."""
    if not isinstance(valor, str):
        raise v.CampoInvalido(campo, 'texto-no-valido', 'Escribe un texto.')
    return v.texto_libre(valor.replace('\t', ' ').replace('\u00a0', ' '), campo, maximo=maximo, multilinea=multilinea, requerido=requerido)


def _entero(valor, minimo, maximo):
    # bool es subclase de int: se excluye con la comparación exacta de tipo.
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ValidationError('Número no válido')
    return valor


def _fuente(nombre, url):
    """Solo http y https, con servidor y sin credenciales. Sin enlace, el nombre es opcional."""
    nombre = _texto(nombre, MAX_FUENTE_NOMBRE, 'sourceName', requerido=False)
    url = _texto(url, MAX_FUENTE_URL, 'sourceUrl', requerido=False)
    if not url:
        return nombre, ''
    if not nombre:
        raise v.CampoInvalido('sourceName', 'campo-requerido', 'Escribe el nombre de la fuente.')
    if not URL_ESQUEMA_RE.match(url) or not URL_RE.fullmatch(url):
        raise v.CampoInvalido('sourceUrl', 'formato-no-valido', 'Escribe un enlace que empiece con https:// o http://.')
    return nombre, url


def _contenido(pregunta, respuesta, orden, fuente_nombre, fuente_url):
    nombre, url = _fuente(fuente_nombre, fuente_url)
    return {'pregunta': _texto(pregunta, MAX_PREGUNTA, 'question'), 'respuesta': _texto(respuesta, MAX_RESPUESTA, 'answer', multilinea=True),
            'orden': v.entero(orden, 'order', 1, MAX_ORDEN), 'fuente_nombre': nombre, 'fuente_url': url}


def _clave_nueva(pregunta):
    # slugify conserva «_», que la clave estable no admite.
    base = re.sub(r'[^a-z0-9]+', '-', slugify(pregunta))[:48].strip('-') or 'guia'
    return f'{base}-{secrets.token_hex(3)}'


# --- Persistencia -------------------------------------------------------------------------------
def _bloquear(guia_id, version):
    guia = GuiaCuidado.objects.select_for_update().get(pk=guia_id)
    if guia.version != _entero(version, 1, 2147483647):
        raise s.RegistroDesactualizado('Otra persona cambió esta ficha')
    return guia


def _guardar(guia, usuario, campos):
    guia.version += 1
    guia.actualizado_en = timezone.now()
    guia.actualizado_por = usuario
    guia.save(update_fields=[*campos, 'version', 'actualizado_en', 'actualizado_por'])


def _acuse(guia):
    # El recibo de idempotencia guarda esta respuesta: sin texto ni actores.
    return {'status': 'accepted', 'guide': {'id': str(guia.pk), 'key': guia.clave, 'state': guia.estado, 'version': guia.version}}


# --- Lectura ------------------------------------------------------------------------------------
def _ordenadas(consulta):
    return consulta.order_by('orden', 'creado_en', 'clave')


def _dto_publico(guia):
    fuente = {'name': guia.fuente_nombre, 'url': guia.fuente_url or None} if guia.fuente_nombre else None
    return {'key': guia.clave, 'question': guia.pregunta, 'answer': guia.respuesta, 'source': fuente}


def publicadas(actor):
    s.identity(actor)
    return {'status': 'ready', 'guides': [_dto_publico(g) for g in _ordenadas(GuiaCuidado.objects.filter(estado='publicada'))[:MAX_LISTA]]}


def _correo(usuario):
    return usuario.email if usuario else None


def _dto_panel(guia):
    return {'id': str(guia.pk), 'key': guia.clave, 'question': guia.pregunta, 'answer': guia.respuesta, 'order': guia.orden,
            'state': guia.estado, 'sourceName': guia.fuente_nombre, 'sourceUrl': guia.fuente_url, 'version': guia.version,
            'createdAt': guia.creado_en.isoformat(), 'updatedAt': guia.actualizado_en.isoformat(),
            'createdBy': _correo(guia.creado_por), 'updatedBy': _correo(guia.actualizado_por)}


def panel(actor):
    s.require_cap(actor, CAPACIDAD)
    filas = _ordenadas(GuiaCuidado.objects.select_related('creado_por', 'actualizado_por'))[:MAX_LISTA]
    return {'status': 'ready', 'guides': [_dto_panel(g) for g in filas]}


# --- Escritura ----------------------------------------------------------------------------------
@transaction.atomic
def crear(actor, *, pregunta, respuesta, orden, fuente_nombre, fuente_url):
    usuario = s.require_cap(actor, CAPACIDAD)
    datos = _contenido(pregunta, respuesta, orden, fuente_nombre, fuente_url)
    guia = GuiaCuidado.objects.create(clave=_clave_nueva(datos['pregunta']), estado='borrador', creado_por=usuario, actualizado_por=usuario, **datos)
    s.auditar(usuario, 'crear_guia', entidad='guia', entidad_id=guia.pk)
    return _acuse(guia)


@transaction.atomic
def editar(actor, guia_id, version, *, pregunta, respuesta, orden, fuente_nombre, fuente_url):
    """No cambia el estado: en una ficha publicada, guardar actualiza lo que ya ven las personas."""
    usuario = s.require_cap(actor, CAPACIDAD)
    datos = _contenido(pregunta, respuesta, orden, fuente_nombre, fuente_url)
    guia = _bloquear(guia_id, version)
    for campo, valor in datos.items():
        setattr(guia, campo, valor)
    _guardar(guia, usuario, datos)
    s.auditar(usuario, 'editar_guia', entidad='guia', entidad_id=guia.pk)
    return _acuse(guia)


def _cambiar_estado(actor, guia_id, version, permitidos, nuevo, accion):
    usuario = s.require_cap(actor, CAPACIDAD)
    guia = _bloquear(guia_id, version)
    if guia.estado not in permitidos:
        raise s.RegistroDesactualizado('Transición no válida')
    guia.estado = nuevo
    _guardar(guia, usuario, ['estado'])
    s.auditar(usuario, accion, entidad='guia', entidad_id=guia.pk)
    return _acuse(guia)


@transaction.atomic
def publicar(actor, guia_id, version):
    return _cambiar_estado(actor, guia_id, version, {'borrador', 'retirada'}, 'publicada', 'publicar_guia')


@transaction.atomic
def retirar(actor, guia_id, version):
    return _cambiar_estado(actor, guia_id, version, {'publicada'}, 'retirada', 'retirar_guia')
