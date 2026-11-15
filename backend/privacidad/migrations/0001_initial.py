# Preparado offline con Django 5.2.18; hora de generación: 2026-11-05 07:14

import django.core.validators
import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentoVersion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tipo', models.CharField(choices=[('aviso_privacidad', 'Aviso de privacidad'), ('terminos', 'Términos')], max_length=16)),
                ('version', models.CharField(max_length=64)),
                ('contenido_ref', models.CharField(max_length=255)),
                ('contenido_sha256', models.CharField(max_length=64, validators=[django.core.validators.RegexValidator('^[0-9a-f]{64}$')])),
                ('registrado_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, editable=False)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('tipo', 'version'), name='priv_documento_version_unica'), models.CheckConstraint(condition=models.Q(('tipo__in', ['aviso_privacidad', 'terminos'])), name='priv_documento_tipo_valido'), models.CheckConstraint(condition=models.Q(('version__regex', '\\S')), name='priv_documento_version_texto'), models.CheckConstraint(condition=models.Q(('contenido_ref__regex', '\\S')), name='priv_documento_ref_texto'), models.CheckConstraint(condition=models.Q(('contenido_sha256__regex', '^[0-9a-f]{64}$')), name='priv_documento_hash_valido')],
            },
        ),
        migrations.CreateModel(
            name='FinalidadOpcional',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('codigo', models.CharField(max_length=64, unique=True, validators=[django.core.validators.RegexValidator('^[a-z][a-z0-9_]{0,63}$')])),
                ('descripcion', models.CharField(max_length=255)),
                ('creada_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, editable=False)),
            ],
            options={
                'constraints': [models.CheckConstraint(condition=models.Q(('codigo__regex', '^[a-z][a-z0-9_]{0,63}$')), name='priv_finalidad_codigo_valido'), models.CheckConstraint(condition=models.Q(('descripcion__regex', '\\S')), name='priv_finalidad_descripcion_texto')],
            },
        ),
        migrations.CreateModel(
            name='SujetoPrivacidad',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('creado_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, editable=False)),
                ('usuario', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sujeto_privacidad', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DecisionPrivacidad',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('acto', models.CharField(choices=[('lectura_aviso', 'lectura_aviso'), ('aceptacion_terminos', 'aceptacion_terminos'), ('consentimiento', 'consentimiento')], max_length=20)),
                ('decision', models.BooleanField()),
                ('registrada_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, editable=False)),
                ('documento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='privacidad.documentoversion')),
                ('finalidad', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='privacidad.finalidadopcional')),
                ('sujeto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='privacidad.sujetoprivacidad')),
            ],
        ),
        migrations.CreateModel(
            name='PreferenciaFinalidad',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('actualizada_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, editable=False)),
                ('decision', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='privacidad.decisionprivacidad')),
                ('finalidad', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='privacidad.finalidadopcional')),
                ('sujeto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='privacidad.sujetoprivacidad')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('sujeto', 'finalidad'), name='priv_preferencia_unica')],
            },
        ),
        migrations.CreateModel(
            name='EventoPrivacidad',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('accion', models.CharField(choices=[('decision', 'decision'), ('rectificacion', 'rectificacion'), ('oposicion', 'oposicion')], max_length=16)),
                ('resultado', models.CharField(choices=[('completado', 'completado'), ('rechazado', 'rechazado')], max_length=12)),
                ('campo', models.CharField(blank=True, choices=[('', 'No aplica'), ('first_name', 'Nombre'), ('last_name', 'Apellido')], default='', max_length=10)),
                ('creado_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, editable=False)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('decision', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='privacidad.decisionprivacidad')),
                ('finalidad', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='privacidad.finalidadopcional')),
                ('sujeto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='privacidad.sujetoprivacidad')),
            ],
            options={
                'indexes': [models.Index(fields=['sujeto', '-creado_en'], name='priv_evento_historial_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('resultado__in', ['completado', 'rechazado'])), name='priv_evento_resultado_valido'), models.CheckConstraint(condition=models.Q(models.Q(('accion', 'rectificacion'), ('actor__isnull', False), ('campo__in', ['first_name', 'last_name']), ('decision__isnull', True), ('finalidad__isnull', True)), models.Q(('accion', 'decision'), ('campo', ''), ('decision__isnull', False)), models.Q(('accion', 'oposicion'), ('actor__isnull', False), ('campo', ''), ('decision__isnull', False), ('finalidad__isnull', False)), _connector='OR'), name='priv_evento_referencias_validas')],
            },
        ),
        migrations.AddIndex(
            model_name='decisionprivacidad',
            index=models.Index(fields=['sujeto', 'finalidad', '-registrada_en'], name='priv_decision_historial_idx'),
        ),
        migrations.AddConstraint(
            model_name='decisionprivacidad',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('acto', 'consentimiento'), ('finalidad__isnull', False)), models.Q(('acto__in', ['lectura_aviso', 'aceptacion_terminos']), ('finalidad__isnull', True)), _connector='OR'), name='priv_decision_acto_finalidad'),
        ),
    ]
