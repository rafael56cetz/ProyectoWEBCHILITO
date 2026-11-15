import uuid

from django.conf import settings
from django.db import models
from django.db.models import Func
from web.models import AHORA, CampoCharFijo

USUARIO = settings.AUTH_USER_MODEL


def uuid_pk():
    return models.UUIDField(primary_key=True, default=uuid.uuid4, db_default=Func(function="gen_random_uuid"),
                            editable=False)


def fk(destino, **opciones):
    return models.ForeignKey(destino, on_delete=models.DO_NOTHING, related_name="+", db_index=False, **opciones)


class Base(models.Model):
    class Meta:
        abstract = True
        default_permissions = ()


class DocumentoLegal(Base):
    id = uuid_pk()
    tipo = models.CharField(max_length=18)
    version = models.CharField(max_length=20)
    titulo = models.CharField(max_length=120)
    contenido = models.TextField()
    contenido_sha256 = CampoCharFijo(max_length=64)
    estado = models.CharField(max_length=10, db_default="borrador")
    creado_por = fk(USUARIO, null=True)
    creado_en = models.DateTimeField(db_default=AHORA)
    actualizado_en = models.DateTimeField(db_default=AHORA)
    publicado_por = fk(USUARIO, null=True)
    publicado_en = models.DateTimeField(null=True)

    class Meta(Base.Meta):
        db_table = "documento_legal"
        constraints = [models.UniqueConstraint(fields=["tipo", "version"], name="legal_version_unica")]


class Finalidad(Base):
    id = uuid_pk()
    codigo = models.CharField(max_length=64, unique=True)
    descripcion = models.CharField(max_length=255)
    creada_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "privacidad_finalidad"


class Sujeto(Base):
    id = uuid_pk()
    ambito = models.CharField(max_length=9)
    usuario = fk(USUARIO, null=True)
    creado_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "privacidad_sujeto"


class Decision(Base):
    id = uuid_pk()
    sujeto = fk(Sujeto)
    acto = models.CharField(max_length=20)
    decision = models.BooleanField()
    documento = fk(DocumentoLegal)
    finalidad = fk(Finalidad, null=True)
    usuario = fk(USUARIO, null=True)
    ip_recortada = models.CharField(max_length=45, db_default="")
    navegador = models.CharField(max_length=120, db_default="")
    registrada_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "privacidad_decision"


class Preferencia(Base):
    id = uuid_pk()
    sujeto = fk(Sujeto)
    finalidad = fk(Finalidad)
    decision = fk(Decision)
    actualizada_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "privacidad_preferencia"
        constraints = [models.UniqueConstraint(fields=["sujeto", "finalidad"], name="priv_preferencia_unica")]


class ConteoNavegacion(Base):
    dia = models.DateField()
    seccion = models.CharField(max_length=16)
    visitas = models.BigIntegerField(db_default=0)

    class Meta(Base.Meta):
        db_table = "conteo_navegacion"
        constraints = [models.UniqueConstraint(fields=["dia", "seccion"], name="conteo_dia_seccion_unico")]
