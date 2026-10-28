from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("cuentas", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="CuotaAcceso",
            fields=[
                ("cache_key", models.CharField(max_length=255, primary_key=True, serialize=False)),
                ("value", models.TextField()),
                ("expires", models.DateTimeField(db_index=True)),
            ],
            options={"db_table": "cuentas_cuotas_acceso"},
        ),
    ]
