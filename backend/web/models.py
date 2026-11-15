from django.conf import settings
from django.db import models
from django.db.models.expressions import RawSQL

# Now() de Django genera statement_timestamp(); la base usa now() (hora de la transacción).
AHORA = RawSQL("now()", [], output_field=models.DateTimeField())
EN_10_MINUTOS = RawSQL("now() + interval '10 minutes'", [], output_field=models.DateTimeField())
EN_24_HORAS = RawSQL("now() + interval '24 hours'", [], output_field=models.DateTimeField())


class CampoCharFijo(models.CharField):
    def db_type(self, connection):
        return "char(%d)" % self.max_length


class Idempotencia(models.Model):
    clave = models.UUIDField()
    ruta = models.CharField(max_length=240)
    huella = CampoCharFijo(max_length=64)
    respuesta = models.JSONField()
    creada_en = models.DateTimeField(db_default=AHORA)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, related_name="+", db_index=False)

    class Meta:
        db_table = "web_idempotencia"
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["actor", "clave"], name="web_idempotencia_actor_clave")]
