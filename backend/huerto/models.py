from django.conf import settings
from django.db import models
from web.models import AHORA


class Huerto(models.Model):
    """Un huerto lo crea la propia persona. No se borra: se archiva."""
    propietario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    nombre = models.CharField(max_length=60, db_default="Mi huerto")
    zona_horaria = models.CharField(max_length=64, db_default="America/Merida")
    estado = models.CharField(max_length=10, db_default="activo")
    creado_en = models.DateTimeField(db_default=AHORA)
    archivado_en = models.DateTimeField(null=True)

    class Meta:
        db_table = "huerto"
        default_permissions = ()


class Planta(models.Model):
    """Las 3 plantas de cada huerto; las crea un trigger al crear el huerto."""
    huerto = models.ForeignKey(Huerto, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    numero = models.SmallIntegerField()
    nombre = models.CharField(max_length=40)
    fecha_siembra = models.DateField(null=True)
    etapa = models.CharField(max_length=16, db_default="sin_sembrar")
    etapa_desde = models.DateField(null=True)

    class Meta:
        db_table = "huerto_planta"
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["huerto", "numero"], name="planta_numero_unico")]


class PlantaEtapa(models.Model):
    """Historial de etapas; lo llena un trigger y no cambia."""
    planta = models.ForeignKey(Planta, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    etapa = models.CharField(max_length=16)
    desde = models.DateField()
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    registrada_en = models.DateTimeField(db_default=AHORA)

    class Meta:
        db_table = "huerto_planta_etapa"
        default_permissions = ()
