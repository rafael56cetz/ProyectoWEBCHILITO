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
    # Ciclo al que pertenece (web.0007): lo fija la base al insertar, con el ciclo abierto de la planta. En la base es NOT NULL.
    ciclo = models.ForeignKey("PlantaCiclo", null=True, on_delete=models.DO_NOTHING, related_name="+", db_index=False)

    class Meta:
        db_table = "huerto_planta_etapa"
        default_permissions = ()


class PlantaCiclo(models.Model):
    """Ciclos de una planta (web.0007): siempre hay uno abierto. Terminarlo lo cierra con su motivo y abre el siguiente;
    lo hace solo el dueño con chilito_terminar_ciclo. No se borran ni cambian después de cerrarse."""
    planta = models.ForeignKey(Planta, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    numero = models.SmallIntegerField()
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True)
    motivo = models.CharField(max_length=16, null=True)   # cosecha_terminada | planta_murio | no_germino | pudricion_plaga | otro
    nota = models.CharField(max_length=500, db_default="")
    cerrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.DO_NOTHING, related_name="+", db_index=False)

    class Meta:
        db_table = "planta_ciclo"
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["planta", "numero"], name="ciclo_numero_unico")]


class PlantaRecomendacion(models.Model):
    """Recomendación ya avisada al dueño (web.0007): una sola vez por ciclo y situación. La escribe solo la base."""
    pk = models.CompositePrimaryKey("ciclo", "situacion")
    ciclo = models.ForeignKey(PlantaCiclo, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    situacion = models.CharField(max_length=20)   # germinacion_larga | sustrato_saturado | seca_con_riegos
    creada_en = models.DateTimeField(db_default=AHORA)

    class Meta:
        db_table = "planta_recomendacion"
        default_permissions = ()
