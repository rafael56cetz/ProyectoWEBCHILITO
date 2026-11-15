"""Paginación de consultas ya autorizadas: cuenta y recorta en la base (LIMIT/OFFSET) antes de crear diccionarios.

La lectura y validación del parámetro `page` sigue en la capa HTTP (`web/api.py`)."""

from django.db import connection

TAMANO_PAGINA = 25


def paginar_sql(columnas, origen, orden, parametros, pagina, adaptador=lambda fila: fila, tamano=TAMANO_PAGINA):
    """Pagina un SELECT sobre vistas. `columnas`, `origen` y `orden` son texto fijo del código; todo valor de la persona
    entra por `parametros`. Devuelve las filas como diccionarios."""
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT count(*) FROM {origen}', parametros)
        total = cursor.fetchone()[0]
        cursor.execute(f'SELECT {columnas} FROM {origen} ORDER BY {orden} LIMIT %s OFFSET %s', [*parametros, tamano, (pagina - 1) * tamano])
        nombres = [columna.name for columna in cursor.description]
        filas = [dict(zip(nombres, fila)) for fila in cursor.fetchall()]
    return {'items': [adaptador(fila) for fila in filas], 'page': pagina, 'total': total}


def paginar(consulta, pagina, adaptador=lambda fila: fila, tamano=TAMANO_PAGINA):
    total = consulta.count()
    inicio = (pagina - 1) * tamano
    return {'items': [adaptador(fila) for fila in consulta[inicio:inicio + tamano]],
            'page': pagina, 'total': total}
