"""Persistencia propuesta; no implementa API, identidad, consentimiento ni ARCO.

Los catálogos se entregan vacíos y no existe aceptación implícita. Los servicios deben autorizar al actor y guardar cambio, estado vigente y evento en una sola transacción."""
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils import timezone


PROTECT = models.PROTECT


def fecha():
    return models.DateTimeField(default=timezone.now, db_default=Now(), editable=False)


def significativo(campo, nombre):
    return models.CheckConstraint(condition=Q(**{campo + "__regex": r"\S"}), name=nombre)


class DocumentoVersion(models.Model):
    TIPOS = [("aviso_privacidad", "Aviso de privacidad"), ("terminos", "Términos"),
             ("politica_cookies", "Política de cookies")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=16, choices=TIPOS)
    version = models.CharField(max_length=64)
    contenido_ref = models.CharField(max_length=255)
    contenido_sha256 = models.CharField(
        max_length=64, validators=[RegexValidator(r"^[0-9a-f]{64}$")]
    )
    registrado_en = fecha()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tipo", "version"], name="priv_documento_version_unica"),
            models.CheckConstraint(condition=Q(tipo__in=["aviso_privacidad", "terminos", "politica_cookies"]), name="priv_documento_tipo_valido"),
            significativo("version", "priv_documento_version_texto"),
            significativo("contenido_ref", "priv_documento_ref_texto"),
            models.CheckConstraint(condition=Q(contenido_sha256__regex=r"^[0-9a-f]{64}$"), name="priv_documento_hash_valido"),
        ]


class SujetoPrivacidad(models.Model):
    # UUID independiente de credenciales, cookies e identificadores de sesión.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ambito = models.CharField(max_length=9, choices=[("cuenta", "Cuenta"), ("navegador", "Navegador")], default="cuenta")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=PROTECT,
        related_name="sujetos_privacidad",
    )
    creado_en = fecha()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(ambito__in=["cuenta", "navegador"]), name="priv_sujeto_ambito_valido"),
            models.UniqueConstraint(fields=["usuario"], condition=Q(ambito="cuenta"), name="priv_sujeto_cuenta_unica"),
        ]


class FinalidadOpcional(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(
        max_length=64, unique=True,
        validators=[RegexValidator(r"^[a-z][a-z0-9_]{0,63}$")],
    )
    descripcion = models.CharField(max_length=255)
    creada_en = fecha()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(codigo__regex=r"^[a-z][a-z0-9_]{0,63}$"), name="priv_finalidad_codigo_valido"),
            significativo("descripcion", "priv_finalidad_descripcion_texto"),
        ]


class DecisionPrivacidad(models.Model):
    ACTOS = [(x, x) for x in ("lectura_aviso", "aceptacion_terminos", "consentimiento", "cookies")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sujeto = models.ForeignKey(SujetoPrivacidad, on_delete=PROTECT)
    documento = models.ForeignKey(DocumentoVersion, on_delete=PROTECT)
    politica_cookies = models.ForeignKey(
        DocumentoVersion, on_delete=PROTECT, null=True, blank=True,
        related_name="decisiones_cookies",
    )
    finalidad = models.ForeignKey(FinalidadOpcional, on_delete=PROTECT, null=True, blank=True)
    acto = models.CharField(max_length=20, choices=ACTOS)
    decision = models.BooleanField()  # Sin valor por defecto: no existe aceptación automática.
    registrada_en = fecha()

    def clean(self):
        super().clean()
        if self.acto not in dict(self.ACTOS):
            raise ValidationError({"acto": "Acto no admitido."})
        if (self.acto in {"consentimiento", "cookies"}) != (self.finalidad_id is not None):
            raise ValidationError({"finalidad": "El consentimiento y las cookies requieren una finalidad opcional."})
        if (self.acto == "cookies") != (self.politica_cookies_id is not None):
            raise ValidationError({"politica_cookies": "Solo la decisión de cookies requiere su política versionada."})
        # Los cruces con los tipos de documento los protege PostgreSQL en 0003.

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(acto="consentimiento", finalidad__isnull=False, politica_cookies__isnull=True)
                           | Q(acto="cookies", finalidad__isnull=False, politica_cookies__isnull=False)
                           | Q(acto__in=["lectura_aviso", "aceptacion_terminos"],
                               finalidad__isnull=True, politica_cookies__isnull=True)),
                name="priv_decision_acto_finalidad",
            ),
        ]
        indexes = [models.Index(fields=["sujeto", "finalidad", "-registrada_en"], name="priv_decision_historial_idx")]


class PreferenciaFinalidad(models.Model):
    """Puntero explícito al estado vigente; la fecha no elige el último evento.

    Cambiar este puntero y crear decisión/evento requiere un servicio transaccional
    con serialización por sujeto. Ese servicio no forma parte de este paquete.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sujeto = models.ForeignKey(SujetoPrivacidad, on_delete=PROTECT)
    finalidad = models.ForeignKey(FinalidadOpcional, on_delete=PROTECT)
    decision = models.ForeignKey(DecisionPrivacidad, on_delete=PROTECT)
    actualizada_en = fecha()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sujeto", "finalidad"], name="priv_preferencia_unica")]


class EventoPrivacidad(models.Model):
    ACCIONES = [(x, x) for x in ("decision", "rectificacion", "oposicion", "acceso")]
    RESULTADOS = [(x, x) for x in ("completado", "rechazado")]
    CAMPOS = [("", "No aplica"), ("first_name", "Nombre"), ("last_name", "Apellido"), ("alias", "Alias")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sujeto = models.ForeignKey(SujetoPrivacidad, on_delete=PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, null=True, blank=True)
    accion = models.CharField(max_length=16, choices=ACCIONES)
    resultado = models.CharField(max_length=12, choices=RESULTADOS)
    decision = models.ForeignKey(DecisionPrivacidad, on_delete=PROTECT, null=True, blank=True)
    finalidad = models.ForeignKey(FinalidadOpcional, on_delete=PROTECT, null=True, blank=True)
    campo = models.CharField(max_length=10, choices=CAMPOS, blank=True, default="")
    creado_en = fecha()

    def clean(self):
        super().clean()
        if self.accion not in dict(self.ACCIONES):
            raise ValidationError({"accion": "Acción no admitida."})
        if self.resultado not in dict(self.RESULTADOS):
            raise ValidationError({"resultado": "Resultado no admitido."})
        if self.accion == "acceso":
            if (self.actor_id is None or self.campo
                    or self.decision_id is not None or self.finalidad_id is not None):
                raise ValidationError("El acceso requiere actor y no registra campos, decisiones ni finalidades.")
        elif self.accion == "rectificacion":
            if (self.actor_id is None or self.campo not in {"first_name", "last_name", "alias"}
                    or self.decision_id is not None or self.finalidad_id is not None):
                raise ValidationError("La rectificación requiere actor y campo del perfil, sin decisión ni finalidad.")
        elif self.campo or self.decision_id is None:
            raise ValidationError("Las decisiones y oposiciones requieren una decisión y no un campo del perfil.")
        elif self.accion == "oposicion" and (self.actor_id is None or self.finalidad_id is None):
            raise ValidationError("La oposición requiere actor y finalidad opcional.")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(resultado__in=["completado", "rechazado"]), name="priv_evento_resultado_valido"),
            models.CheckConstraint(
                condition=(Q(accion="rectificacion", actor__isnull=False, campo__in=["first_name", "last_name", "alias"],
                             decision__isnull=True, finalidad__isnull=True)
                           | Q(accion="acceso", actor__isnull=False, campo="",
                               decision__isnull=True, finalidad__isnull=True)
                           | Q(accion="decision", campo="", decision__isnull=False)
                           | Q(accion="oposicion", actor__isnull=False, campo="", decision__isnull=False, finalidad__isnull=False)),
                name="priv_evento_referencias_validas",
            ),
        ]
        indexes = [models.Index(fields=["sujeto", "-creado_en"], name="priv_evento_historial_idx")]


class ConteoNavegacion(models.Model):
    """Totales diarios. La autorización previa corresponde al servicio pendiente.

    No conserva rutas completas, parámetros, cuentas, sujetos, cookies o IP.
    La sección es un código de una lista cerrada, nunca texto enviado libremente.
    """
    SECCIONES = [(x, x) for x in ("inicio", "proyecto", "prototipo", "funcionamiento",
                                "huerto", "panel_tecnico", "mantenimiento", "soporte",
                                "avisos", "cuenta", "privacidad")]
    dia = models.DateField()
    seccion = models.CharField(max_length=16, choices=SECCIONES)
    visitas = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["dia", "seccion"], name="priv_conteo_dia_seccion_unico"),
            models.CheckConstraint(condition=Q(seccion__in=[x for x, _ in (
                ("inicio", ""), ("proyecto", ""), ("prototipo", ""), ("funcionamiento", ""),
                ("huerto", ""), ("panel_tecnico", ""), ("mantenimiento", ""), ("soporte", ""),
                ("avisos", ""), ("cuenta", ""), ("privacidad", ""))]), name="priv_conteo_seccion_valida"),
        ]
