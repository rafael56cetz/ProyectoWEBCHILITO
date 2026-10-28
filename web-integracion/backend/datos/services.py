"""Trusted persistence boundary, not an HTTP API. Call with authenticated request.user.
All IDs from the browser identify resources only; never take actor/role from a payload.
"""
import hashlib, hmac, re, secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from allauth.account.models import EmailAddress
from huerto.models import Huerto, Membresia, Aviso, AvisoLeido
from .models import (Dispositivo,Mantenimiento,CasoSoporte,PermisoSoporte,SesionTecnica,
                     ValidacionVersion,RevisionConocimiento,Solicitud,Auditoria)
CAPS={'ver_flota','atender_soporte','ver_gobernanza','gestionar_cambios'}
TOKEN_RE=re.compile(r'^[A-Za-z0-9_-]{43}$',re.ASCII)

def identity(actor):
    if not getattr(actor,'is_authenticated',False) or not getattr(actor,'pk',None):
        raise PermissionDenied('Sesión requerida')
    user=get_user_model().objects.get(pk=actor.pk)
    if not user.is_active or not EmailAddress.objects.filter(user=user,email__iexact=user.email,verified=True).exists():
        raise PermissionDenied('Cuenta activa y verificada requerida')
    return user

def capabilities(actor):
    user=identity(actor)
    # Explicit grants only. Django's implicit superuser bypass is deliberately not used.
    return set(Permission.objects.filter(Q(user=user)|Q(group__user=user),
        content_type__app_label='datos',codename__in=CAPS).values_list('codename',flat=True))

def require_cap(actor,cap):
    user=identity(actor)
    if cap not in capabilities(user): raise PermissionDenied('Capacidad requerida')
    return user

def session_contract(actor):
    user=identity(actor); caps=sorted(capabilities(user))
    return {'status':'authenticated','sessionConfirmed':True,'role':'admin' if caps else 'user',
            'capabilities':caps,'profile':{'id':str(user.pk),'email':user.email,'verified':True,'status':'ready'}}

def member(actor,garden_id,lock=False):
    user=identity(actor)
    query=Membresia.objects.select_for_update() if lock else Membresia.objects
    if not query.filter(usuario=user,huerto_id=garden_id,activa=True).exists():
        raise PermissionDenied('Sin membresía activa')
    return user

def audit(actor,action,**refs):
    # No free text, tokens, emails, client-provided metadata or exception bodies.
    return Auditoria.objects.create(actor=actor,accion=action,**refs)

def token_verifier(token):
    if not isinstance(token,str) or not TOKEN_RE.fullmatch(token):
        raise PermissionDenied('Autorización no válida')
    key=settings.CHILITO_SUPPORT_KEY
    if not isinstance(key,str) or len(key.encode())<32:
        raise ValidationError('Falta clave externa de soporte de al menos 32 bytes')
    return hmac.new(key.encode(),token.encode('ascii'),hashlib.sha256).hexdigest()

def permission_state(p,now=None):
    now=now or timezone.now()
    return 'revoked' if p.revocado_en else 'expired' if p.vence_en<=now else 'active'

@transaction.atomic
def record_maintenance(actor,garden_id,task):
    user=member(actor,garden_id,lock=True)
    if task not in dict(Mantenimiento.TIPOS): raise ValidationError('Tarea no válida')
    record=Mantenimiento.objects.create(actor=user,huerto_id=garden_id,tipo=task)
    audit(user,'maintenance',huerto_id=garden_id,mantenimiento=record)
    return record

def maintenance_history(actor,garden_id):
    member(actor,garden_id)
    return Mantenimiento.objects.filter(huerto_id=garden_id).order_by('-registrado_en','id')

@transaction.atomic
def mark_notice_read(actor,notice_id):
    user=identity(actor)
    notice=Aviso.objects.get(pk=notice_id)
    member(user,notice.huerto_id,lock=True)
    item,_=AvisoLeido.objects.get_or_create(aviso=notice,usuario=user,defaults={'leido_en':timezone.now()})
    return item

@transaction.atomic
def record_user_request(actor,garden_id,kind):
    user=member(actor,garden_id,lock=True)
    if kind not in {'water','lamp-off','lamp-auto'}: raise ValidationError('Solicitud no válida')
    device=Dispositivo.objects.get(huerto_id=garden_id)
    # This is a durable request, never a command dispatch or physical success.
    request=Solicitud.objects.create(actor=user,tipo=kind,huerto_id=garden_id,dispositivo=device)
    audit(user,'request-recorded',huerto_id=garden_id,solicitud=request,resultado='pending')
    return request

def _owner_lock(user_id):
    # All support actions lock the grantor first, then membership, case, permission,
    # technical session. Revocation and use are ordered by this database mutex.
    user=get_user_model().objects.select_for_update().get(pk=user_id)
    return user

def _case_lock(case_id,admin=None,eligible=True):
    source=CasoSoporte.objects.get(pk=case_id)
    # Lock subjects by stable numeric order, including the administrator when present.
    ids={source.solicitante_id}
    if admin is not None:ids.add(admin.pk)
    owner=None
    for user_id in sorted(ids):
        locked=_owner_lock(user_id)
        if user_id==source.solicitante_id:owner=locked
    if eligible:
        if admin is not None:require_cap(admin,'atender_soporte')
        member(owner,source.huerto_id,lock=True)
    case=CasoSoporte.objects.select_for_update().get(pk=source.pk)
    return case,owner

def _close_permission_sessions(permission,reason,now):
    SesionTecnica.objects.filter(permiso=permission,cerrada_en__isnull=True).update(cerrada_en=now,motivo_cierre=reason)

@transaction.atomic
def issue_support(actor,garden_id,incident,consent,*,duration=timedelta(hours=24)):
    user=identity(actor); user=_owner_lock(user.pk)
    member(user,garden_id,lock=True)
    if consent is not True or incident not in dict(CasoSoporte.INCIDENTES):
        raise ValidationError('Incidente y autorización explícita requeridos')
    if not timedelta(0)<duration<=timedelta(hours=24): raise ValidationError('Vigencia no válida')
    device=Dispositivo.objects.get(huerto_id=garden_id)
    token=secrets.token_urlsafe(32); verifier=token_verifier(token)
    now=timezone.now()
    # Existing UI replaces the grantor's previous authorization, retaining reports.
    for p in PermisoSoporte.objects.select_for_update().filter(otorgante=user,revocado_en__isnull=True,vence_en__gt=now):
        p.revocado_en=now;p.save(update_fields=['revocado_en'])
        _close_permission_sessions(p,'replaced',now)
        audit(user,'support-revoked',caso=p.caso,permiso=p,huerto=p.caso.huerto)
    case=CasoSoporte.objects.create(huerto_id=garden_id,dispositivo=device,solicitante=user,incidente=incident,creado_en=now)
    p=PermisoSoporte.objects.create(caso=case,otorgante=user,verificador=verifier,emitido_en=now,vence_en=now+duration)
    audit(user,'support-granted',caso=case,permiso=p,huerto_id=garden_id)
    # Only successful issuance returns raw token, once. Never stored or logged.
    return {'status':'accepted','permission':{'token':token,'ticket':str(case.pk),'device':device.identificador,
        'user':str(user.pk),'createdAt':int(now.timestamp()*1000),'expiresAt':int(p.vence_en.timestamp()*1000)}}

@transaction.atomic
def revoke_support(actor,case_id):
    user=identity(actor)
    case,owner=_case_lock(case_id)
    if owner.pk!=user.pk:raise PermissionDenied('Caso ajeno')
    now=timezone.now()
    for p in PermisoSoporte.objects.select_for_update().filter(caso=case,revocado_en__isnull=True):
        p.revocado_en=now;p.save(update_fields=['revocado_en'])
        _close_permission_sessions(p,'revoked',now)
        audit(user,'support-revoked',caso=case,permiso=p,huerto=case.huerto)
    return {'status':'accepted'}

@transaction.atomic
def request_support_token(actor,case_id):
    admin=require_cap(actor,'atender_soporte');case,_=_case_lock(case_id)
    audit(admin,'token-requested',caso=case,huerto=case.huerto)
    return {'status':'accepted'}

@transaction.atomic
def open_technical(actor,case_id,token):
    admin=require_cap(actor,'atender_soporte');case,_=_case_lock(case_id,admin)
    verifier=token_verifier(token)
    p=PermisoSoporte.objects.select_for_update().filter(caso=case,verificador=verifier).first()
    if not p or permission_state(p)!='active':raise PermissionDenied('Autorización no válida')
    if not hmac.compare_digest(verifier,p.verificador):raise PermissionDenied('Autorización no válida')
    now=timezone.now()
    SesionTecnica.objects.filter(administrador=admin,cerrada_en__isnull=True).update(cerrada_en=now,motivo_cierre='replaced')
    session=SesionTecnica.objects.create(permiso=p,administrador=admin,iniciada_en=now)
    audit(admin,'technical-opened',caso=case,permiso=p,huerto=case.huerto,sesion_tecnica=session)
    return session

@transaction.atomic
def technical_action(actor,session_id,action):
    admin=require_cap(actor,'atender_soporte')
    source=SesionTecnica.objects.select_related('permiso__caso').get(pk=session_id)
    case,_=_case_lock(source.permiso.caso_id,admin)
    p=PermisoSoporte.objects.select_for_update().get(pk=source.permiso_id)
    session=SesionTecnica.objects.select_for_update().get(pk=source.pk)
    if session.administrador_id!=admin.pk or session.cerrada_en is not None or permission_state(p)!='active':
        raise PermissionDenied('Sesión técnica no vigente')
    if action=='diagnostic':
        audit(admin,'diagnostic-requested',caso=case,permiso=p,huerto=case.huerto,sesion_tecnica=session)
        return {'status':'accepted','pins':[],'logs':[],'at':None,'source':'unavailable'}
    if action=='restart-node':
        request=Solicitud.objects.create(actor=admin,tipo=action,huerto=case.huerto,dispositivo=case.dispositivo,sesion_tecnica=session)
        audit(admin,'request-recorded',caso=case,permiso=p,huerto=case.huerto,solicitud=request,resultado='pending')
        return request
    raise ValidationError('Operación no válida')

@transaction.atomic
def close_technical(actor,session_id,reason='explicit'):
    admin=identity(actor)
    source=SesionTecnica.objects.select_related('permiso__caso').get(pk=session_id)
    case,_=_case_lock(source.permiso.caso_id,admin,eligible=False)
    session=SesionTecnica.objects.select_for_update().get(pk=session_id)
    if session.administrador_id!=admin.pk:raise PermissionDenied('Sesión ajena')
    if reason not in {'explicit','logout'}:raise ValidationError('Motivo no válido')
    if session.cerrada_en is None:
        session.cerrada_en=timezone.now();session.motivo_cierre=reason;session.save(update_fields=['cerrada_en','motivo_cierre'])
        audit(admin,'technical-closed',caso=case,permiso=session.permiso,huerto=case.huerto,sesion_tecnica=session)

@transaction.atomic
def validate_version(actor,kind,version,notes=''):
    admin=require_cap(actor,'gestionar_cambios')
    if not isinstance(version,str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{2,63}',version):raise ValidationError('Versión no válida')
    if kind not in dict(ValidacionVersion.TIPOS) or not isinstance(notes,str) or len(notes)>2000:raise ValidationError('Datos no válidos')
    row=ValidacionVersion.objects.create(actor=admin,tipo=kind,version=version,notas=notes)
    audit(admin,'version-validated',validacion=row);return row

@transaction.atomic
def request_deployment(actor,validation_id):
    admin=require_cap(actor,'gestionar_cambios')
    row=ValidacionVersion.objects.select_for_update().get(pk=validation_id)
    if row.actor_id!=admin.pk:raise PermissionDenied('Validación ajena')
    request=Solicitud.objects.create(actor=admin,tipo=row.tipo,validacion=row)
    audit(admin,'request-recorded',solicitud=request,resultado='pending');return request

@transaction.atomic
def save_knowledge(actor,content):
    admin=require_cap(actor,'gestionar_cambios')
    if not isinstance(content,str) or not 20<=len(content.strip())<=10000:raise ValidationError('Contenido no válido')
    revision=RevisionConocimiento.objects.create(autor=admin,contenido=content.strip())
    audit(admin,'knowledge-saved',conocimiento=revision);return revision

@transaction.atomic
def request_platform_restart(actor):
    admin=require_cap(actor,'gestionar_cambios')
    request=Solicitud.objects.create(actor=admin,tipo='restart-platform')
    audit(admin,'request-recorded',solicitud=request,resultado='pending');return request

def fleet_projection(actor):
    require_cap(actor,'ver_flota')
    return {'nodes':[{'device':d.identificador,'gardenId':str(d.huerto_id),'connected':None,'heartbeat':None}
         for d in Dispositivo.objects.order_by('id')[:100]], 'metrics':None,'trends':{'soil':[],'humidity':[]}}

def governance_projection(actor):
    require_cap(actor,'ver_gobernanza')
    return {'scope':'diagnostico_incidente','maximumSeconds':86400,'defaultAccess':'denied'}

def garden_projection(actor,garden_id):
    member(actor,garden_id)
    garden=Huerto.objects.get(pk=garden_id)
    zones=list(garden.zona_set.order_by('numero'))
    if [z.numero for z in zones]!=[1,2,3]:raise ValidationError('Configuración incompleta')
    def missing():return {'value':None,'quality':'missing','at':None}
    return {'status':'waiting','name':garden.nombre,'updatedAt':None,
      'plants':[{'id':z.numero,'zoneId':str(z.pk),'name':z.nombre,'crop':z.cultivo,'reading':missing()} for z in zones],
      'temperature':missing(),'humidity':missing(),'tank':{'state':'unknown','at':None}}

def notices_projection(actor,garden_id,*,offset=0,limit=None,notice_id=None):
    user=member(actor,garden_id)
    query=Aviso.objects.filter(huerto_id=garden_id).select_related('zona').order_by('-creado_en','-id')
    if notice_id is not None:query=query.filter(pk=notice_id)
    query=query[offset:offset+limit] if limit is not None else query[offset:]
    selected=list(query)
    read=set(AvisoLeido.objects.filter(usuario=user,aviso_id__in=[n.pk for n in selected]).values_list('aviso_id',flat=True))
    return [{'id':str(n.pk),'title':n.titulo,'description':n.descripcion,'recommendation':n.recomendacion,
             'zone':n.zona.nombre if n.zona_id else 'Huerto','createdAt':n.creado_en.isoformat(),
             'resolvedAt':n.resuelto_en.isoformat() if n.resuelto_en else None,
             'importance':{'informacion':'info','advertencia':'medium','critico':'high'}[n.severidad],
             'condition':'resolved' if n.resuelto_en else 'active','read':n.pk in read}
            for n in selected]

def _case_dto(case):
    permission=case.permisosoporte_set.order_by('-emitido_en').first()
    state=permission_state(permission) if permission else 'closed'
    return {'id':str(case.pk),'device':case.dispositivo.identificador,'user':str(case.solicitante_id),
            'incident':case.incidente,'createdAt':case.creado_en.isoformat(),'permissionState':state,
            'expiresAt':int(permission.vence_en.timestamp()*1000) if permission else None}

def support_reports(actor,garden_id):
    user=member(actor,garden_id)
    return [_case_dto(case) for case in CasoSoporte.objects.filter(huerto_id=garden_id,solicitante=user).select_related('dispositivo').order_by('-creado_en')]

def administrative_reports(actor):
    require_cap(actor,'atender_soporte')
    # Minimal operational identifiers, never token/verifier or household histories.
    return [_case_dto(case) for case in CasoSoporte.objects.select_related('dispositivo').order_by('-creado_en')]

def changes_projection(actor):
    require_cap(actor,'gestionar_cambios')
    latest=RevisionConocimiento.objects.order_by('-id').first()
    return {'activeVersion':None,'knowledge':latest.contenido if latest else '',
      'knowledgeVersion':str(latest.pk) if latest else None,
      'releases':[{'id':str(s.pk),'type':s.tipo,'version':s.validacion.version,
                   'notes':s.validacion.notas,'at':s.creada_en.isoformat(),'status':'pending'}
         for s in Solicitud.objects.filter(validacion__isnull=False).select_related('validacion').order_by('-creada_en')[:100]],
      'audit':[{'id':str(e.pk),'actor':str(e.actor_id),'action':e.accion,'status':e.resultado,
                'at':e.creada_en.isoformat(),'permissionId':str(e.permiso_id) if e.permiso_id else None}
               for e in Auditoria.objects.order_by('-creada_en')[:100]]}

def user_requests(actor,garden_id):
    member(actor,garden_id)
    return Solicitud.objects.filter(huerto_id=garden_id,tipo__in=['water','lamp-off','lamp-auto']).order_by('-creada_en')
