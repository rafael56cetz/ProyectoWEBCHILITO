"""Owner-only fixture, synthetic verification container only."""
import os,sys,secrets
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.testing')
import django;django.setup()
from django.conf import settings
if settings.DATABASES['default']['NAME']!='chilito_integracion_sinteticos':raise RuntimeError('Solo base sintética')
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from allauth.account.models import EmailAddress
from huerto.models import Huerto,Membresia,Aviso
from datos.models import Dispositivo
from django.utils import timezone
# Login in the runtime probe uses session middleware/force_login only; password not exposed.
u=get_user_model().objects.create_user('runtime-user@example.test',secrets.token_urlsafe(32))
a=get_user_model().objects.create_user('runtime-admin@example.test',secrets.token_urlsafe(32))
for actor in [u,a]:EmailAddress.objects.create(user=actor,email=actor.email,primary=True,verified=True)
a.user_permissions.add(*Permission.objects.filter(content_type__app_label='datos',codename__in=['ver_flota','atender_soporte','ver_gobernanza','gestionar_cambios']))
g=Huerto.objects.create(clave='principal',nombre='Huerto de verificación');Membresia.objects.create(usuario=u,huerto=g)
Dispositivo.objects.create(huerto=g,identificador='runtime-verificacion')
Aviso.objects.create(huerto=g,titulo='Revisión',descripcion='Aviso sintético',recomendacion='',severidad='informacion',creado_en=timezone.now())
print('Fixture sintética preparada por propietario.')
