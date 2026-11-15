"""Frontera de persistencia de confianza (no es una API HTTP): se llama con el `request.user` ya autenticado.

Los ID del navegador solo identifican recursos; el actor y el rol nunca se toman de lo que envía el cliente."""
import hashlib, hmac, re, secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Exists,F,OuterRef,Q,Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from huerto.models import Huerto, Membresia, Aviso, AvisoLeido
from . import avisos_correo
from .models import (AvisoCorreo,ConsultaProducto,ResolucionSoporte,AsignacionMantenimiento,Dispositivo,Mantenimiento,CasoSoporte,PermisoSoporte,RevisionMantenimiento,
                     SesionTecnica,Solicitud,Auditoria)
CAPS={'ver_flota','atender_soporte','gestionar_mantenimientos','atender_consultas','vincular_huertos','gestionar_guias'}

class FactorRequerido(PermissionDenied):
    """Administrador sin TOTP ni WebAuthn: puede entrar a su cuenta, no al panel."""

class GardenUnassigned(Exception):
    """La cuenta no tiene ningún huerto activo."""

class RegistroDesactualizado(Exception):
    """Otra persona revisó el registro después de que este editor lo consultara."""
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

def strong_factor(user):
    return Authenticator.objects.filter(user=user,type__in=[Authenticator.Type.TOTP,Authenticator.Type.WEBAUTHN]).exists()

def require_cap(actor,cap):
    user=identity(actor)
    if cap not in capabilities(user): raise PermissionDenied('Capacidad requerida')
    if not strong_factor(user): raise FactorRequerido('Segundo factor requerido')
    return user

def session_contract(actor):
    user=identity(actor); caps=sorted(capabilities(user))
    return {'status':'authenticated','sessionConfirmed':True,'role':'admin' if caps else 'user',
            'capabilities':caps,'mfaRequired':bool(caps) and not strong_factor(user),'profile':{'id':str(user.pk),'email':user.email,'verified':True,'status':'ready',
             'firstName':user.first_name,'lastName':user.last_name,'alias':user.alias,
             'greeting':user.nombre_presentacion,'welcomePending':user.bienvenida_atendida_en is None}}

def current_garden(actor):
    user=identity(actor)
    query=Membresia.objects.filter(usuario=user,activa=True).select_related('huerto')
    row=query.filter(huerto__clave='principal').first() or query.order_by('huerto_id').first()
    if not row:raise GardenUnassigned
    return row.huerto_id

def has_garden(actor):
    return Membresia.objects.filter(usuario=identity(actor),activa=True).exists()

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

def _maintenance_state(query):
    # Único criterio de estado vigente para usuario y administrador.
    revisions=RevisionMantenimiento.objects.filter(mantenimiento=OuterRef('pk'))
    return query.annotate(anulado=Exists(revisions.filter(tipo='anulacion')),
        tipo_vigente=Coalesce(Subquery(revisions.filter(tipo='correccion').order_by('-numero').values('tipo_corregido')[:1]),F('tipo')),
        revision=Coalesce(Subquery(revisions.order_by('-numero').values('numero')[:1]),0))

def maintenance_history(actor,garden_id):
    member(actor,garden_id)
    return _maintenance_state(Mantenimiento.objects.filter(huerto_id=garden_id)).filter(anulado=False).order_by('-registrado_en','id')

def maintenance_scope(actor,garden_id):
    admin=require_cap(actor,'gestionar_mantenimientos')
    if not AsignacionMantenimiento.objects.filter(usuario=admin,huerto_id=garden_id,activa=True).exists():
        raise PermissionDenied('Huerto no asignado')
    return admin

def assigned_gardens(actor):
    admin=require_cap(actor,'gestionar_mantenimientos')
    return Huerto.objects.filter(asignacionmantenimiento__usuario=admin,asignacionmantenimiento__activa=True).order_by('nombre')

def admin_maintenance(actor,*,garden_id=None,state=None,task=None,since=None,until=None):
    gardens=assigned_gardens(actor)
    query=_maintenance_state(Mantenimiento.objects.filter(huerto__in=gardens)).select_related('huerto')
    if garden_id is not None:query=query.filter(huerto_id=garden_id)
    if state is not None:query=query.filter(anulado=state=='voided')
    if task is not None:query=query.filter(tipo_vigente=task)
    if since is not None:query=query.filter(registrado_en__date__gte=since)
    if until is not None:query=query.filter(registrado_en__date__lte=until)
    return query.order_by('-registrado_en','id')

def maintenance_detail(actor,record_id):
    row=_maintenance_state(Mantenimiento.objects.filter(pk=record_id)).select_related('huerto').get()
    maintenance_scope(actor,row.huerto_id)
    return row,list(RevisionMantenimiento.objects.filter(mantenimiento=row).order_by('numero'))

@transaction.atomic
def admin_record_maintenance(actor,garden_id,task):
    admin=maintenance_scope(actor,garden_id)
    if task not in dict(Mantenimiento.TIPOS):raise ValidationError('Tarea no válida')
    record=Mantenimiento.objects.create(actor=admin,huerto_id=garden_id,tipo=task)
    audit(admin,'maintenance',huerto_id=garden_id,mantenimiento=record)
    return _maintenance_state(Mantenimiento.objects.filter(pk=record.pk)).select_related('huerto').get()

def _revise(actor,record_id,kind,reason,seen,corrected=None):
    if not isinstance(reason,str) or not 1<=len(reason.strip())<=500:raise ValidationError('Motivo no válido')
    if not isinstance(seen,int) or isinstance(seen,bool) or seen<0:raise ValidationError('Revisión no válida')
    garden=Mantenimiento.objects.values_list('huerto_id',flat=True).get(pk=record_id)
    admin=maintenance_scope(actor,garden)
    record=Mantenimiento.objects.select_for_update().get(pk=record_id)
    current=_maintenance_state(Mantenimiento.objects.filter(pk=record_id)).get()
    # Comparar con lo que vio el editor evita que una decisión se base en datos ya cambiados.
    if current.revision!=seen or current.anulado:raise RegistroDesactualizado
    if corrected==current.tipo_vigente:raise ValidationError('El tipo no cambia')
    revision=RevisionMantenimiento.objects.create(mantenimiento=record,numero=seen+1,tipo=kind,tipo_corregido=corrected,
                                                  editor=admin,motivo=reason.strip())
    audit(admin,'maintenance-corrected' if kind=='correccion' else 'maintenance-voided',huerto_id=record.huerto_id,revision_mantenimiento=revision)
    return _maintenance_state(Mantenimiento.objects.filter(pk=record_id)).select_related('huerto').get()

@transaction.atomic
def correct_maintenance(actor,record_id,task,reason,seen):
    if task not in dict(Mantenimiento.TIPOS):raise ValidationError('Tarea no válida')
    return _revise(actor,record_id,'correccion',reason,seen,task)

@transaction.atomic
def void_maintenance(actor,record_id,reason,seen):
    return _revise(actor,record_id,'anulacion',reason,seen)

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
    avisos_correo.encolar('caso_nuevo',caso=case)
    # Only successful issuance returns raw token, once. Never stored or logged.
    return {'status':'accepted','permission':{'token':token,'ticket':str(case.pk),'folio':avisos_correo.folio_caso(case),
        'supportEmail':settings.CHILITO_CONTACTO_SOPORTE or None,'device':device.identificador,
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

TOKEN_REQUEST_WINDOW=timedelta(minutes=10)

def is_resolved(case):
    return ResolucionSoporte.objects.filter(caso=case).exists()

@transaction.atomic
def request_support_token(actor,case_id):
    """Avisa a la persona usuaria de que soporte necesita el token. No recupera ni reenvía el secreto."""
    admin=require_cap(actor,'atender_soporte');case,_=_case_lock(case_id)
    if is_resolved(case):raise RegistroDesactualizado('Caso resuelto')
    audit(admin,'token-requested',caso=case,huerto=case.huerto)
    # Dobles pulsaciones o reintentos: un aviso por caso cada 10 minutos.
    recent=AvisoCorreo.objects.filter(caso=case,tipo='token_solicitado',creado_en__gte=timezone.now()-TOKEN_REQUEST_WINDOW).exclude(estado='fallido').first()
    notice=recent or avisos_correo.encolar('token_solicitado',caso=case)
    return {'status':'accepted','notice':notice.estado,'repeated':recent is not None}

@transaction.atomic
def resolve_case(actor,case_id,result,note=''):
    """Cierre expreso por un administrador autorizado. Revoca el permiso y cierra el acceso técnico:
    el mismo token ya no puede abrir otra sesión, aunque no haya vencido."""
    admin=require_cap(actor,'atender_soporte')
    case,_=_case_lock(case_id,admin,eligible=False)
    if result not in dict(ResolucionSoporte.RESULTADOS):raise ValidationError('Resultado no válido')
    note=(note or '').strip()
    if len(note)>500 or (note and not note.replace('\n','').isprintable()):raise ValidationError('Nota no válida')
    if result=='otro' and not note:raise ValidationError('Explica el resultado')
    if is_resolved(case):raise RegistroDesactualizado('Caso ya resuelto')
    now=timezone.now()
    resolution=ResolucionSoporte.objects.create(caso=case,responsable=admin,resultado=result,nota=note,resuelto_en=now)
    for p in PermisoSoporte.objects.select_for_update().filter(caso=case,revocado_en__isnull=True):
        p.revocado_en=now;p.save(update_fields=['revocado_en'])
        _close_permission_sessions(p,'resolved',now)
    audit(admin,'case-resolved',caso=case,huerto=case.huerto)
    return resolution

@transaction.atomic
def open_technical(actor,case_id,token):
    admin=require_cap(actor,'atender_soporte');case,_=_case_lock(case_id,admin)
    if is_resolved(case):raise PermissionDenied('Caso resuelto')
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
def close_actor_sessions(actor,reason):
    # Limpieza al terminar la sesión web: no exige capacidad ni membresía vigentes, porque
    # solo cierra de forma irreversible sesiones de esa misma identidad y nunca concede acceso.
    if reason not in {'logout','expiry'}:raise ValidationError('Motivo no válido')
    sources=list(SesionTecnica.objects.filter(administrador=actor,cerrada_en__isnull=True).select_related('permiso__caso'))
    for source in sources:
        case,_=_case_lock(source.permiso.caso_id,actor,eligible=False)
        permission=PermisoSoporte.objects.select_for_update().get(pk=source.permiso_id)
        session=SesionTecnica.objects.select_for_update().get(pk=source.pk)
        if session.administrador_id!=actor.pk:raise PermissionDenied
        if session.cerrada_en is None:
            session.cerrada_en=timezone.now();session.motivo_cierre=reason;session.save(update_fields=['cerrada_en','motivo_cierre'])
            audit(actor,'technical-closed',caso=case,permiso=permission,huerto=case.huerto,sesion_tecnica=session)

def is_admin(actor):
    # Mismo criterio que session_contract. Una cuenta sin verificar no es administradora.
    try:return bool(capabilities(actor))
    except (PermissionDenied,get_user_model().DoesNotExist):return False

def notices_total(actor,garden_id):
    member(actor,garden_id)
    return Aviso.objects.filter(huerto_id=garden_id).count()

def check_replay(actor,path,kwargs,receipt):
    """Repite la autorización antes de devolver un recibo guardado."""
    if path.startswith('/api/huertos/') or path=='/api/soporte':
        garden=current_garden(actor);member(actor,garden,lock=True)
        if 'notice_id' in kwargs and not Aviso.objects.filter(pk=kwargs['notice_id'],huerto_id=garden).exists():raise PermissionDenied
        if 'record' in receipt:member(actor,Mantenimiento.objects.get(pk=receipt['record']['id']).huerto_id,lock=True)
        if 'request' in receipt:member(actor,Solicitud.objects.get(pk=receipt['request']['id']).huerto_id,lock=True)
        if 'permission' in receipt:
            member(actor,CasoSoporte.objects.get(pk=receipt['permission']['ticket'],solicitante=actor).huerto_id,lock=True)
    elif path.startswith('/api/admin/mantenimientos'):
        maintenance_scope(actor,Mantenimiento.objects.get(pk=receipt['record']['id']).huerto_id)
    elif path=='/api/vinculacion':
        from . import vinculacion
        vinculacion.comprobar_recibo(actor,receipt)
    elif path.startswith('/api/soporte/'):
        member(actor,CasoSoporte.objects.get(pk=kwargs['case_id'],solicitante=actor).huerto_id,lock=True)
    elif 'session_id' in kwargs and not SesionTecnica.objects.filter(pk=kwargs['session_id'],administrador=actor).exists():
        raise PermissionDenied

def fleet_projection(actor):
    require_cap(actor,'ver_flota')
    return {'nodes':[{'device':d.identificador,'gardenId':str(d.huerto_id),'connected':None,'heartbeat':None}
         for d in Dispositivo.objects.order_by('id')[:100]], 'metrics':None,'trends':{'soil':[],'humidity':[]}}

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

def case_dto(case):
    """Estado de atención (abierto/resuelto) separado del estado del permiso y de los avisos."""
    permission=case.permisosoporte_set.order_by('-emitido_en').first()
    state=permission_state(permission) if permission else 'closed'
    resolution=ResolucionSoporte.objects.filter(caso=case).select_related('responsable').first()
    notices={n.tipo:n.estado for n in AvisoCorreo.objects.filter(caso=case).order_by('creado_en')}
    requested=Auditoria.objects.filter(caso=case,accion='token-requested').order_by('-creada_en').values_list('creada_en',flat=True).first()
    return {'id':str(case.pk),'folio':avisos_correo.folio_caso(case),'device':case.dispositivo.identificador,'user':str(case.solicitante_id),
            'incident':case.incidente,'createdAt':case.creado_en.isoformat(),'permissionState':state,
            'expiresAt':int(permission.vence_en.timestamp()*1000) if permission else None,
            'caseState':'resolved' if resolution else 'open',
            'resolution':{'result':resolution.resultado,'note':resolution.nota,'at':resolution.resuelto_en.isoformat()} if resolution else None,
            'tokenRequestedAt':requested.isoformat() if requested else None,
            'notices':{'newCase':notices.get('caso_nuevo'),'tokenRequest':notices.get('token_solicitado')}}

def support_reports(actor,garden_id):
    user=member(actor,garden_id)
    return CasoSoporte.objects.filter(huerto_id=garden_id,solicitante=user).select_related('dispositivo').order_by('-creado_en')

def administrative_reports(actor):
    require_cap(actor,'atender_soporte')
    # Minimal operational identifiers, never token/verifier or household histories.
    return CasoSoporte.objects.select_related('dispositivo').order_by('-creado_en')

def user_requests(actor,garden_id):
    member(actor,garden_id)
    return Solicitud.objects.filter(huerto_id=garden_id,tipo__in=['water','lamp-off','lamp-auto']).order_by('-creada_en')


# Buzón de consultas del producto. Solo con la capacidad explícita atender_consultas y segundo factor.
INQUIRY_WINDOW=timedelta(minutes=10)

def inquiry_fingerprint(email,message):
    return hashlib.sha256((email.strip().lower()+'\n'+message.strip()).encode()).hexdigest()

@transaction.atomic
def record_inquiry(name,email,message):
    """Guarda la consulta y su aviso juntos. Repetir el mismo correo y mensaje en 10 minutos no duplica."""
    fingerprint=inquiry_fingerprint(email,message)
    recent=(ConsultaProducto.objects.select_for_update()
            .filter(huella=fingerprint,recibida_en__gte=timezone.now()-INQUIRY_WINDOW).first())
    if recent:return recent
    inquiry=ConsultaProducto.objects.create(nombre=name,correo=email,mensaje=message,huella=fingerprint)
    avisos_correo.encolar('consulta_nueva',consulta=inquiry)
    return inquiry

def admin_inquiries(actor,state=None):
    require_cap(actor,'atender_consultas')
    rows=ConsultaProducto.objects.select_related('atendida_por').order_by('-recibida_en')
    if state is not None:
        if state not in dict(ConsultaProducto.ESTADOS):raise ValidationError('Estado no válido')
        rows=rows.filter(estado=state)
    return rows

@transaction.atomic
def update_inquiry(actor,inquiry_id,state):
    """Atención de una consulta: nueva -> atendida|archivada, atendida -> archivada, archivada -> atendida.

    Nunca vuelve a «nueva». Marcarla atendida registra quién la atendió y cuándo; archivarla
    después conserva ese dato. Si se archivó sin responder, guarda quién la archivó hasta que se atienda.
    """
    admin=require_cap(actor,'atender_consultas')
    inquiry=ConsultaProducto.objects.select_for_update().get(pk=inquiry_id)
    allowed={'nueva':{'atendida','archivada'},'atendida':{'archivada'},'archivada':{'atendida'}}.get(inquiry.estado,set())
    if state not in allowed:raise RegistroDesactualizado('Transición no válida')
    if inquiry.estado=='nueva' or state=='atendida':inquiry.atendida_por,inquiry.atendida_en=admin,timezone.now()
    inquiry.estado=state
    inquiry.save(update_fields=['estado','atendida_por','atendida_en'])
    return inquiry

def inquiry_dto(row):
    notice=AvisoCorreo.objects.filter(consulta=row).values_list('estado',flat=True).first()
    return {'id':str(row.pk),'folio':avisos_correo.folio_consulta(row),'receivedAt':row.recibida_en.isoformat(),
            'name':row.nombre,'email':row.correo,'message':row.mensaje,'state':row.estado,
            'attendedBy':row.atendida_por.email if row.atendida_por_id else None,
            'attendedAt':row.atendida_en.isoformat() if row.atendida_en else None,'notice':notice}
