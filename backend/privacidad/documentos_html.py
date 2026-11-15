"""Fragmentos legales: solo texto, formato básico y enlaces sin contenido activo."""
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit


ETIQUETAS = {'p', 'h2', 'h3', 'strong', 'em', 'ul', 'ol', 'li', 'br', 'a'}
OMITIR = {'script', 'style', 'head', 'h1', 'iframe', 'object', 'embed', 'svg', 'math', 'template', 'noscript'}
VACIAS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
BLOQUES = {'p', 'h2', 'h3', 'ul', 'ol', 'li'}


def _enlace_seguro(valor):
    if not valor or '\\' in valor or any(ord(caracter) <= 32 or ord(caracter) == 127 for caracter in valor):
        return False
    if valor.startswith('#') or (valor.startswith('/') and not valor.startswith('//')):
        return True
    try:
        partes = urlsplit(valor)
    except ValueError:
        return False
    return ((partes.scheme in {'http', 'https'} and bool(partes.netloc))
            or (partes.scheme == 'mailto' and bool(partes.path)))


class _FragmentoLegal(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html = []
        self.texto = []
        self.abiertas = []
        self.omitidas = []

    def handle_starttag(self, etiqueta, atributos):
        if self.omitidas:
            if etiqueta not in VACIAS:
                self.omitidas.append(etiqueta)
            return
        if etiqueta in OMITIR:
            if etiqueta not in VACIAS:
                self.omitidas.append(etiqueta)
            return
        if etiqueta not in ETIQUETAS:
            return
        # Las secciones conservan el h3 y los estilos de la vista anterior.
        salida = 'h3' if etiqueta == 'h2' else etiqueta
        enlace = next((valor for nombre, valor in atributos if nombre == 'href'), None)
        atributo = f' href="{escape(enlace, quote=True)}"' if etiqueta == 'a' and _enlace_seguro(enlace) else ''
        self.html.append(f'<{salida}{atributo}>')
        if etiqueta in BLOQUES:
            self.texto.append('\n\n')
            if etiqueta in {'h2', 'h3'}:
                self.texto.append('## ')
            elif etiqueta == 'li':
                self.texto.append('• ')
        if etiqueta == 'br':
            self.texto.append('\n')
        else:
            self.abiertas.append((etiqueta, salida))

    def handle_endtag(self, etiqueta):
        if self.omitidas:
            if etiqueta in self.omitidas:
                indice = len(self.omitidas) - 1 - self.omitidas[::-1].index(etiqueta)
                del self.omitidas[indice:]
            return
        coincidencias = [indice for indice, (origen, _) in enumerate(self.abiertas) if origen == etiqueta]
        if not coincidencias:
            return
        while len(self.abiertas) > coincidencias[-1]:
            origen, salida = self.abiertas.pop()
            self.html.append(f'</{salida}>')
            if origen in BLOQUES:
                self.texto.append('\n\n')

    def handle_data(self, texto):
        if not self.omitidas:
            self.html.append(escape(texto))
            self.texto.append(texto)


def sanear_html(contenido):
    """Devuelve HTML limitado y texto compatible con el cliente anterior.

    Los atributos se eliminan salvo href seguro. Los comentarios y el contenido
    activo no llegan a la respuesta; nunca se interpreta código del documento.
    """
    fragmento = _FragmentoLegal()
    fragmento.feed(contenido)
    fragmento.close()
    while fragmento.abiertas:
        _, salida = fragmento.abiertas.pop()
        fragmento.html.append(f'</{salida}>')
    texto = '\n\n'.join(bloque.strip() for bloque in ''.join(fragmento.texto).split('\n\n') if bloque.strip())
    return ''.join(fragmento.html), texto
