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
                     ('ver_gobernanza','Consultar gobernanza'),('gestionar_cambios','Solicitar cambios administrativos')]

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
         (Q(cerrada_en__isnull=False,cerrada_en__gte=F('iniciada_en'))&Q(motivo_cierre__in=['explicit','revoked','replaced','logout','expiry'])),name='sesion_tecnica_cierre_valido')]
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
    # Only fixed action codes and object references; no token, password or free-text detail.
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(accion__in=['maintenance','support-granted','support-revoked','token-requested','technical-opened','technical-closed','diagnostic-requested','request-recorded','version-validated','knowledge-saved']),name='auditoria_accion_valida'),
          models.CheckConstraint(condition=Q(resultado__in=['recorded','pending']),name='auditoria_resultado_valido')]
        indexes=[models.Index(fields=['actor','-creada_en'],name='auditoria_actor_fecha_idx')]
