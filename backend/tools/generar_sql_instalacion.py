"""Genera sql/instalacion/03_esquema_completo.sql desde las migraciones, sin conectarse.

Reproduce cada migración en orden para que el script y `migrate` no se contradigan.
Se ejecuta otra vez cada vez que cambia una migración o sql/privilegios.sql.
"""
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.testing')
os.environ.setdefault('CHILITO_ENV', 'testing')
os.environ.setdefault('CHILITO_DJANGO_KEY', 'solo-generacion-sin-valor-real-0000000')
os.environ.setdefault('CHILITO_SUPPORT_KEY', 'solo-generacion-sin-valor-real-0000001')
os.environ.setdefault('CHILITO_VINCULACION_SECRETO', 'solo-generacion-sin-valor-real-0000002')

import django
from django.db import connections


def desconectado(*args, **kwargs):
    raise RuntimeError('La generación no puede conectarse a PostgreSQL.')


for conexion in connections.all():
    conexion.ensure_connection = desconectado
django.setup()

from django.apps import apps
from django.contrib.auth.management import _get_all_permissions
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from psycopg.sql import Literal

BASE = 'chilito_integracion_sinteticos'
RAIZ = BACKEND.parent
# Operaciones Python del historial: migran filas existentes y en una base vacía no hacen nada.
SIN_EFECTO_EN_BASE_VACIA = {
    ('account', '0006_emailaddress_lower'),
    ('account', '0008_emailaddress_unique_primary_email_fixup'),
    ('auth', '0011_update_proxy_permissions'),
    ('contenttypes', '0002_remove_content_type_name'),
}
GUARDA = f"""DO $$ BEGIN
 IF current_database() <> '{BASE}'
 OR current_user <> 'chilito_pkg_owner'
 OR session_user <> 'chilito_pkg_owner'
 OR (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) <> 'chilito_pkg_owner'
 THEN RAISE EXCEPTION 'Conectarse a la base {BASE} como chilito_pkg_owner'; END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 17
 THEN RAISE EXCEPTION 'Este script se prepara para PostgreSQL 17'; END IF;
 IF EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public')
 THEN RAISE EXCEPTION 'La base no está vacía; este script no actualiza una base existente'; END IF;
END $$;
"""


def literal(valor):
    return "'" + str(valor).replace("'", "''") + "'"


def compilar(sql, params):
    # Solo DDL generado por Django, nunca entrada de una petición.
    return sql % tuple(Literal(valor).as_string() for valor in params) if params else sql


def resolver_nombres(editor, previo):
    """Sustituye la consulta a la base: el nombre se lee del SQL ya generado.

    En una base recién creada cada restricción tiene el nombre que le dio esa
    sentencia. Si no aparece exactamente uno, se detiene en vez de suponerlo.
    """
    def resolver(model, column_names=None, **filtros):
        tabla = model._meta.db_table
        columnas = ', '.join(f'"{c}"' for c in column_names)
        tipo = 'FOREIGN KEY' if filtros.get('foreign_key') else 'UNIQUE'
        texto = '\n'.join(previo)
        hallados = re.findall(rf'ALTER TABLE "{tabla}" ADD CONSTRAINT "([^"]+)" {tipo} \({re.escape(columnas)}\)', texto)
        if not hallados and tipo == 'UNIQUE' and len(column_names) == 1:
            creacion = re.search(rf'CREATE TABLE "{tabla}" \((.*)\);', texto)
            if creacion and re.search(rf'"{column_names[0]}" [^,]* UNIQUE', creacion.group(1)):
                hallados = [f'{tabla}_{column_names[0]}_key']
        if len(hallados) != 1:
            raise RuntimeError(f'Restricción no resuelta: {tabla} {column_names} {filtros}: {hallados}')
        return hallados

    editor._constraint_names = resolver


def orden_de_migraciones(loader):
    orden = []
    for hoja in sorted(loader.graph.leaf_nodes()):
        for nodo in loader.graph.forwards_plan(hoja):
            if nodo not in orden:
                orden.append(nodo)
    return orden


def ddl_de_migraciones(loader, orden):
    estado = loader.project_state([])
    textos, previo = [], []
    for nodo in orden:
        migracion = loader.disk_migrations[nodo]
        with connection.schema_editor(collect_sql=True, atomic=False) as editor:
            resolver_nombres(editor, previo)
            estado = migracion.apply(estado, editor, collect_sql=True)
        lineas = [t for t in editor.collected_sql if t.strip()]
        previo.extend(lineas)
        sin_sql = [t for t in lineas if 'THIS OPERATION CANNOT BE WRITTEN AS SQL' in t]
        if sin_sql and nodo not in SIN_EFECTO_EN_BASE_VACIA:
            raise RuntimeError(f'{nodo} tiene operaciones que no se pueden escribir como SQL')
        textos.append(f'-- Migración {nodo[0]}.{nodo[1]}\n' + '\n'.join(lineas))
    return textos


def tabla_de_migraciones():
    with connection.schema_editor(collect_sql=True, atomic=False) as editor:
        editor.create_model(MigrationRecorder.Migration)
    return '\n'.join(editor.collected_sql)


def tipos_y_permisos():
    """Lo que Django crea en post_migrate, necesario para las capacidades."""
    tipos, permisos = [], []
    for config in apps.get_app_configs():
        for modelo in config.get_models():
            opts = modelo._meta
            app, nombre = literal(opts.app_label), literal(opts.model_name)
            tipos.append(f'({app},{nombre})')
            for codigo, texto in _get_all_permissions(opts):
                permisos.append(
                    f'INSERT INTO public.auth_permission(name,content_type_id,codename) '
                    f'SELECT {literal(texto)},id,{literal(codigo)} FROM public.django_content_type '
                    f'WHERE app_label={app} AND model={nombre};')
    return ('INSERT INTO public.django_content_type(app_label,model) VALUES\n'
            + ',\n'.join(tipos) + ';\n' + '\n'.join(permisos))


def registro_de_migraciones(orden):
    filas = ',\n'.join(f'({literal(a)},{literal(n)},now())' for a, n in orden)
    return f'INSERT INTO public.django_migrations(app,name,applied) VALUES\n{filas};'


def privilegios():
    texto = (RAIZ / 'sql' / 'privilegios.sql').read_text()
    texto = texto.replace(':"db_name"', f'"{BASE}"')
    lineas = [l for l in texto.splitlines() if l.strip() not in ('BEGIN;', 'COMMIT;')]
    return '\n'.join(lineas)


def main():
    connection.ops.compose_sql = compilar
    loader = MigrationLoader(None)
    orden = orden_de_migraciones(loader)
    partes = [
        '-- GENERADO por backend/tools/generar_sql_instalacion.py. No editar a mano.\n'
        f'-- Base {BASE} vacía, Query Tool de pgAdmin, como chilito_pkg_owner.\n'
        f'-- Incluye {len(orden)} migraciones, tipos y permisos de Django, y privilegios.\n'
        '-- No contiene contraseñas ni cuentas. Si falla, se revierte todo.',
        'BEGIN;',
        GUARDA,
        tabla_de_migraciones(),
        *ddl_de_migraciones(loader, orden),
        '-- Tipos de contenido y permisos (post_migrate de Django)',
        tipos_y_permisos(),
        '-- Registro para que Django reconozca las migraciones como aplicadas',
        registro_de_migraciones(orden),
        '-- Privilegios: copia de sql/privilegios.sql',
        privilegios(),
        'COMMIT;',
    ]
    salida = RAIZ / 'sql' / 'instalacion' / '03_esquema_completo.sql'
    salida.parent.mkdir(exist_ok=True)
    salida.write_text('\n\n'.join(partes) + '\n')
    print(f'{salida.relative_to(RAIZ)}: {len(orden)} migraciones, sin conexión.')


if __name__ == '__main__':
    main()
