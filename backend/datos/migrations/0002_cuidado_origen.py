"""Estado de Django para el origen de los cuidados. No ejecuta SQL: la columna, sus reglas y el registrado_por
opcional (solo para las recargas del equipo) los crea la migración web.0004_deposito_flotador."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('datos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.AddField(model_name='cuidado', name='origen',
                                field=models.CharField(db_default='persona', max_length=7)),
            migrations.AlterField(model_name='cuidado', name='registrado_por',
                                  field=models.ForeignKey(db_index=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                                          related_name='+', to=settings.AUTH_USER_MODEL)),
        ]),
    ]
