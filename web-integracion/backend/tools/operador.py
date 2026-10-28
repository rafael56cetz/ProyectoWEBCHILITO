"""Trusted operator only; no new account, never assigns privileges via browser."""
import os,sys,json,argparse
from pathlib import Path
from entorno import local_connection
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('email');p.add_argument('--huerto',action='store_true');p.add_argument('--capacidades',nargs='*',default=[]);a=p.parse_args()
allowed={'ver_flota','atender_soporte','ver_gobernanza','gestionar_cambios'}
if set(a.capacidades)-allowed:raise SystemExit('Capacidad no admitida')
meta=json.loads((ROOT/'evidencias/entorno-local.json').read_text());os.environ.update({**json.loads(Path(meta['owner']).read_text()),**local_connection(meta['container'])})
sys.path.insert(0,str(ROOT/'backend'));import django;django.setup()
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import transaction
from huerto.models import Huerto,Membresia
from datos.models import Dispositivo
with transaction.atomic():
 user=get_user_model().objects.get(email__iexact=a.email)
 if a.huerto:
  garden,_=Huerto.objects.get_or_create(clave='principal',defaults={'nombre':'Mi huerto'})
  Membresia.objects.get_or_create(usuario=user,huerto=garden)
  Dispositivo.objects.get_or_create(huerto=garden,defaults={'identificador':'chilito-principal'})
 if a.capacidades:user.user_permissions.add(*Permission.objects.filter(content_type__app_label='datos',codename__in=a.capacidades))
print('Asignación de operador completada sobre cuenta existente; no se creó ni verificó una cuenta.')
