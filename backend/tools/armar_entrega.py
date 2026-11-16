"""Genera la copia limpia para la nube a partir de esta carpeta, que sigue siendo el original.

Copia solo lo incluido en la lista y después comprueba que no se coló nada. No muestra valores.
Uso: python backend/tools/armar_entrega.py [destino]
"""
import fnmatch
import re
import shutil
import sys
from pathlib import Path

from correo_config import load_smtp_file
from entorno_local import RAIZ, leer

MARCA = '.generado-por-armar-entrega'
DESTINO = RAIZ.parent / 'el-chilito-nube'
INCLUIR = ['COMO-ENCENDER-EL-SERVIDOR.md', '.env.example', '.gitignore',
           'backend/manage.py', 'backend/requirements-lock.txt', 'backend/config', 'backend/cuentas', 'backend/datos',
           'backend/huerto', 'backend/privacidad', 'backend/tests', 'backend/web',
           'frontend/index.html', 'frontend/favicon.svg', 'frontend/controladores', 'frontend/modelos', 'frontend/vistas',
           'frontend/pruebas',
           *[f'backend/tools/{n}.py' for n in ('__init__', 'servir_local', 'entorno_local',
                                                'configurar_correo', 'correo_config', 'soporte_local')]]
EXCLUIR = ['*/__pycache__/*', '*.pyc']
PROHIBIDOS = ['.env', 'CLAUDE.md', 'README.md', 'armar_entrega.py', 'simular_equipo.py', 'pruebas_local.py', 'probar_seguridad.py', 'probar_mfa.py',
              'probar_privacidad.py', 'probar_correo.py', 'destino_temporal.py']
PATRONES = {'clave privada': rb'-----BEGIN [A-Z ]*PRIVATE KEY', 'token Google': rb'AIza[0-9A-Za-z_-]{30,}', 'token GitHub': rb'gh[pousr]_[A-Za-z0-9]{30,}',
            'clave AWS': rb'AKIA[0-9A-Z]{16}', 'cadena de conexión': rb'postgres(?:ql)?://[^\s\'"]+:[^\s\'"@]+@'}


def excluido(relativa):
    return any(fnmatch.fnmatch(relativa, patron) for patron in EXCLUIR)


def preparar(destino):
    if RAIZ == destino or RAIZ in destino.parents:
        sys.exit('El destino debe estar fuera de esta carpeta')
    if destino.exists():
        if not (destino / MARCA).is_file():
            sys.exit('El destino existe y no lo creó esta herramienta')
        for hijo in destino.iterdir():
            if hijo.name != '.git':     # el historial de la copia se conserva
                shutil.rmtree(hijo) if hijo.is_dir() else hijo.unlink()
    destino.mkdir(parents=True, exist_ok=True)
    (destino / MARCA).write_text('Copia generada desde web-integracion. No editar aquí.\n')


def copiar(destino):
    total = 0
    for patron in INCLUIR:
        coincidencias = list(RAIZ.glob(patron))
        if not coincidencias:
            sys.exit(f'Falta en el original: {patron}')
        for origen in coincidencias:
            for archivo in ([origen] if origen.is_file() else [p for p in origen.rglob('*') if p.is_file()]):
                relativa = archivo.relative_to(RAIZ).as_posix()
                if not excluido(relativa):
                    (destino / relativa).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(archivo, destino / relativa)
                    total += 1
    return total


def valores_sensibles():
    """Valores reales que no deben aparecer: claves, contraseñas y direcciones."""
    valores = {}
    if (RAIZ / '.env').is_file():
        valores.update(leer('.env'))
    ruta = leer('.env').get('CHILITO_SMTP_CONFIG') if (RAIZ / '.env').is_file() else None
    if ruta:
        valores.update({f'smtp:{k}': v for k, v in load_smtp_file(ruta).items()})
    claves = ('KEY', 'PASSWORD', 'SMTP_USER', 'CONTACTO', 'FROM_EMAIL', 'ALLOWED_RECIPIENTS')
    return {v.encode() for k, v in valores.items() if any(c in k for c in claves) and len(v) >= 6 and 'example.test' not in v}


def verificar(destino):
    archivos = [p for p in destino.rglob('*') if p.is_file() and '.git' not in p.relative_to(destino).parts]
    problemas = [f'{p.relative_to(destino)}: archivo prohibido' for p in archivos if p.name in PROHIBIDOS]
    problemas += [f'{p.relative_to(destino)}: caché' for p in archivos if '__pycache__' in p.parts or p.suffix == '.pyc']
    problemas += [str(p.relative_to(destino)) + ': carpeta prohibida' for p in destino.rglob('.claude')]
    sensibles = valores_sensibles()
    for archivo in archivos:
        contenido = archivo.read_bytes()
        if any(valor in contenido for valor in sensibles):
            problemas.append(f'{archivo.relative_to(destino)}: contiene un valor real de un .env')
        problemas += [f'{archivo.relative_to(destino)}: {tipo}' for tipo, patron in PATRONES.items() if re.search(patron, contenido)]
    print(f'Archivos: {len(archivos)}. Valores reales comparados: {len(sensibles)}. Problemas: {len(problemas)}.')
    for problema in problemas:
        print('  ' + problema)
    return not problemas


if __name__ == '__main__':
    destino = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else DESTINO
    preparar(destino)
    print(f'Copiados: {copiar(destino)} en {destino}')
    sys.exit(0 if verificar(destino) else 1)
