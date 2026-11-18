"""Estado de Django para las recargas detectadas por el flotador. No ejecuta SQL: la tabla deposito_deteccion,
sus reglas y sus privilegios los crea la migración web.0005_recarga_por_confirmar."""
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('datos', '0002_cuidado_origen'),
        ('huerto', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.CreateModel(
                name='DepositoDeteccion',
                fields=[
                    ('id', models.UUIDField(db_default=models.Func(function='gen_random_uuid'), default=uuid.uuid4, editable=False,
                                            primary_key=True, serialize=False)),
                    ('detectada_en', models.DateTimeField()),
                    ('estado', models.CharField(db_default='pendiente', max_length=13)),
                    ('decidida_en', models.DateTimeField(null=True)),
                    ('cuidado', models.ForeignKey(db_index=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                                  related_name='+', to='datos.cuidado')),
                    ('decidida_por', models.ForeignKey(db_index=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                                       related_name='+', to=settings.AUTH_USER_MODEL)),
                    ('huerto', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.DO_NOTHING,
                                                 related_name='+', to='huerto.huerto')),
                ],
                options={'db_table': 'deposito_deteccion', 'abstract': False, 'default_permissions': ()},
            ),
        ]),
    ]
