import uuid

from django.conf import settings
from django.db import models
from django.db.models import Case, F, Value, When
from django.db.models.functions import Cast, Concat, Replace, Substr, Upper

from huerto.models import Huerto
from web.models import AHORA, EN_10_MINUTOS, EN_24_HORAS, CampoCharFijo

USUARIO = settings.AUTH_USER_MODEL


class CampoMac(models.Field):
    def db_type(self, connection):
        return "macaddr"


def folio(prefijo):
    texto = Replace(Cast("id", models.CharField()), Value("-"), Value(""))
    return models.GeneratedField(
        expression=Concat(Value(prefijo), Upper(Substr(texto, 1, 8))),
        output_field=models.CharField(max_length=11), db_persist=True, unique=True)


def uuid_pk():
    return models.UUIDField(primary_key=True, default=uuid.uuid4, db_default=models.Func(function="gen_random_uuid"),
                            editable=False)


def fk(destino, **opciones):
    return models.ForeignKey(destino, on_delete=models.DO_NOTHING, related_name="+", db_index=False, **opciones)


class Base(models.Model):
    class Meta:
        abstract = True
        default_permissions = ()


class Dispositivo(Base):
    identificador = models.CharField(max_length=32, unique=True)
    mac = CampoMac(unique=True)
    credencial_hash = models.CharField(max_length=255)
    firmware_version = models.CharField(max_length=32, db_default="")
    estado = models.CharField(max_length=12, db_default="disponible")
    huerto = models.OneToOneField(Huerto, null=True, on_delete=models.DO_NOTHING, related_name="+")
    vinculado_en = models.DateTimeField(null=True)
    conexion = models.CharField(max_length=12, db_default="nunca")
    ultima_conexion_en = models.DateTimeField(null=True)
    registrado_por = fk(USUARIO, null=True)
    registrado_en = models.DateTimeField(db_default=AHORA)
    retirado_en = models.DateTimeField(null=True)

    class Meta(Base.Meta):
        db_table = "dispositivo"


class CodigoVinculacion(Base):
    id = uuid_pk()
    huerto = fk(Huerto)
    generado_por = fk(USUARIO)
    codigo_hash = CampoCharFijo(max_length=64, unique=True)
    generado_en = models.DateTimeField(db_default=AHORA)
    vence_en = models.DateTimeField(db_default=EN_10_MINUTOS)
    estado = models.CharField(max_length=10, db_default="pendiente")
    dispositivo = fk(Dispositivo, null=True)
    cerrado_en = models.DateTimeField(null=True)

    class Meta(Base.Meta):
        db_table = "codigo_vinculacion"


class DispositivoEvento(Base):
    dispositivo = fk(Dispositivo)
    huerto = fk(Huerto, null=True)
    tipo = models.CharField(max_length=20)
    detalle = models.CharField(max_length=200, db_default="")
    actor = fk(USUARIO, null=True)
    ocurrido_en = models.DateTimeField(db_default=AHORA)
    registrado_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "dispositivo_evento"


class Medicion(Base):
    dispositivo = fk(Dispositivo)
    huerto = fk(Huerto)
    medida_en = models.DateTimeField()
    recibida_en = models.DateTimeField(db_default=AHORA)
    temperatura_c = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    humedad_aire_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    luz_lux = models.DecimalField(max_digits=8, decimal_places=1, null=True)
    deposito_con_agua = models.BooleanField(null=True)

    class Meta(Base.Meta):
        db_table = "medicion"
        constraints = [models.UniqueConstraint(fields=["dispositivo", "medida_en"], name="medicion_unica")]


class MedicionPlanta(Base):
    pk = models.CompositePrimaryKey("medicion", "planta_numero")
    medicion = models.ForeignKey(Medicion, on_delete=models.CASCADE, related_name="+", db_index=False)
    planta_numero = models.SmallIntegerField()
    humedad_sustrato_pct = models.DecimalField(max_digits=4, decimal_places=1)
    adc_crudo = models.SmallIntegerField(null=True)

    class Meta(Base.Meta):
        db_table = "medicion_planta"


class ResumenHoraHuerto(Base):
    pk = models.CompositePrimaryKey("huerto", "hora")
    huerto = fk(Huerto)
    hora = models.DateTimeField()
    muestras = models.IntegerField()
    temperatura_prom = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    temperatura_min = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    temperatura_max = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    humedad_aire_prom = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    humedad_aire_min = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    humedad_aire_max = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    luz_prom = models.DecimalField(max_digits=8, decimal_places=1, null=True)
    luz_max = models.DecimalField(max_digits=8, decimal_places=1, null=True)
    muestras_sin_agua = models.IntegerField(db_default=0)

    class Meta(Base.Meta):
        db_table = "resumen_hora_huerto"


class ResumenHoraPlanta(Base):
    pk = models.CompositePrimaryKey("huerto", "hora", "planta_numero")
    huerto = fk(Huerto)
    hora = models.DateTimeField()
    planta_numero = models.SmallIntegerField()
    muestras = models.IntegerField()
    humedad_prom = models.DecimalField(max_digits=4, decimal_places=1)
    humedad_min = models.DecimalField(max_digits=4, decimal_places=1)
    humedad_max = models.DecimalField(max_digits=4, decimal_places=1)

    class Meta(Base.Meta):
        db_table = "resumen_hora_planta"


class SoporteCaso(Base):
    id = uuid_pk()
    folio = folio("CS-")
    huerto = fk(Huerto)
    dispositivo = fk(Dispositivo)
    solicitante = fk(USUARIO)
    incidente = models.CharField(max_length=10)
    nota = models.CharField(max_length=500, db_default="")
    autodiagnostico = models.ForeignKey("Autodiagnostico", null=True, on_delete=models.DO_NOTHING, related_name="+", db_index=False)
    consentimiento = models.BooleanField()
    autorizada_en = models.DateTimeField(db_default=AHORA)
    autorizacion_vence_en = models.DateTimeField(db_default=EN_24_HORAS)
    autorizacion_revocada_en = models.DateTimeField(null=True)
    estado = models.CharField(max_length=12, db_default="abierto")
    atendido_por = fk(USUARIO, null=True)
    tomado_en = models.DateTimeField(null=True)
    resultado = models.CharField(max_length=14, null=True)
    nota_resolucion = models.CharField(max_length=500, db_default="")
    cerrado_en = models.DateTimeField(null=True)
    creado_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "soporte_caso"


class SoporteSesion(Base):
    id = uuid_pk()
    caso = fk(SoporteCaso)
    administrador = fk(USUARIO)
    iniciada_en = models.DateTimeField(db_default=AHORA)
    cerrada_en = models.DateTimeField(null=True)
    motivo_cierre = models.CharField(max_length=14, db_default="")

    class Meta(Base.Meta):
        db_table = "soporte_sesion"


class Comando(Base):
    id = uuid_pk()
    huerto = fk(Huerto)
    dispositivo = fk(Dispositivo)
    tipo = models.CharField(max_length=20)
    planta_numero = models.SmallIntegerField(null=True)
    duracion_s = models.SmallIntegerField(null=True)
    origen = models.CharField(max_length=8)
    solicitado_por = fk(USUARIO)
    sesion = fk(SoporteSesion, null=True)
    estado = models.CharField(max_length=10, db_default="pendiente")
    creado_en = models.DateTimeField(db_default=AHORA)
    enviado_en = models.DateTimeField(null=True)
    resuelto_en = models.DateTimeField(null=True)
    detalle_error = models.CharField(max_length=200, db_default="")

    class Meta(Base.Meta):
        db_table = "comando"


class Actuacion(Base):
    dispositivo = fk(Dispositivo)
    huerto = fk(Huerto)
    actuador = models.CharField(max_length=10)
    planta_numero = models.SmallIntegerField(null=True)
    accion = models.CharField(max_length=10)
    duracion_s = models.SmallIntegerField(null=True)
    origen = models.CharField(max_length=10)
    comando = fk(Comando, null=True)
    ocurrido_en = models.DateTimeField()
    registrado_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "actuacion"


class Autodiagnostico(Base):
    id = uuid_pk()
    huerto = fk(Huerto)
    dispositivo = fk(Dispositivo)
    comando = models.OneToOneField(Comando, on_delete=models.DO_NOTHING, related_name="+")
    solicitado_por = fk(USUARIO)
    estado = models.CharField(max_length=14, db_default="en_curso")
    resultado_general = models.CharField(max_length=12, null=True)
    iniciado_en = models.DateTimeField(db_default=AHORA)
    completado_en = models.DateTimeField(null=True)

    class Meta(Base.Meta):
        db_table = "autodiagnostico"


class AutodiagnosticoRevision(Base):
    pk = models.CompositePrimaryKey("autodiagnostico", "componente")
    autodiagnostico = fk(Autodiagnostico)
    componente = models.CharField(max_length=20)
    resultado = models.CharField(max_length=14)
    detalle = models.CharField(max_length=200, db_default="")

    class Meta(Base.Meta):
        db_table = "autodiagnostico_revision"


class Cuidado(Base):
    id = uuid_pk()
    huerto = fk(Huerto)
    planta_numero = models.SmallIntegerField(null=True)
    tipo = models.CharField(max_length=18)
    chiles_cosechados = models.SmallIntegerField(null=True)
    realizado_en = models.DateTimeField(db_default=AHORA)
    registrado_por = fk(USUARIO)
    registrado_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "cuidado"


class CuidadoRevision(Base):
    id = uuid_pk()
    cuidado = fk(Cuidado)
    numero = models.IntegerField()
    tipo = models.CharField(max_length=10)
    tipo_corregido = models.CharField(max_length=18, null=True)
    planta_corregida = models.SmallIntegerField(null=True)
    chiles_corregidos = models.SmallIntegerField(null=True)
    motivo = models.CharField(max_length=500)
    editor = fk(USUARIO)
    registrada_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "cuidado_revision"
        constraints = [models.UniqueConstraint(fields=["cuidado", "numero"], name="revision_cuidado_orden")]


class GuiaCuidado(Base):
    id = uuid_pk()
    clave = models.CharField(max_length=64, unique=True)
    pregunta = models.CharField(max_length=200)
    respuesta = models.TextField()
    orden = models.IntegerField()
    estado = models.CharField(max_length=10, db_default="borrador")
    fuente_nombre = models.CharField(max_length=120, db_default="")
    fuente_url = models.CharField(max_length=500, db_default="")
    version = models.IntegerField(db_default=1)
    creado_en = models.DateTimeField(db_default=AHORA)
    actualizado_en = models.DateTimeField(db_default=AHORA)
    creado_por = fk(USUARIO, null=True)
    actualizado_por = fk(USUARIO, null=True)

    class Meta(Base.Meta):
        db_table = "guia_cuidado"


class Notificacion(Base):
    destinatario = fk(USUARIO)
    origen = models.CharField(max_length=12)
    severidad = models.CharField(max_length=12, db_default="informacion")
    titulo = models.CharField(max_length=120)
    texto = models.CharField(max_length=1000, db_default="")
    huerto = fk(Huerto, null=True)
    enlace = models.CharField(max_length=120, db_default="")
    creada_en = models.DateTimeField(db_default=AHORA)
    leida_en = models.DateTimeField(null=True)
    resuelta_en = models.DateTimeField(null=True)

    class Meta(Base.Meta):
        db_table = "notificacion"


class IaResumen(Base):
    huerto = fk(Huerto)
    contenido = models.CharField(max_length=2000)
    modelo = models.CharField(max_length=64)
    datos_hasta = models.DateTimeField()
    generado_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "ia_resumen"


class ConsultaProducto(Base):
    id = uuid_pk()
    folio = folio("CP-")
    recibida_en = models.DateTimeField(db_default=AHORA)
    nombre = models.CharField(max_length=100, db_default="")
    correo = models.CharField(max_length=254)
    mensaje = models.CharField(max_length=2000)
    huella = CampoCharFijo(max_length=64)
    estado = models.CharField(max_length=10, db_default="nueva")
    atendida_en = models.DateTimeField(null=True)
    atendida_por = fk(USUARIO, null=True)
    anonimizada_en = models.DateTimeField(null=True)

    class Meta(Base.Meta):
        db_table = "consulta_producto"


class CorreoPendiente(Base):
    id = uuid_pk()
    tipo = models.CharField(max_length=16)
    caso = fk(SoporteCaso, null=True)
    consulta = fk(ConsultaProducto, null=True)
    estado = models.CharField(max_length=14, db_default="pendiente")
    intentos = models.SmallIntegerField(db_default=0)
    creado_en = models.DateTimeField(db_default=AHORA)
    ultimo_intento_en = models.DateTimeField(null=True)
    aceptado_en = models.DateTimeField(null=True)

    class Meta(Base.Meta):
        db_table = "correo_pendiente"


class Venta(Base):
    dispositivo = fk(Dispositivo)
    comprador_nombre = models.CharField(max_length=120)
    comprador_correo = models.CharField(max_length=254)
    comprador_usuario = fk(USUARIO, null=True)
    municipio = models.CharField(max_length=60)
    precio_mxn = models.DecimalField(max_digits=10, decimal_places=2)
    importe_recibido_mxn = models.DecimalField(max_digits=10, decimal_places=2, db_default=0)
    referencia_pago = models.CharField(max_length=120, db_default="")
    estado_pago = models.GeneratedField(
        expression=Case(When(importe_recibido_mxn=0, then=Value("pendiente")),
                        When(importe_recibido_mxn__lt=F("precio_mxn"), then=Value("parcial")),
                        default=Value("completo")),
        output_field=models.CharField(max_length=10), db_persist=True)
    modalidad_entrega = models.CharField(max_length=10)
    vendida_en = models.DateField()
    entrega_prevista_en = models.DateField(null=True)
    entregada_en = models.DateField(null=True)
    estado = models.CharField(max_length=10, db_default="vigente")
    cancelada_en = models.DateTimeField(null=True)
    nota = models.CharField(max_length=500, db_default="")
    registrada_por = fk(USUARIO)
    registrada_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "venta"


class Auditoria(Base):
    actor = fk(USUARIO, null=True)
    accion = models.CharField(max_length=48)
    entidad = models.CharField(max_length=40, db_default="")
    entidad_id = models.CharField(max_length=64, db_default="")
    huerto = fk(Huerto, null=True)
    resultado = models.CharField(max_length=10, db_default="exito")
    detalle = models.JSONField(db_default={})
    ip_recortada = models.CharField(max_length=45, db_default="")
    creada_en = models.DateTimeField(db_default=AHORA)

    class Meta(Base.Meta):
        db_table = "auditoria"
