"""Tablas de ciclos de planta y de recomendaciones ya avisadas, y el ciclo de cada etapa de la línea de vida. Sus reglas, el ciclo 1 de las plantas existentes, los privilegios y las recomendaciones
los añade web.0007_ciclos_planta."""
import django.db.models.deletion
import django.db.models.expressions
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('huerto', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlantaCiclo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('planta', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='huerto.planta')),
                ('numero', models.SmallIntegerField()),
                ('inicio', models.DateTimeField()),
                ('fin', models.DateTimeField(null=True)),
                ('motivo', models.CharField(max_length=16, null=True)),
                ('nota', models.CharField(db_default='', max_length=500)),
                ('cerrado_por', models.ForeignKey(db_index=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'planta_ciclo',
                'default_permissions': (),
                'constraints': [models.UniqueConstraint(fields=('planta', 'numero'), name='ciclo_numero_unico')],
            },
        ),
        migrations.CreateModel(
            name='PlantaRecomendacion',
            fields=[
                ('pk', models.CompositePrimaryKey('ciclo', 'situacion', blank=True, editable=False, primary_key=True, serialize=False)),
                ('ciclo', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='huerto.plantaciclo')),
                ('situacion', models.CharField(max_length=20)),
                ('creada_en', models.DateTimeField(db_default=django.db.models.expressions.RawSQL('now()', [], output_field=models.DateTimeField()))),
            ],
            options={'db_table': 'planta_recomendacion', 'default_permissions': ()},
        ),
        # El ciclo de cada etapa de la línea de vida: web.0007 lo rellena, lo hace NOT NULL y lo fija al insertar.
        migrations.AddField(
            model_name='plantaetapa',
            name='ciclo',
            field=models.ForeignKey(db_index=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='huerto.plantaciclo'),
        ),
    ]
