import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Length
models.TextField.register_lookup(Length)
from django.utils import timezone
PROTECT=models.PROTECT

def significant(field):
    return Q(**{field+'__regex':r'\S'})

def nonblank(field,name):
    return models.CheckConstraint(condition=significant(field),name=name)

class Dispositivo(models.Model):
    huerto=models.OneToOneField('huerto.Huerto',on_delete=PROTECT)
    identificador=models.CharField(max_length=128,unique=True)
    creado_en=models.DateTimeField(default=timezone.now,editable=False)
    class Meta:
        constraints=[nonblank('identificador','dispositivo_id_significativo')]
        permissions=[('ver_flota','Consultar flota agregada'),('atender_soporte','Atender casos de soporte'),
                     ('gestionar_mantenimientos','Gestionar mantenimientos de huertos asignados'),
                     ('atender_consultas','Atender consultas del producto'),
                     ('vincular_huertos','Emitir y revocar códigos de vinculación de huertos'),
                     ('gestionar_guias','Crear, editar, publicar y retirar guías de cuidado')]

class Mantenimiento(models.Model):
    TIPOS=[(x,x) for x in ['refill','substrate','germination','harvest','inspection']]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    huerto=models.ForeignKey('huerto.Huerto',on_delete=PROTECT)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT)
    tipo=models.CharField(max_length=16,choices=TIPOS)
    registrado_en=models.DateTimeField(default=timezone.now,editable=False)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(tipo__in=['refill','substrate','germination','harvest','inspection']),name='mantenimiento_tipo_valido')]
        indexes=[models.Index(fields=['huerto','-registrado_en'],name='mant_huerto_fecha_idx')]

class AsignacionMantenimiento(models.Model):
    # Alcance por huerto de gestionar_mantenimientos. Lo administra el propietario;
    # el runtime solo lee, y la capacidad sola no da acceso a ningún huerto.
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT,related_name='asignaciones_mantenimiento')
    huerto=models.ForeignKey('huerto.Huerto',on_delete=PROTECT)
    activa=models.BooleanField(default=True)
    asignada_en=models.DateTimeField(default=timezone.now,editable=False)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['usuario','huerto'],name='asignacion_mant_unica')]

class RevisionMantenimiento(models.Model):
    # Anexo de solo inserción: Mantenimiento conserva el registro original. El estado
    # vigente sale de estas filas; numero ordena sin depender de fechas ni de UUID.
    TIPOS=[(x,x) for x in ['correccion','anulacion']]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    mantenimiento=models.ForeignKey(Mantenimiento,on_delete=PROTECT)
    numero=models.PositiveIntegerField()
    tipo=models.CharField(max_length=12,choices=TIPOS)
    tipo_corregido=models.CharField(max_length=16,choices=Mantenimiento.TIPOS,null=True,blank=True)
    editor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT,related_name='revisiones_mantenimiento')
    motivo=models.TextField()
    registrada_en=models.DateTimeField(default=timezone.now,editable=False)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['mantenimiento','numero'],name='revision_mant_orden_unico'),
         models.UniqueConstraint(fields=['mantenimiento'],condition=Q(tipo='anulacion'),name='revision_mant_una_anulacion'),
         models.CheckConstraint(condition=Q(numero__gte=1),name='revision_mant_numero_valido'),
         models.CheckConstraint(condition=(Q(tipo='correccion',tipo_corregido__isnull=False,tipo_corregido__in=['refill','substrate','germination','harvest','inspection'])|
          Q(tipo='anulacion',tipo_corregido__isnull=True)),name='revision_mant_tipo_coherente'),
         nonblank('motivo','revision_mant_motivo_significativo'),
         models.CheckConstraint(condition=Q(motivo__length__lte=500),name='revision_mant_motivo_limite')]

class CasoSoporte(models.Model):
    INCIDENTES=[(x,x) for x in ['pump','humidity','lamp','connection','other']]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    huerto=models.ForeignKey('huerto.Huerto',on_delete=PROTECT)
    dispositivo=models.ForeignKey(Dispositivo,on_delete=PROTECT)
    solicitante=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT)
    incidente=models.CharField(max_length=16,choices=INCIDENTES)
    creado_en=models.DateTimeField(default=timezone.now,editable=False)
    # No closure flow exists in the frontend; permission/session states are derived.
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(incidente__in=['pump','humidity','lamp','connection','other']),name='soporte_incidente_valido')]
        indexes=[models.Index(fields=['solicitante','-creado_en'],name='caso_solicitante_fecha_idx')]

class PermisoSoporte(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    caso=models.ForeignKey(CasoSoporte,on_delete=PROTECT)
    otorgante=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT)
    consentimiento=models.BooleanField(default=True,editable=False)
    verificador=models.CharField(max_length=64,unique=True,editable=False)
    alcance=models.CharField(max_length=24,default='diagnostico_incidente',editable=False)
    emitido_en=models.DateTimeField(default=timezone.now,editable=False)
    vence_en=models.DateTimeField()
    revocado_en=models.DateTimeField(null=True,blank=True)
    class Meta:
        constraints=[
          models.CheckConstraint(condition=Q(consentimiento=True),name='permiso_consentimiento_explicito'),
          models.CheckConstraint(condition=Q(verificador__regex=r'^[0-9a-f]{64}$'),name='permiso_verificador_sha256'),
          models.CheckConstraint(condition=Q(alcance='diagnostico_incidente'),name='permiso_alcance_limitado'),
          models.CheckConstraint(condition=Q(vence_en__gt=F('emitido_en')) & Q(vence_en__lte=F('emitido_en')+timedelta(hours=24)),name='permiso_ventana_24h'),
          models.CheckConstraint(condition=Q(revocado_en__isnull=True)|Q(revocado_en__gte=F('emitido_en')),name='permiso_revocacion_coherente')]
        indexes=[models.Index(fields=['caso','vence_en'],name='permiso_caso_vence_idx')]

class ResolucionSoporte(models.Model):
    """Cierre expreso de un caso: quién, cuándo y con qué resultado. Historial inmutable.
    El caso no se modifica; está resuelto si tiene resolución. Vencer o revocar el permiso no resuelve."""
    RESULTADOS=[('solucionado','Problema solucionado'),('sin_falla','Sin falla detectada'),
                ('sin_respuesta','Sin respuesta de la persona usuaria'),('otro','Otro (explicado en la nota)')]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    caso=models.OneToOneField(CasoSoporte,on_delete=PROTECT,related_name='resolucion')
    responsable=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT,related_name='resoluciones_soporte')
    resultado=models.CharField(max_length=20,choices=RESULTADOS)
    nota=models.TextField(blank=True,default='')
    resuelto_en=models.DateTimeField(default=timezone.now,editable=False)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(resultado__in=['solucionado','sin_falla','sin_respuesta','otro']),name='resolucion_resultado_valido'),
         models.CheckConstraint(condition=~Q(resultado='otro')|Q(nota__regex=r'\S'),name='resolucion_otro_con_nota'),
         models.CheckConstraint(condition=Q(nota__length__lte=500),name='resolucion_nota_limite')]

class SesionTecnica(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    permiso=models.ForeignKey(PermisoSoporte,on_delete=PROTECT)
    administrador=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT)
    iniciada_en=models.DateTimeField(default=timezone.now,editable=False)
    cerrada_en=models.DateTimeField(null=True,blank=True)
    motivo_cierre=models.CharField(max_length=24,blank=True,default='')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['administrador'],condition=Q(cerrada_en__isnull=True),name='tecnica_admin_una_abierta'),
         models.CheckConstraint(condition=(Q(cerrada_en__isnull=True)&Q(motivo_cierre=''))|
         (Q(cerrada_en__isnull=False,cerrada_en__gte=F('iniciada_en'))&Q(motivo_cierre__in=['explicit','revoked','replaced','logout','expiry','resolved'])),name='sesion_tecnica_cierre_valido')]
        indexes=[models.Index(fields=['administrador','cerrada_en'],name='tecnica_admin_cierre_idx')]

class ValidacionVersion(models.Model):
    TIPOS=[(x,x) for x in ['weights','math','rollback']]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT)
    tipo=models.CharField(max_length=12,choices=TIPOS)
    version=models.CharField(max_length=64)
    notas=models.TextField(blank=True,default='')
    validada_en=models.DateTimeField(default=timezone.now,editable=False)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(tipo__in=['weights','math','rollback']),name='version_tipo_valido'),
         models.CheckConstraint(condition=Q(version__regex=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{2,63}$'),name='version_formato_valido'),
         models.CheckConstraint(condition=Q(notas__length__lte=2000),name='version_notas_limite')]

class RevisionConocimiento(models.Model):
    # Global ordered revision; previous content is retained.
    autor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT)
    contenido=models.TextField()
    creada_en=models.DateTimeField(default=timezone.now,editable=False)
    class Meta:
        constraints=[nonblank('contenido','conocimiento_significativo'),
          models.CheckConstraint(condition=Q(contenido__length__gte=20,contenido__length__lte=10000),name='conocimiento_longitud')]

class Solicitud(models.Model):
    TIPOS=[(x,x) for x in ['water','lamp-off','lamp-auto','weights','math','rollback','restart-node','restart-platform']]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT)
    tipo=models.CharField(max_length=20,choices=TIPOS)
    huerto=models.ForeignKey('huerto.Huerto',null=True,blank=True,on_delete=PROTECT)
    dispositivo=models.ForeignKey(Dispositivo,null=True,blank=True,on_delete=PROTECT)
    sesion_tecnica=models.ForeignKey(SesionTecnica,null=True,blank=True,on_delete=PROTECT)
    validacion=models.OneToOneField(ValidacionVersion,null=True,blank=True,on_delete=PROTECT)
    creada_en=models.DateTimeField(default=timezone.now,editable=False)
    estado=models.CharField(max_length=16,default='pending',editable=False)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(estado='pending'),name='solicitud_sin_actuacion'),
         models.CheckConstraint(condition=Q(tipo__in=['water','lamp-off','lamp-auto','weights','math','rollback','restart-node','restart-platform']),name='solicitud_tipo_valido'),
         models.CheckConstraint(condition=(Q(tipo__in=['water','lamp-off','lamp-auto'],huerto__isnull=False,dispositivo__isnull=False,sesion_tecnica__isnull=True,validacion__isnull=True)|
          Q(tipo='restart-node',huerto__isnull=False,dispositivo__isnull=False,sesion_tecnica__isnull=False,validacion__isnull=True)|
          Q(tipo__in=['weights','math','rollback'],huerto__isnull=True,dispositivo__isnull=True,sesion_tecnica__isnull=True,validacion__isnull=False)|
          Q(tipo='restart-platform',huerto__isnull=True,dispositivo__isnull=True,sesion_tecnica__isnull=True,validacion__isnull=True)),name='solicitud_referencias_por_tipo')]
        indexes=[models.Index(fields=['huerto','-creada_en'],name='solicitud_huerto_fecha_idx')]

class CodigoVinculacion(models.Model):
    """Código temporal de un solo uso que asocia un huerto a una cuenta concreta.

    El código nunca se guarda: solo su resumen con el algoritmo de contraseñas de Django.
    «Vencido» no es un estado guardado: se deduce de vence_en.
    """
    ENTREGAS=[('presencial','Presencial'),('correo','Correo verificado')]
    ESTADOS=[('pendiente','Pendiente'),('consumido','Consumido'),('revocado','Revocado'),
             ('reemplazado','Reemplazado'),('bloqueado','Bloqueado por intentos')]
    ENVIOS=[('no_aplica','No aplica'),('pendiente','Pendiente'),('aceptado_smtp','Aceptado por SMTP'),
            ('rechazado','Rechazado'),('incierto','Resultado incierto')]
    VIGENCIA=timedelta(minutes=10)
    MAX_INTENTOS=5
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    huerto=models.ForeignKey('huerto.Huerto',on_delete=PROTECT)
    destinatario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT,related_name='codigos_vinculacion')
    emitido_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT,related_name='codigos_vinculacion_emitidos')
    entrega=models.CharField(max_length=10,choices=ENTREGAS)
    verificador=models.CharField(max_length=128)
    emitido_en=models.DateTimeField(default=timezone.now,editable=False)
    vence_en=models.DateTimeField()
    intentos=models.PositiveSmallIntegerField(default=0)
    estado=models.CharField(max_length=12,choices=ESTADOS,default='pendiente')
    envio=models.CharField(max_length=14,choices=ENVIOS)
    cerrado_en=models.DateTimeField(null=True,blank=True)
    membresia=models.OneToOneField('huerto.Membresia',null=True,blank=True,on_delete=PROTECT,related_name='codigo_vinculacion')
    class Meta:
        constraints=[
          models.CheckConstraint(condition=Q(entrega__in=['presencial','correo']),name='vinculacion_entrega_valida'),
          models.CheckConstraint(condition=Q(estado__in=['pendiente','consumido','revocado','reemplazado','bloqueado']),name='vinculacion_estado_valido'),
          models.CheckConstraint(condition=(Q(entrega='presencial',envio='no_aplica')|
            Q(entrega='correo',envio__in=['pendiente','aceptado_smtp','rechazado','incierto'])),name='vinculacion_envio_coherente'),
          # Formato de resumen de Django (algoritmo$...), nunca el código en claro.
          models.CheckConstraint(condition=Q(verificador__regex=r'^[a-z0-9_]+\$[^$]+\$'),name='vinculacion_verificador_resumido'),
          models.CheckConstraint(condition=Q(vence_en__gt=F('emitido_en'),vence_en__lte=F('emitido_en')+timedelta(minutes=10)),name='vinculacion_vigencia_maxima'),
          models.CheckConstraint(condition=Q(intentos__lte=5),name='vinculacion_intentos_limite'),
          models.CheckConstraint(condition=(Q(estado='pendiente',cerrado_en__isnull=True,membresia__isnull=True)|
            Q(estado='consumido',cerrado_en__isnull=False,membresia__isnull=False)|
            Q(estado__in=['revocado','reemplazado','bloqueado'],cerrado_en__isnull=False,membresia__isnull=True)),name='vinculacion_cierre_coherente'),
          models.UniqueConstraint(fields=['huerto'],condition=Q(estado='pendiente'),name='vinculacion_pendiente_por_huerto'),
          models.UniqueConstraint(fields=['destinatario'],condition=Q(estado='pendiente'),name='vinculacion_pendiente_por_cuenta')]
        indexes=[models.Index(fields=['estado','-emitido_en'],name='vinculacion_estado_fecha_idx'),
                 models.Index(fields=['huerto','destinatario','entrega'],name='vinculacion_entrega_idx')]

class GuiaCuidado(models.Model):
    # Contenido del sitio: no pertenece a ninguna cuenta. Los actores son referencias estables, sin correo.
    # creado_por y actualizado_por son nulos solo en la carga inicial. Nunca se borra: se retira.
    ESTADOS=[(x,x) for x in ['borrador','publicada','retirada']]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    clave=models.CharField(max_length=64,unique=True,editable=False)
    pregunta=models.CharField(max_length=200)
    respuesta=models.TextField()
    orden=models.PositiveIntegerField()
    estado=models.CharField(max_length=10,choices=ESTADOS,default='borrador')
    fuente_nombre=models.CharField(max_length=120,blank=True,default='')
    fuente_url=models.CharField(max_length=500,blank=True,default='')
    version=models.PositiveIntegerField(default=1)
    creado_en=models.DateTimeField(default=timezone.now,editable=False)
    actualizado_en=models.DateTimeField(default=timezone.now)
    creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=PROTECT,related_name='guias_creadas')
    actualizado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=PROTECT,related_name='guias_actualizadas')
    class Meta:
        constraints=[nonblank('pregunta','guia_pregunta_significativa'),nonblank('respuesta','guia_respuesta_significativa'),
         models.CheckConstraint(condition=Q(respuesta__length__lte=4000),name='guia_respuesta_limite'),
         models.CheckConstraint(condition=Q(clave__regex=r'^[a-z0-9]+(-[a-z0-9]+)*$'),name='guia_clave_valida'),
         models.CheckConstraint(condition=Q(orden__gte=1,orden__lte=9999),name='guia_orden_valido'),
         models.CheckConstraint(condition=Q(estado__in=['borrador','publicada','retirada']),name='guia_estado_valido'),
         models.CheckConstraint(condition=Q(version__gte=1),name='guia_version_valida'),
         models.CheckConstraint(condition=Q(fuente_url='')|(Q(fuente_url__regex=r'^https?://[^[:space:]]+$')&~Q(fuente_nombre='')),name='guia_fuente_valida')]
        indexes=[models.Index(fields=['estado','orden'],name='guia_estado_orden_idx')]

class Auditoria(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=PROTECT)
    accion=models.CharField(max_length=32)
    resultado=models.CharField(max_length=16,default='recorded')
    creada_en=models.DateTimeField(default=timezone.now,editable=False)
    huerto=models.ForeignKey('huerto.Huerto',null=True,blank=True,on_delete=PROTECT)
    caso=models.ForeignKey(CasoSoporte,null=True,blank=True,on_delete=PROTECT)
    permiso=models.ForeignKey(PermisoSoporte,null=True,blank=True,on_delete=PROTECT)
    solicitud=models.ForeignKey(Solicitud,null=True,blank=True,on_delete=PROTECT)
    mantenimiento=models.ForeignKey(Mantenimiento,null=True,blank=True,on_delete=PROTECT)
    sesion_tecnica=models.ForeignKey(SesionTecnica,null=True,blank=True,on_delete=PROTECT)
    validacion=models.ForeignKey(ValidacionVersion,null=True,blank=True,on_delete=PROTECT)
    conocimiento=models.ForeignKey(RevisionConocimiento,null=True,blank=True,on_delete=PROTECT)
    revision_mantenimiento=models.ForeignKey(RevisionMantenimiento,null=True,blank=True,on_delete=PROTECT)
    vinculacion=models.ForeignKey(CodigoVinculacion,null=True,blank=True,on_delete=PROTECT)
    guia=models.ForeignKey(GuiaCuidado,null=True,blank=True,on_delete=PROTECT)
    # Only fixed action codes and object references; no token, password or free-text detail.
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(accion__in=['maintenance','support-granted','support-revoked','token-requested','technical-opened','technical-closed','diagnostic-requested','request-recorded','version-validated','knowledge-saved','maintenance-corrected','maintenance-voided','case-resolved','mfa-reset','binding-issued','binding-revoked','binding-replaced','binding-consumed','binding-rejected','binding-locked','binding-limited','guide-created','guide-updated','guide-published','guide-withdrawn']),name='auditoria_accion_valida'),
          # Editar ajeno se audita por la revisión: la regla actor = autor de mantenimiento sigue intacta.
          models.CheckConstraint(condition=(Q(accion__in=['maintenance-corrected','maintenance-voided'],revision_mantenimiento__isnull=False,mantenimiento__isnull=True)|
           (~Q(accion__in=['maintenance-corrected','maintenance-voided'])&Q(revision_mantenimiento__isnull=True))),name='auditoria_revision_coherente'),
          models.CheckConstraint(condition=(Q(accion__startswith='guide-',guia__isnull=False)|(~Q(accion__startswith='guide-')&Q(guia__isnull=True))),name='auditoria_guia_coherente'),
          models.CheckConstraint(condition=Q(resultado__in=['recorded','pending']),name='auditoria_resultado_valido')]
        indexes=[models.Index(fields=['actor','-creada_en'],name='auditoria_actor_fecha_idx')]


class ConsultaProducto(models.Model):
    """Consulta de interés del formulario público. No es pedido, pago ni suscripción.
    El contenido no cambia; solo avanza su atención: nueva -> atendida -> archivada."""
    ESTADOS=[('nueva','Nueva'),('atendida','Atendida'),('archivada','Archivada')]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    recibida_en=models.DateTimeField(default=timezone.now,editable=False)
    nombre=models.CharField(max_length=100,blank=True,default='')
    correo=models.CharField(max_length=254)
    mensaje=models.TextField()
    huella=models.CharField(max_length=64,editable=False)
    estado=models.CharField(max_length=10,choices=ESTADOS,default='nueva')
    atendida_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=PROTECT,related_name='consultas_atendidas')
    atendida_en=models.DateTimeField(null=True,blank=True)
    class Meta:
        constraints=[nonblank('correo','consulta_correo_significativo'),nonblank('mensaje','consulta_mensaje_significativo'),
         models.CheckConstraint(condition=Q(mensaje__length__lte=2000),name='consulta_mensaje_limite'),
         models.CheckConstraint(condition=Q(huella__regex=r'^[0-9a-f]{64}$'),name='consulta_huella_valida'),
         models.CheckConstraint(condition=Q(estado__in=['nueva','atendida','archivada']),name='consulta_estado_valido'),
         models.CheckConstraint(condition=(Q(estado='nueva',atendida_por__isnull=True,atendida_en__isnull=True))|
           (Q(estado__in=['atendida','archivada'],atendida_por__isnull=False,atendida_en__isnull=False)),name='consulta_atencion_coherente')]
        indexes=[models.Index(fields=['estado','-recibida_en'],name='consulta_estado_fecha_idx'),
                 models.Index(fields=['huella','-recibida_en'],name='consulta_huella_idx')]


class AvisoCorreo(models.Model):
    """Cola de avisos automáticos. No guarda destinatario ni cuerpo: se calculan al enviar,
    así el registro no duplica datos personales ni puede contener un token.
    aceptado_smtp significa que el servidor de correo lo aceptó, no que llegó a la bandeja."""
    TIPOS=[('caso_nuevo','Caso de soporte nuevo'),('token_solicitado','Soporte solicita el token'),('consulta_nueva','Consulta del producto nueva')]
    ESTADOS=[('pendiente','Pendiente'),('aceptado_smtp','Aceptado por SMTP'),('fallido','Fallido')]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    tipo=models.CharField(max_length=20,choices=TIPOS)
    caso=models.ForeignKey(CasoSoporte,null=True,blank=True,on_delete=PROTECT)
    consulta=models.ForeignKey(ConsultaProducto,null=True,blank=True,on_delete=PROTECT)
    creado_en=models.DateTimeField(default=timezone.now,editable=False)
    estado=models.CharField(max_length=16,choices=ESTADOS,default='pendiente')
    intentos=models.PositiveSmallIntegerField(default=0)
    ultimo_intento_en=models.DateTimeField(null=True,blank=True)
    aceptado_en=models.DateTimeField(null=True,blank=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(tipo__in=['caso_nuevo','token_solicitado','consulta_nueva']),name='aviso_correo_tipo_valido'),
         models.CheckConstraint(condition=(Q(tipo__in=['caso_nuevo','token_solicitado'],caso__isnull=False,consulta__isnull=True))|
           (Q(tipo='consulta_nueva',caso__isnull=True,consulta__isnull=False)),name='aviso_correo_referencia_coherente'),
         models.CheckConstraint(condition=Q(estado__in=['pendiente','aceptado_smtp','fallido']),name='aviso_correo_estado_valido'),
         models.CheckConstraint(condition=Q(intentos__lte=5),name='aviso_correo_intentos_limite'),
         models.CheckConstraint(condition=(Q(estado='aceptado_smtp',aceptado_en__isnull=False))|(~Q(estado='aceptado_smtp')&Q(aceptado_en__isnull=True)),name='aviso_correo_aceptacion_coherente'),
         # Un solo aviso de caso nuevo por caso y de consulta nueva por consulta.
         models.UniqueConstraint(fields=['caso'],condition=Q(tipo='caso_nuevo'),name='aviso_correo_caso_unico'),
         models.UniqueConstraint(fields=['consulta'],condition=Q(tipo='consulta_nueva'),name='aviso_correo_consulta_unico')]
        indexes=[models.Index(fields=['estado','creado_en'],name='aviso_correo_pendientes_idx')]
