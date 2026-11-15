"""Compara localhost:8780 con este frontend, sin sesión, Django ni base de datos.

Uso, en la terminal del equipo donde se abre la aplicación: python3 backend/tools/comprobar_frontend_local.py
Solo hace GET de index.html y de sus scripts y estilos. No muestra cuerpos, cookies ni datos de cuentas, no sigue redirecciones ni usa proxies del entorno.
Que coincida acredita los archivos servidos; la cuenta real se comprueba aparte, en el navegador. El número de archivos se calcula desde index.html."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener


FRONTEND = Path(__file__).resolve().parents[2] / 'frontend'
ORIGEN = 'http://localhost:8780'


class Referencias(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('src'):
            self.urls.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet' and attrs.get('href'):
            self.urls.append(attrs['href'])


class SinRedirecciones(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def comparar(recurso):
    url, archivo = recurso
    esperado = archivo.read_bytes()
    resultado = {'archivo': url}
    try:
        cliente = build_opener(ProxyHandler({}), SinRedirecciones())
        with cliente.open(ORIGEN + url, timeout=5) as respuesta:
            # Un byte adicional basta para detectar también un archivo más largo.
            servido = respuesta.read(len(esperado) + 1)
            resultado.update(http=respuesta.status, coincide=servido == esperado)
            if servido == esperado:
                resultado['sha256'] = hashlib.sha256(esperado).hexdigest()
    except HTTPError as error:
        resultado.update(http=error.code, coincide=False)
    except (URLError, OSError, TimeoutError) as error:
        razon = getattr(error, 'reason', error)
        resultado.update(error=type(razon).__name__, errno=getattr(razon, 'errno', None))
    return resultado


def main():
    inicio = comparar(('/', FRONTEND / 'index.html'))
    if inicio.get('http') != 200:
        print(json.dumps({'estado': 'no_comprobado', 'origen': ORIGEN, 'detalle': inicio}, ensure_ascii=False))
        return 2
    referencias = Referencias()
    referencias.feed((FRONTEND / 'index.html').read_text(encoding='utf-8'))
    recursos = []
    for url in dict.fromkeys(referencias.urls):
        partes = urlsplit(url)
        archivo = (FRONTEND / partes.path.lstrip('/')).resolve()
        if partes.scheme or partes.netloc or FRONTEND.resolve() not in archivo.parents or not archivo.is_file():
            print(json.dumps({'estado': 'referencia_local_invalida'}, ensure_ascii=False))
            return 1
        recursos.append(('/' + url.lstrip('/'), archivo))
    with ThreadPoolExecutor(max_workers=4) as consultas:
        resultados = [inicio, *consultas.map(comparar, recursos)]
    problemas = [r for r in resultados if not r.get('coincide')]
    print(json.dumps({
        'estado': 'coincide' if not problemas else 'revisar',
        'origen': ORIGEN,
        'archivos_comprobados': len(resultados),
        'archivos_identicos': len(resultados) - len(problemas),
        'index_sha256': inicio.get('sha256'),
        'problemas': problemas,
        'sesion': 'no_consultada',
    }, ensure_ascii=False, indent=2))
    return 1 if problemas else 0


if __name__ == '__main__':
    raise SystemExit(main())
