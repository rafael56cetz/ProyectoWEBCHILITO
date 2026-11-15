from django.conf import settings
from django.db import models
class Idempotencia(models.Model):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    clave=models.UUIDField()
    ruta=models.CharField(max_length=240)
    huella=models.CharField(max_length=64)
    respuesta=models.JSONField()
    creada_en=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['actor','clave'],name='web_idempotencia_actor_clave')]
