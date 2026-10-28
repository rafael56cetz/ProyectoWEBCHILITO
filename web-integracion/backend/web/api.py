"""Same-origin JSON boundary. Authorization lives in validated Django services."""
import hashlib,hmac,json,uuid
from functools import wraps
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied,ValidationError,ObjectDoesNotExist,RequestDataTooBig
from django.db import transaction,connection,IntegrityError,DatabaseError
from django.http import JsonResponse
from django.utils import timezone
from datos import services as s
from datos.models import SesionTecnica,CasoSoporte,Mantenimiento,Solicitud
from huerto.models import Membresia,Aviso
from .models import Idempotencia

class InputError(Exception):pass
class Conflict(Exception):pass
class GardenUnassigned(Exception):pass

def failure(status,code):return JsonResponse({'status':status,'code':code},status=status)
def body(request,allowed):
    if request.content_type!='application/json':raise InputError
    def pairs(items):
        data={}
        for k,v in items:
            if k in data:raise InputError
            data[k]=v
        return data
    data=json.loads(request.body or b'{}',object_pairs_hook=pairs)
    if not isinstance(data,dict) or set(data)-set(allowed):raise InputError
    return data

def text(data,key,maximum=100,required=True):
    value=data.get(key,'' if not required else None)
    if not isinstance(value,str) or len(value)>maximum:raise InputError
    return value

def bounds(request):
    if set(request.GET)-{'page'}:raise InputError
    value=request.GET.get('page','1')
    if not value.isascii() or not value.isdecimal() or not 1<=int(value)<=10000:raise InputError
    return int(value)

def page(items,request,mapper=lambda row:row):
    p=bounds(request);total=items.count()
    return {'status':'ready','items':[mapper(row) for row in items[(p-1)*25:p*25]],'page':p,'total':total}

def quota(request):
    bucket=int(timezone.now().timestamp())//60
    scope='technical' if '/soporte/' in request.path or '/sesiones/' in request.path else 'write'
    ratekey=f'web-rate:{request.user.pk}:{scope}:{bucket}'
    lock=int.from_bytes(hashlib.sha256(ratekey.encode()).digest()[:8],signed=True)
    with transaction.atomic():
        with connection.cursor() as c:c.execute('SELECT pg_advisory_xact_lock(%s)',[lock])
        count=cache.get(ratekey,0)+1
        cache.set(ratekey,count,120)
    return count<=(15 if scope=='technical' else 60)

def replay_guard(request,kwargs,previous):
    # A cached receipt never extends data access after membership/privilege loss.
    if request.path.startswith('/api/huertos/') or request.path=='/api/soporte':
        g=garden_id(request.user);s.member(request.user,g,lock=True)
        if 'notice_id' in kwargs and not Aviso.objects.filter(pk=kwargs['notice_id'],huerto_id=g).exists():raise PermissionDenied
        receipt=previous.respuesta
        if 'record' in receipt:
            row=Mantenimiento.objects.get(pk=receipt['record']['id']);s.member(request.user,row.huerto_id,lock=True)
        if 'request' in receipt:
            row=Solicitud.objects.get(pk=receipt['request']['id']);s.member(request.user,row.huerto_id,lock=True)
        if 'permission' in receipt:
            row=CasoSoporte.objects.get(pk=receipt['permission']['ticket'],solicitante=request.user);s.member(request.user,row.huerto_id,lock=True)
    elif request.path.startswith('/api/soporte/'):
        case=CasoSoporte.objects.get(pk=kwargs['case_id'],solicitante=request.user)
        s.member(request.user,case.huerto_id,lock=True)
    elif 'session_id' in kwargs and not SesionTecnica.objects.filter(pk=kwargs['session_id'],administrador=request.user).exists():raise PermissionDenied

def garden_id(actor):
    s.identity(actor)
    query=Membresia.objects.filter(usuario=actor,activa=True).select_related('huerto')
    row=query.filter(huerto__clave='principal').first() or query.order_by('huerto_id').first()
    if not row:raise GardenUnassigned
    return row.huerto_id

def request_dto(row):return {'id':str(row.pk),'type':row.tipo,'status':row.estado,'at':row.creada_en.isoformat()}
def maintenance_dto(row):return {'id':str(row.pk),'type':row.tipo,'task':row.tipo,'at':row.registrado_en.isoformat(),'actor':str(row.actor_id)}
def validation_dto(row):return {'id':str(row.pk),'type':row.tipo,'version':row.version,'notes':row.notas,'at':row.validada_en.isoformat()}
def scrub(value):
    if isinstance(value,dict):return {k:(None if k in {'token','verificador','password'} else scrub(v)) for k,v in value.items()}
    if isinstance(value,list):return [scrub(v) for v in value]
    return value

def endpoint(methods=('GET',),fields=(),cap=None):
    def wrap(func):
        @wraps(func)
        def view(request,*args,**kwargs):
            if request.method not in methods:return failure(405,'method-not-allowed')
            if not request.user.is_authenticated:return failure(401,'unauthenticated')
            try:
                s.identity(request.user)
                if cap:s.require_cap(request.user,cap)
                if request.method=='GET':return JsonResponse(func(request,{},*args,**kwargs))
                data=body(request,fields)
                if not quota(request):return failure(429,'rate-limited')
                key=uuid.UUID(request.headers.get('Idempotency-Key',''))
                digest=hmac.new(settings.CHILITO_SUPPORT_KEY.encode(),json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
                lock=int.from_bytes(hashlib.sha256(f'{request.user.pk}:{key}'.encode()).digest()[:8],signed=True)
                with transaction.atomic():
                    with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_xact_lock(%s)',[lock])
                    previous=Idempotencia.objects.filter(actor=request.user,clave=key).first()
                    if previous:
                        replay_guard(request,kwargs,previous)
                        if previous.ruta!=request.path or not hmac.compare_digest(previous.huella,digest):raise Conflict
                        return JsonResponse(previous.respuesta)
                    result=func(request,data,*args,**kwargs)
                    Idempotencia.objects.create(actor=request.user,clave=key,ruta=request.path,huella=digest,respuesta=scrub(result))
                return JsonResponse(result)
            except (InputError,ValueError,TypeError,ValidationError,UnicodeError,RecursionError):return failure(400,'invalid-input')
            except RequestDataTooBig:return failure(413,'request-too-large')
            except Conflict:return failure(409,'idempotency-conflict')
            except GardenUnassigned:return failure(403,'garden-unassigned')
            except (PermissionDenied,ObjectDoesNotExist):return failure(403,'access-denied')
            except IntegrityError:return failure(409,'operation-conflict')
            except DatabaseError:return failure(503,'service-unavailable')
        return view
    return wrap

@endpoint()
def garden(request,data):return {'status':'ready','garden':s.garden_projection(request.user,garden_id(request.user))}
@endpoint()
def notices(request,data):
    g=garden_id(request.user);p=bounds(request)
    return {'status':'ready','items':s.notices_projection(request.user,g,offset=(p-1)*25,limit=25),'page':p,'total':Aviso.objects.filter(huerto_id=g).count()}
@endpoint()
def notice(request,data,notice_id):
    for row in s.notices_projection(request.user,garden_id(request.user),notice_id=notice_id):
        if row['id']==notice_id:return {'status':'ready','notice':row}
    raise PermissionDenied
@endpoint(('POST',))
def read_notice(request,data,notice_id):
    # Authorize against the currently presented garden before mutation.
    selected=next((n for n in s.notices_projection(request.user,garden_id(request.user),notice_id=notice_id) if n['id']==notice_id),None)
    if not selected:raise PermissionDenied
    s.mark_notice_read(request.user,notice_id);selected['read']=True
    return {'status':'accepted','id':notice_id,'read':True,'item':selected,'notice':selected}
@endpoint(('GET','POST'),('type',))
def maintenance(request,data):
    g=garden_id(request.user)
    if request.method=='GET':return page(s.maintenance_history(request.user,g),request,maintenance_dto)
    return {'status':'accepted','record':maintenance_dto(s.record_maintenance(request.user,g,text(data,'type',32)))}
@endpoint(('GET','POST'),('type',))
def requests(request,data):
    g=garden_id(request.user)
    if request.method=='GET':return page(s.user_requests(request.user,g),request,request_dto)
    return {'status':'accepted','request':request_dto(s.record_user_request(request.user,g,text(data,'type',32)))}
@endpoint(('GET','POST'),('incident','consent'))
def support(request,data):
    g=garden_id(request.user)
    if request.method=='GET':
        s.member(request.user,g);return page(CasoSoporte.objects.filter(huerto_id=g,solicitante=request.user).select_related('dispositivo').order_by('-creado_en'),request,s._case_dto)
    return s.issue_support(request.user,g,text(data,'incident',32),data.get('consent'))
@endpoint(('POST',))
def revoke(request,data,case_id):return s.revoke_support(request.user,case_id)
@endpoint(cap='ver_flota')
def fleet(request,data):return {'status':'ready',**s.fleet_projection(request.user)}
@endpoint(cap='ver_gobernanza')
def governance(request,data):return {'status':'ready',**s.governance_projection(request.user)}
@endpoint(cap='gestionar_cambios')
def changes(request,data):return {'status':'ready',**s.changes_projection(request.user)}
@endpoint(cap='atender_soporte')
def reports(request,data):return page(CasoSoporte.objects.select_related('dispositivo').order_by('-creado_en'),request,s._case_dto)
@endpoint(('POST',),cap='atender_soporte')
def ask_token(request,data,case_id):return s.request_support_token(request.user,case_id)
@endpoint(('POST',),('token',),cap='atender_soporte')
def open_session(request,data,case_id):
    row=s.open_technical(request.user,case_id,text(data,'token',43))
    return {'status':'accepted','session':{'id':str(row.pk),'ticket':str(row.permiso.caso_id),
      'expiresAt':int(row.permiso.vence_en.timestamp()*1000),'openedAt':row.iniciada_en.isoformat()}}
@endpoint(('POST',),('action',),cap='atender_soporte')
def technical(request,data,session_id):
    result=s.technical_action(request.user,session_id,text(data,'action',32))
    return result if isinstance(result,dict) else {'status':'accepted','request':request_dto(result)}
@endpoint(('POST',))
def close_session(request,data,session_id):
    s.close_technical(request.user,session_id)
    return {'status':'accepted'}
@endpoint(('POST',),('type','version','notes'),cap='gestionar_cambios')
def validate(request,data):
    return {'status':'accepted','validation':validation_dto(s.validate_version(request.user,text(data,'type',32),text(data,'version',64),text(data,'notes',2000,False)))}
@endpoint(('POST',),('validationId',),cap='gestionar_cambios')
def deploy(request,data):
    return {'status':'accepted','request':request_dto(s.request_deployment(request.user,uuid.UUID(text(data,'validationId',36))))}
@endpoint(('POST',),('content',),cap='gestionar_cambios')
def knowledge(request,data):
    row=s.save_knowledge(request.user,text(data,'content',10000))
    return {'status':'accepted','revision':{'id':str(row.pk),'content':row.contenido,'at':row.creada_en.isoformat()}}
@endpoint(('POST',),cap='gestionar_cambios')
def restart(request,data):return {'status':'accepted','request':request_dto(s.request_platform_restart(request.user))}
