"""Textos legales para quien tiene `gestionar_legales`: borradores, vista previa y publicación. La base exige la versión mayor,
avisa a las cuentas al publicar y no deja tocar una versión publicada; no sanea el contenido: eso se hace aquí, en el servidor,
tanto para la vista previa como para lo que verá el público."""
import hashlib
import io
import re
import zipfile

import mammoth

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404

from datos import services as s
from web.respuestas import ReglaDeNegocio

from .documentos_html import sanear_html
from .models import DocumentoLegal

CAPACIDAD = 'gestionar_legales'
TIPOS = ('terminos', 'aviso_privacidad', 'politica_cookies')
VERSION = re.compile(r'^[0-9]{1,3}\.[0-9]{1,3}(\.[0-9]{1,3})?$')
MAXIMO_TITULO = 120
MAXIMO_CONTENIDO = 200000
MAXIMO_ARCHIVO = 2 * 1024 * 1024
MAXIMO_PEGADO = 256 * 1024
# Un .docx es un ZIP: estos topes detienen un archivo pequeño que se descomprime en cientos de MB.
MAXIMO_ENTRADAS = 200
MAXIMO_DESCOMPRIMIDO = 20 * 1024 * 1024
FIRMA_ZIP = b'PK\x03\x04'
# Los títulos de Word pasan a h2, h3 y h4; se nombran por identificador y por nombre (Word en español conserva el nombre inglés).
NIVELES = {1: 'h2', 2: 'h3', 3: 'h4', 4: 'h4', 5: 'h4', 6: 'h4'}
MAPA_DE_ESTILOS = '\n'.join(
    [f"p.Heading{n} => {h}:fresh\np[style-name='Heading {n}'] => {h}:fresh\np[style-name='heading {n}'] => {h}:fresh" for n, h in NIVELES.items()]
    + ["p.Title => h2:fresh", "p[style-name='Title'] => h2:fresh", "p[style-name='Quote'] => blockquote > p:fresh",
       "p[style-name='Intense Quote'] => blockquote > p:fresh", 'u => u'])


def _fecha(valor):
    return valor.isoformat() if valor else None


def _dto(documento, *, con_contenido=False):
    dto = {'id': str(documento.pk), 'type': documento.tipo, 'version': documento.version, 'title': documento.titulo, 'state': documento.estado,
           'createdAt': _fecha(documento.creado_en), 'updatedAt': _fecha(documento.actualizado_en), 'publishedAt': _fecha(documento.publicado_en),
           'publishedBy': documento.publicado_por.email if documento.publicado_por_id else None, 'sha256': documento.contenido_sha256}
    if con_contenido:
        dto.update(content=documento.contenido, html=sanear_html(documento.contenido)[0])
    return dto


def _tipo(valor):
    if valor not in TIPOS:
        raise ValidationError('Tipo no válido')
    return valor


def _datos(version, titulo, contenido):
    if not isinstance(version, str) or not VERSION.match(version):
        raise ValidationError('Versión no válida')
    if not isinstance(titulo, str) or not 1 <= len(titulo.strip()) <= MAXIMO_TITULO or not titulo.isprintable():
        raise ValidationError('Título no válido')
    if not isinstance(contenido, str) or not contenido.strip() or len(contenido) > MAXIMO_CONTENIDO or '\x00' in contenido:
        raise ValidationError('Contenido no válido')
    return version, titulo.strip(), contenido


def _numerica(version):
    return tuple(int(parte) for parte in version.split('.'))


def por_tipo(actor, tipo):
    s.require_cap(actor, CAPACIDAD)
    consulta = DocumentoLegal.objects.select_related('publicado_por').filter(tipo=_tipo(tipo))
    publicadas = sorted(consulta.filter(estado='publicada'), key=lambda documento: documento.publicado_en, reverse=True)
    return {'status': 'ready', 'type': tipo, 'current': _dto(publicadas[0]) if publicadas else None,
            'drafts': [_dto(documento) for documento in consulta.filter(estado='borrador').order_by('-actualizado_en')],
            'history': [_dto(documento) for documento in publicadas]}


def _documento(documento_id, *, bloquear=False):
    consulta = DocumentoLegal.objects.select_related('publicado_por')
    documento = (consulta.select_for_update(of=('self',)) if bloquear else consulta).filter(pk=documento_id).first()
    if documento is None:
        raise Http404
    return documento


def detalle(actor, documento_id):
    s.require_cap(actor, CAPACIDAD)
    return {'status': 'ready', 'document': _dto(_documento(documento_id), con_contenido=True)}


def vista_previa(actor, contenido):
    s.require_cap(actor, CAPACIDAD)
    if not isinstance(contenido, str) or len(contenido) > MAXIMO_CONTENIDO or '\x00' in contenido:
        raise ValidationError('Contenido no válido')
    return {'status': 'ready', 'html': sanear_html(contenido)[0]}


def _no_docx():
    return ReglaDeNegocio('documento-no-docx', 'Sube un documento de Word guardado como .docx.')


def _ilegible():
    return ReglaDeNegocio('documento-ilegible', 'No se pudo leer el documento. Ábrelo en Word y guárdalo de nuevo como .docx.')


def _bytes_de_docx(archivo):
    if not archivo.name.lower().endswith('.docx'):
        raise _no_docx()
    if archivo.size > MAXIMO_ARCHIVO:
        raise ReglaDeNegocio('documento-grande', 'El documento pasa de 2 MB.')
    datos = archivo.read()
    if not datos.startswith(FIRMA_ZIP):
        raise _no_docx()
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as paquete:
            entradas = paquete.infolist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, EOFError):
        raise _ilegible() from None
    if (len(entradas) > MAXIMO_ENTRADAS or sum(entrada.file_size for entrada in entradas) > MAXIMO_DESCOMPRIMIDO
            or 'word/document.xml' not in {entrada.filename for entrada in entradas}):
        raise _ilegible()
    return datos


def _html_dentro_del_limite(html):
    if len(html) > MAXIMO_CONTENIDO:
        raise ReglaDeNegocio('documento-largo', 'El texto convertido pasa de 200 000 caracteres. Divide el documento.')
    return html


def importar_docx(actor, archivo):
    """Convierte un .docx a HTML saneado. El archivo no se guarda: el editor recibe el HTML y lo guarda el borrador."""
    usuario = s.require_cap(actor, CAPACIDAD)
    datos = _bytes_de_docx(archivo)
    try:
        resultado = mammoth.convert_to_html(io.BytesIO(datos), style_map=MAPA_DE_ESTILOS, include_embedded_style_map=False,
                                            external_file_access=False, convert_image=lambda imagen: [])
    # mammoth lee un archivo que no controlamos: cualquier fallo al interpretarlo es un documento ilegible.
    except Exception:
        raise _ilegible() from None
    html = _html_dentro_del_limite(sanear_html(resultado.value)[0])
    s.auditar(usuario, 'importar_documento_legal', entidad='documento_legal',
              detalle={'kb': -(-len(datos) // 1024), 'avisos_conversion': len(resultado.messages)})
    return {'status': 'ready', 'html': html}


def sanear_pegado(actor, archivo):
    """HTML del portapapeles saneado con la misma lista blanca. Llega como archivo para no chocar con el límite de JSON."""
    s.require_cap(actor, CAPACIDAD)
    if archivo.size > MAXIMO_PEGADO:
        raise ReglaDeNegocio('pegado-grande', 'Lo que pegaste pasa de 256 KB. Pégalo por partes o sube el .docx.')
    try:
        contenido = archivo.read().decode('utf-8')
    except UnicodeDecodeError:
        raise ValidationError('Texto no válido') from None
    return {'status': 'ready', 'html': _html_dentro_del_limite(sanear_html(contenido)[0])}


def _hash(contenido):
    return hashlib.sha256(contenido.encode()).hexdigest()


def _sin_repetir(tipo, version, excepto=None):
    repetidas = DocumentoLegal.objects.filter(tipo=tipo, version=version)
    if excepto is not None:
        repetidas = repetidas.exclude(pk=excepto)
    if repetidas.exists():
        raise ReglaDeNegocio('version-existente', 'Ya existe esa versión de este documento.')


@transaction.atomic
def crear(actor, tipo, version, titulo, contenido):
    usuario = s.require_cap(actor, CAPACIDAD)
    tipo = _tipo(tipo)
    version, titulo, contenido = _datos(version, titulo, contenido)
    _sin_repetir(tipo, version)
    documento = DocumentoLegal.objects.create(tipo=tipo, version=version, titulo=titulo, contenido=contenido, contenido_sha256=_hash(contenido), creado_por=usuario)
    s.auditar(usuario, 'crear_borrador_legal', entidad='documento_legal', entidad_id=documento.pk, detalle={'tipo': tipo, 'version': version})
    return {'status': 'accepted', 'document': _dto(_documento(documento.pk), con_contenido=True)}


def _borrador_vigente_en_pantalla(documento_id, esperado):
    documento = _documento(documento_id, bloquear=True)
    if documento.estado != 'borrador':
        raise ReglaDeNegocio('documento-publicado', 'Una versión publicada no se edita ni se borra: crea una nueva.')
    if esperado != _fecha(documento.actualizado_en):
        raise s.RegistroDesactualizado('El borrador cambió')
    return documento


@transaction.atomic
def editar(actor, documento_id, esperado, version, titulo, contenido):
    usuario = s.require_cap(actor, CAPACIDAD)
    documento = _borrador_vigente_en_pantalla(documento_id, esperado)
    version, titulo, contenido = _datos(version, titulo, contenido)
    _sin_repetir(documento.tipo, version, excepto=documento.pk)
    documento.version, documento.titulo, documento.contenido, documento.contenido_sha256 = version, titulo, contenido, _hash(contenido)
    documento.save(update_fields=['version', 'titulo', 'contenido', 'contenido_sha256'])
    s.auditar(usuario, 'editar_borrador_legal', entidad='documento_legal', entidad_id=documento.pk, detalle={'tipo': documento.tipo, 'version': version})
    return {'status': 'accepted', 'document': _dto(_documento(documento.pk), con_contenido=True)}


@transaction.atomic
def eliminar(actor, documento_id, esperado):
    usuario = s.require_cap(actor, CAPACIDAD)
    documento = _borrador_vigente_en_pantalla(documento_id, esperado)
    s.auditar(usuario, 'eliminar_borrador_legal', entidad='documento_legal', entidad_id=documento.pk, detalle={'tipo': documento.tipo, 'version': documento.version})
    documento.delete()
    return {'status': 'accepted'}


@transaction.atomic
def publicar(actor, documento_id, esperado):
    usuario = s.require_cap(actor, CAPACIDAD)
    documento = _borrador_vigente_en_pantalla(documento_id, esperado)
    ultimas = [_numerica(otra.version) for otra in DocumentoLegal.objects.filter(tipo=documento.tipo, estado='publicada')]
    if ultimas and _numerica(documento.version) <= max(ultimas):
        raise ReglaDeNegocio('version-no-mayor', 'La versión debe ser mayor que la vigente.')
    documento.estado = 'publicada'
    documento.save(update_fields=['estado'])
    s.auditar(usuario, 'publicar_legal', entidad='documento_legal', entidad_id=documento.pk, detalle={'tipo': documento.tipo, 'version': documento.version})
    avisadas = get_user_model().objects.filter(is_active=True, anonimizada_en__isnull=True).count()
    return {'status': 'accepted', 'document': _dto(_documento(documento.pk)), 'notified': avisadas}
