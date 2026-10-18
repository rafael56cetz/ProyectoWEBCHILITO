from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

class ValidatedModel(models.Model):
    class Meta:
        abstract = True
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class Huerto(ValidatedModel):
    clave = models.SlugField(max_length=64, unique=True)
    nombre = models.CharField(max_length=100)
    zona_horaria = models.CharField(max_length=64, default="America/Mexico_City")
    creado_en = models.DateTimeField(auto_now_add=True)

    def clean(self):
        try:
            ZoneInfo(self.zona_horaria)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValidationError({"zona_horaria": "Zona horaria IANA invalida."}) from None

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(nombre=""), name="huerto_nombre_no_vacio"),
            models.CheckConstraint(condition=~Q(clave=""), name="huerto_clave_no_vacia"),
        ]

class Zona(ValidatedModel):
    huerto = models.ForeignKey(Huerto, on_delete=models.PROTECT)
    numero = models.PositiveSmallIntegerField()
    nombre = models.CharField(max_length=80)
    cultivo = models.CharField(max_length=80, default="Chile habanero")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["huerto", "numero"], name="zona_numero_unico"),
            models.CheckConstraint(condition=Q(numero__gte=1, numero__lte=3), name="zona_rango_1_3"),
            models.CheckConstraint(condition=~Q(nombre=""), name="zona_nombre_no_vacio"),
        ]

class Membresia(ValidatedModel):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    huerto = models.ForeignKey(Huerto, on_delete=models.PROTECT)
    activa = models.BooleanField(default=True)
    asignada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "huerto"], name="membresia_unica"),
        ]

class Aviso(ValidatedModel):
    """Only recorded notices; no automatic generator, seed data or IoT commands."""
    huerto = models.ForeignKey(Huerto, on_delete=models.PROTECT)
    zona = models.ForeignKey(Zona, null=True, blank=True, on_delete=models.PROTECT)
    severidad = models.CharField(max_length=16, choices=[
        ("informacion", "Información"), ("advertencia", "Advertencia"), ("critico", "Crítico")])
    titulo = models.CharField(max_length=160)
    descripcion = models.TextField()
    recomendacion = models.TextField(blank=True)
    creado_en = models.DateTimeField()
    resuelto_en = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.zona_id and not Zona.objects.filter(pk=self.zona_id, huerto_id=self.huerto_id).exists():
            raise ValidationError({"zona": "La zona no pertenece al huerto del aviso."})
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values("huerto_id", "zona_id").first()
            if previous and (previous["huerto_id"], previous["zona_id"]) != (self.huerto_id, self.zona_id):
                raise ValidationError("No se puede reasignar un aviso.")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(severidad__in=["informacion", "advertencia", "critico"]), name="aviso_severidad_valida"),
            models.CheckConstraint(condition=~Q(titulo=""), name="aviso_titulo_no_vacio"),
            models.CheckConstraint(condition=~Q(descripcion=""), name="aviso_descripcion_no_vacia"),
            models.CheckConstraint(condition=Q(resuelto_en__isnull=True) | Q(resuelto_en__gte=models.F("creado_en")), name="aviso_fechas_coherentes"),
        ]
        indexes = [models.Index(fields=["huerto", "-creado_en", "-id"], name="aviso_huerto_orden_idx")]

class AvisoLeido(ValidatedModel):
    aviso = models.ForeignKey(Aviso, on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    leido_en = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["aviso", "usuario"], name="aviso_usuario_unico")]
