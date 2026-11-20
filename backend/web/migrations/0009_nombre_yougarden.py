"""El proyecto cambia de nombre: «El Chilito» pasa a ser «YouGarden» en el texto de las guías de cuidado ya publicadas
(por ejemplo, «¿Cuándo termina el ciclo de mi habanero?», de web.0007).

Solo cambia texto visible. Los identificadores técnicos (tablas y funciones chilito_*, roles chilito_pkg_*) no cambian.
Igual que en web.0007, el trigger de guías exige un admin con «gestionar_guias», que en una migración no existe, así que
se suspende solo durante el UPDATE. La reversión hace el reemplazo inverso.
"""
from django.db import migrations


def _reemplazar(schema_editor, antes, despues):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('ALTER TABLE guia_cuidado DISABLE TRIGGER guia_reglas')
        cursor.execute('UPDATE guia_cuidado SET pregunta = replace(pregunta, %s, %s), respuesta = replace(respuesta, %s, %s) '
                       'WHERE pregunta LIKE %s OR respuesta LIKE %s', [antes, despues, antes, despues, f'%{antes}%', f'%{antes}%'])
        # Las llaves foráneas diferidas dejan eventos pendientes que impiden el ALTER TABLE: se comprueban ya.
        cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        cursor.execute('ALTER TABLE guia_cuidado ENABLE TRIGGER guia_reglas')
        cursor.execute('SET CONSTRAINTS ALL DEFERRED')


def a_yougarden(apps, schema_editor):
    _reemplazar(schema_editor, 'El Chilito', 'YouGarden')


def a_el_chilito(apps, schema_editor):
    _reemplazar(schema_editor, 'YouGarden', 'El Chilito')


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0008_arranque_legal'),
    ]

    operations = [
        migrations.RunPython(a_yougarden, a_el_chilito),
    ]
