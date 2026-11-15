"""Frontera JSON del mismo origen. La autorización vive en los servicios de Django ya validados."""
import logging,uuid
from datetime import date
from functools import wraps
from django.core.exceptions import PermissionDenied,ValidationError,ObjectDoesNotExist,RequestDataTooBig
from django.db import IntegrityError,DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from allauth.core import ratelimit
from datos import services as s
from datos import diagnostico,guias,vinculacion
from datos.paginacion import paginar
from allauth.account.authentication import get_authentication_records
from . import services as operacion
from .respuestas import EntradaInvalida as InputError,error as failure,leer_json as body

logger=logging.getLogger(__name__)

def text(data,key,maximum=100,required=True):
    value=data.get(key,'' if not required else None)
    if not isinstance(value,str) or len(value)>maximum:raise InputError
    return value

def identifier(value):
    # Identificador numérico: entero positivo o dígitos ASCII. Nunca booleano, decimal ni notación laxa.
    if type(value) is int and 0<value<10**18:return value
    if isinstance(value,str) and value.isascii() and value.isdecimal() and len(value)<=18 and int(value)>0:return int(value)
    raise InputError

def bounds(request,allowed=('page',)):
    # Lista blanca de parámetros: cualquier otro es entrada no válida.
    if set(request.GET)-set(allowed):raise InputError
    value=request.GET.get('page','1')
    if not value.isascii() or not value.isdecimal() or not 1<=int(value)<=10000:raise InputError
    return int(value)

def page(items,request,mapper=lambda row:row,allowed=('page',)):
    # Solo HTTP: validar `page`. Contar y recortar la consulta es trabajo de datos.paginacion.
    return {'status':'ready',**paginar(items,bounds(request,allowed),mapper)}

def request_dto(row):return {'id':str(row.pk),'type':row.tipo,'status':row.estado,'at':row.creada_en.isoformat()}
def maintenance_dto(row):
    task=getattr(row,'tipo_vigente',row.tipo)
    return {'id':str(row.pk),'type':task,'task':task,'at':row.registrado_en.isoformat(),'actor':str(row.actor_id)}
def admin_maintenance_dto(row):
    return {**maintenance_dto(row),'originalType':row.tipo,'gardenId':row.huerto_id,'garden':row.huerto.nombre,
            'state':'voided' if row.anulado else 'active','revision':row.revision}
def revision_dto(row):return {'number':row.numero,'kind':row.tipo,'correctedType':row.tipo_corregido,'editor':str(row.editor_id),'reason':row.motivo,'at':row.registrada_en.isoformat()}
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
                if not operacion.dentro_de_cuota(request.user,request.path):return failure(429,'rate-limited')
                key=uuid.UUID(request.headers.get('Idempotency-Key',''))
                return JsonResponse(operacion.ejecutar_idempotente(request.user,key,request.path,operacion.huella_de(data),kwargs,
                                                                   lambda:func(request,data,*args,**kwargs)))
            except (InputError,ValueError,TypeError,ValidationError,UnicodeError,RecursionError):return failure(400,'invalid-input')
            except RequestDataTooBig:return failure(413,'request-too-large')
            except operacion.Conflicto:return failure(409,'idempotency-conflict')
            except s.RegistroDesactualizado:return failure(409,'stale-record')
            except s.GardenUnassigned:return failure(403,'garden-unassigned')
            except vinculacion.ReautenticacionRequerida:return failure(403,'reauthentication-required')
            except s.FactorRequerido:return failure(403,'mfa-required')
            except (PermissionDenied,ObjectDoesNotExist):return failure(403,'access-denied')
            except IntegrityError:return failure(409,'operation-conflict')
            except DatabaseError:
                logger.exception('operacion-no-disponible')
                return failure(503,'service-unavailable')
        return view
    return wrap

@endpoint()
def garden(request,data):
    g=s.current_garden(request.user)
    return {'status':'ready','garden':s.garden_projection(request.user,g),'diagnosis':diagnostico.proyeccion(request.user,g)}
@endpoint()
def notices(request,data):
    g=s.current_garden(request.user);p=bounds(request)
    return {'status':'ready','items':s.notices_projection(request.user,g,offset=(p-1)*25,limit=25),'page':p,'total':s.notices_total(request.user,g)}
@endpoint()
def notice(request,data,notice_id):
    for row in s.notices_projection(request.user,s.current_garden(request.user),notice_id=notice_id):
        if row['id']==notice_id:return {'status':'ready','notice':row}
    raise PermissionDenied
@endpoint(('POST',))
def read_notice(request,data,notice_id):
    # Authorize against the currently presented garden before mutation.
    selected=next((n for n in s.notices_projection(request.user,s.current_garden(request.user),notice_id=notice_id) if n['id']==notice_id),None)
    if not selected:raise PermissionDenied
    s.mark_notice_read(request.user,notice_id);selected['read']=True
    return {'status':'accepted','id':notice_id,'read':True,'item':selected,'notice':selected}
@endpoint(('GET','POST'),('type',))
def maintenance(request,data):
    g=s.current_garden(request.user)
    if request.method=='GET':return page(s.maintenance_history(request.user,g),request,maintenance_dto)
    return {'status':'accepted','record':maintenance_dto(s.record_maintenance(request.user,g,text(data,'type',32)))}
@endpoint(('GET','POST'),('type',))
def requests(request,data):
    g=s.current_garden(request.user)
    if request.method=='GET':return page(s.user_requests(request.user,g),request,request_dto)
    return {'status':'accepted','request':request_dto(s.record_user_request(request.user,g,text(data,'type',32)))}
@endpoint(('GET','POST'),('incident','consent'))
def support(request,data):
    g=s.current_garden(request.user)
    if request.method=='GET':
        return page(s.support_reports(request.user,g),request,s.case_dto)
    return s.issue_support(request.user,g,text(data,'incident',32),data.get('consent'))
@endpoint(('POST',))
def revoke(request,data,case_id):return s.revoke_support(request.user,case_id)
@endpoint(cap='ver_flota')
def fleet(request,data):return {'status':'ready',**s.fleet_projection(request.user)}
@endpoint(cap='atender_soporte')
def reports(request,data):return page(s.administrative_reports(request.user),request,s.case_dto)
@endpoint(('POST',),('result','note'),cap='atender_soporte')
def resolve_case(request,data,case_id):
    resolution=s.resolve_case(request.user,case_id,text(data,'result',20),text(data,'note',500,required=False) or '')
    return {'status':'accepted','case':s.case_dto(resolution.caso)}
@endpoint(cap='atender_consultas')
def inquiries(request,data):
    state=request.GET.get('state') or None
    return page(s.admin_inquiries(request.user,state),request,s.inquiry_dto,allowed=('page','state'))
@endpoint(('POST',),('state',),cap='atender_consultas')
def inquiry_state(request,data,inquiry_id):
    return {'status':'accepted','inquiry':s.inquiry_dto(s.update_inquiry(request.user,inquiry_id,text(data,'state',10)))}
# Vinculación de huertos. El servicio decide; aquí solo se lee la petición.
@endpoint(('POST',),('code',))
def bind_garden(request,data):
    return vinculacion.consumir(request.user,text(data,'code',64))
@endpoint(cap='vincular_huertos')
def binding_panel(request,data):
    bounds(request,allowed=())
    return vinculacion.panel(request.user)
@endpoint(('POST',),('garden','email','delivery'),cap='vincular_huertos')
def binding_issue(request,data):
    return vinculacion.emitir(request.user,get_authentication_records(request),identifier(data.get('garden')),text(data,'email',254),text(data,'delivery',12))
@endpoint(('POST',),cap='vincular_huertos')
def binding_revoke(request,data,code_id):
    return vinculacion.revocar(request.user,get_authentication_records(request),code_id)
# Guías de cuidado. El servicio valida y autoriza; aquí solo se lee la petición.
CAMPOS_GUIA=('question','answer','order','sourceName','sourceUrl')
def guide_content(data):
    return {'pregunta':data.get('question'),'respuesta':data.get('answer'),'orden':data.get('order'),
            'fuente_nombre':data.get('sourceName',''),'fuente_url':data.get('sourceUrl','')}
@endpoint()
def care_guides(request,data):
    bounds(request,allowed=())
    return guias.publicadas(request.user)
@endpoint(('GET','POST'),CAMPOS_GUIA,cap='gestionar_guias')
def admin_guides(request,data):
    if request.method=='POST':return guias.crear(request.user,**guide_content(data))
    bounds(request,allowed=())
    return guias.panel(request.user)
@endpoint(('POST',),(*CAMPOS_GUIA,'version'),cap='gestionar_guias')
def admin_guide_edit(request,data,guide_id):
    return guias.editar(request.user,guide_id,data.get('version'),**guide_content(data))
@endpoint(('POST',),('version',),cap='gestionar_guias')
def admin_guide_publish(request,data,guide_id):
    return guias.publicar(request.user,guide_id,data.get('version'))
@endpoint(('POST',),('version',),cap='gestionar_guias')
def admin_guide_withdraw(request,data,guide_id):
    return guias.retirar(request.user,guide_id,data.get('version'))
@endpoint(('POST',),cap='atender_soporte')
def ask_token(request,data,case_id):return s.request_support_token(request.user,case_id)
@endpoint(('POST',),('token',),cap='atender_soporte')
def open_session(request,data,case_id):
    row=s.open_technical(request.user,case_id,text(data,'token',43))
    return {'status':'accepted','session':{'id':str(row.pk),'ticket':str(row.permiso.caso_id),
      'expiresAt':int(row.permiso.vence_en.timestamp()*1000),'openedAt':row.iniciada_en.isoformat()}}
@endpoint(('POST',),('action',),cap='atender_soporte')
def technical(request,data,session_id):
    # El reinicio del dispositivo está fuera de alcance: solo se expone el diagnóstico.
    if text(data,'action',32)!='diagnostic':raise InputError
    return s.technical_action(request.user,session_id,'diagnostic')
@endpoint(('POST',))
def close_session(request,data,session_id):
    s.close_technical(request.user,session_id)
    return {'status':'accepted'}
FILTROS_MANTENIMIENTO={'page','garden','state','task','since','until'}
def maintenance_filters(request):
    if set(request.GET)-FILTROS_MANTENIMIENTO:raise InputError
    get=request.GET.get
    state=get('state')
    if state not in {None,'active','voided'}:raise InputError
    return {'garden_id':identifier(get('garden')) if get('garden') else None,'state':state,'task':get('task') or None,
            'since':date.fromisoformat(get('since')) if get('since') else None,
            'until':date.fromisoformat(get('until')) if get('until') else None}
@endpoint(('GET','POST'),('gardenId','task'),cap='gestionar_mantenimientos')
def admin_maintenance(request,data):
    if request.method=='POST':
        return {'status':'accepted','record':admin_maintenance_dto(s.admin_record_maintenance(request.user,identifier(data.get('gardenId')),text(data,'task',32)))}
    rows=s.admin_maintenance(request.user,**maintenance_filters(request))
    return {**page(rows,request,admin_maintenance_dto,allowed=FILTROS_MANTENIMIENTO),
            'gardens':[{'id':g.pk,'name':g.nombre} for g in s.assigned_gardens(request.user)]}
@endpoint(cap='gestionar_mantenimientos')
def admin_maintenance_detail(request,data,record_id):
    row,revisions=s.maintenance_detail(request.user,record_id)
    return {'status':'ready','record':admin_maintenance_dto(row),'revisions':[revision_dto(item) for item in revisions]}
@endpoint(('POST',),('task','reason','revision'),cap='gestionar_mantenimientos')
def admin_maintenance_correct(request,data,record_id):
    return {'status':'accepted','record':admin_maintenance_dto(s.correct_maintenance(request.user,record_id,text(data,'task',32),text(data,'reason',500),data.get('revision')))}
@endpoint(('POST',),('reason','revision'),cap='gestionar_mantenimientos')
def admin_maintenance_void(request,data,record_id):
    return {'status':'accepted','record':admin_maintenance_dto(s.void_maintenance(request.user,record_id,text(data,'reason',500),data.get('revision')))}

@never_cache
@require_POST
def contact(request):
    """Pública, con CSRF y cuota. El campo trampa, invisible para personas, descarta bots sin avisarles."""
    if not ratelimit.consume(request,action='contacto_producto'):return failure(429,'rate-limited')
    try:
        data=body(request,('name','email','message','website'))
        if not data.get('website'):operacion.enviar_contacto(data)
    except (InputError,ValueError,TypeError,ValidationError,UnicodeError,RecursionError):return failure(400,'invalid-input')
    except RequestDataTooBig:return failure(413,'request-too-large')
    except DatabaseError:
        logger.exception('contacto-no-guardado')
        return failure(503,'service-unavailable')
    return JsonResponse({'status':'accepted'})
