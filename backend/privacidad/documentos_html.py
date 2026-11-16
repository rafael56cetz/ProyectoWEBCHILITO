"""Fragmentos legales: solo texto, formato básico, tablas y enlaces sin contenido activo."""
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit


ETIQUETAS = {'p', 'h2', 'h3', 'h4', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'br', 'a', 'blockquote',
             'table', 'thead', 'tbody', 'tr', 'th', 'td'}
# La página ya tiene su h1 y el texto usa tres niveles; Word marca la negrita y la cursiva con b e i.
EQUIVALENTES = {'h1': 'h2', 'h5': 'h4', 'h6': 'h4', 'b': 'strong', 'i': 'em'}
OMITIR = {'script', 'style', 'head', 'title', 'xml', 'iframe', 'object', 'embed', 'svg', 'math', 'template', 'noscript'}
VACIAS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
BLOQUES = {'p', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'blockquote', 'table', 'tr'}
TITULOS = {'h2', 'h3', 'h4'}
REL = 'noopener noreferrer nofollow'


def _enlace_seguro(valor):
    if not valor or '\\' in valor or any(ord(caracter) <= 32 or ord(caracter) == 127 for caracter in valor):
        return False
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
        self.condicionales = 0

    def unknown_decl(self, declaracion):
        # Word pega `<![if !supportLists]>…<![endif]>` con viñetas e imágenes de respaldo: no son texto del documento.
        if declaracion.startswith('if'):
            self.condicionales += 1
        elif declaracion.startswith('endif') and self.condicionales:
            self.condicionales -= 1

    def handle_starttag(self, etiqueta, atributos):
        if self.omitidas:
            if etiqueta not in VACIAS:
                self.omitidas.append(etiqueta)
            return
        if etiqueta in OMITIR:
            if etiqueta not in VACIAS:
                self.omitidas.append(etiqueta)
            return
        salida = EQUIVALENTES.get(etiqueta, etiqueta)
        if salida not in ETIQUETAS or self.condicionales:
            return
        enlace = next((valor for nombre, valor in atributos if nombre == 'href'), None)
        atributo = f' href="{escape(enlace, quote=True)}" rel="{REL}"' if salida == 'a' and _enlace_seguro(enlace) else ''
        self.html.append(f'<{salida}{atributo}>')
        if salida in BLOQUES:
            self.texto.append('\n\n')
            if salida in TITULOS:
                self.texto.append('## ')
            elif salida == 'li':
                self.texto.append('• ')
        elif salida in {'th', 'td'}:
            self.texto.append(' ')
        if salida == 'br':
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
            _, salida = self.abiertas.pop()
            self.html.append(f'</{salida}>')
            if salida in BLOQUES:
                self.texto.append('\n\n')

    def handle_data(self, texto):
        if not self.omitidas and not self.condicionales:
            self.html.append(escape(texto))
            self.texto.append(texto)


def sanear_html(contenido):
    """Devuelve HTML limitado y texto compatible con el cliente anterior.

    Los atributos se eliminan salvo href seguro, que lleva rel. Los comentarios, las secciones
    condicionales de Word y el contenido activo no llegan a la respuesta; nunca se interpreta código del documento.
    """
    fragmento = _FragmentoLegal()
    fragmento.feed(contenido)
    fragmento.close()
    while fragmento.abiertas:
        _, salida = fragmento.abiertas.pop()
        fragmento.html.append(f'</{salida}>')
    texto = '\n\n'.join(bloque.strip() for bloque in ''.join(fragmento.texto).split('\n\n') if bloque.strip())
    return ''.join(fragmento.html), texto
