"""HTTP requests using restricted DB role, including public signup and code verify."""
import os,sys,json,uuid,re,secrets
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.testing')
import django;django.setup()
from django.test import Client
from django.core import mail
from django.contrib.auth import get_user_model
from django.db import connection,DatabaseError
from datos.models import Auditoria
client=Client(enforce_csrf_checks=True,HTTP_HOST='127.0.0.1')
def bootstrap(c):assert c.get('/api/acceso/configuracion').status_code==200
def post(c,path,payload):
 bootstrap(c)
 r=c.post(path,json.dumps(payload),content_type='application/json',HTTP_X_CSRFTOKEN=c.cookies['csrftoken'].value,HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
 assert r.status_code in [200,201,202],(path,r.status_code,r.content)
 return r.json()
with connection.cursor() as c:
 c.execute('SELECT current_user');assert c.fetchone()[0]=='chilito_pkg_runtime'
for email in ['runtime-user@example.test','runtime-admin@example.test']:
 user=get_user_model().objects.get(email=email);client.force_login(user,backend='django.contrib.auth.backends.ModelBackend')
 assert client.get('/api/cuenta').status_code==200
 if 'user' in email:
  assert client.get('/api/huertos/actual').status_code==200
  post(client,'/api/huertos/actual/mantenimiento',{'type':'inspection'})
  post(client,'/api/huertos/actual/solicitudes',{'type':'water'})
  permission=post(client,'/api/soporte',{'incident':'connection','consent':True})['permission']
 else:
  session=post(client,'/api/admin/soporte/'+permission['ticket']+'/abrir',{'token':permission['token']})['session']
  post(client,'/api/admin/sesiones/'+session['id']+'/accion',{'action':'restart-node'})
  post(client,'/api/admin/sesiones/'+session['id']+'/cerrar',{})
bootstrap(client)
r=client.delete('/_allauth/browser/v1/auth/session',data='{}',content_type='application/json',HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value);assert r.status_code in [200,401]
# Registration is exercised with the runtime's INSERT guard (no escalation).
new=Client(enforce_csrf_checks=True,HTTP_HOST='127.0.0.1');bootstrap(new)
pw=secrets.token_urlsafe(24)
r=new.post('/_allauth/browser/v1/auth/signup',json.dumps({'email':'runtime-new@example.test','password':pw,'termsAccepted':True}),content_type='application/json',HTTP_X_CSRFTOKEN=new.cookies['csrftoken'].value)
assert r.status_code==401,(r.status_code,r.content)
code=re.search(r'\b[0-9]{6}\b',mail.outbox[-1].body).group()
r=post(new,'/_allauth/browser/v1/auth/email/verify',{'key':code})
assert new.get('/api/cuenta').status_code==200
with connection.cursor() as c:
 for statement in ['CREATE TABLE forbidden_runtime(id int)','TRUNCATE datos_auditoria','DELETE FROM datos_auditoria','UPDATE huerto_membresia SET activa=false']:
  try:c.execute(statement)
  except DatabaseError:pass
  else:raise AssertionError('Privilegio inesperado')
print('HTTP runtime: cuenta, registro/verificación en memoria, huerto, mantenimiento, solicitud pending, soporte y consola aprobados; DDL/TRUNCATE/auditoría/membresía denegados.')
