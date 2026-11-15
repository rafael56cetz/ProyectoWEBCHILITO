"""Paginación de consultas ya autorizadas: cuenta y recorta en la base (LIMIT/OFFSET) antes de crear diccionarios.

La lectura y validación del parámetro `page` sigue en la capa HTTP (`web/api.py`)."""

TAMANO_PAGINA = 25


def paginar(consulta, pagina, adaptador=lambda fila: fila, tamano=TAMANO_PAGINA):
    total = consulta.count()
    inicio = (pagina - 1) * tamano
    return {'items': [adaptador(fila) for fila in consulta[inicio:inicio + tamano]],
            'page': pagina, 'total': total}
