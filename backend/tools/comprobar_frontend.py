"""Reproducible UI checks: only the isolated DB, with fixture cleanup and no real mail."""
import os
import argparse
import subprocess
import socket
import sys
import time
from pathlib import Path
from urllib.request import urlopen

parser=argparse.ArgumentParser()
parser.add_argument("--etapa",type=int,choices=[2,3],default=2)
parser.add_argument("--contrasenas",action="store_true",help="Check Stage A password guidance with isolated fixtures")
parser.add_argument("--responsive",action="store_true",help="Audit phone, tablet and landscape layouts")
parser.add_argument("--vinculacion",action="store_true",help="Check empty garden and visual-only device linking")
args=parser.parse_args()
if args.vinculacion and args.etapa!=3:
    parser.error("--vinculacion requires --etapa 3")
if args.responsive and args.etapa!=3:
    parser.error("--responsive requires --etapa 3")
stage=args.etapa
if args.contrasenas and stage!=2:
    parser.error("--contrasenas uses the access fixture only")
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"))
os.environ["DJANGO_SETTINGS_MODULE"]="config.settings.testing"
os.environ["ELCHILITO_DB_SCOPE"]="test"
os.environ["ELCHILITO_DB_ROLE"]="app"
import django
django.setup()
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import connection
from allauth.account.models import EmailAddress
from django.utils import timezone
from datetime import timedelta
from huerto.models import Huerto,Zona,Membresia,Aviso,AvisoLeido
from huerto.services import mark_notice_read

with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(),current_user")
    if cursor.fetchone()!=("el_chilito_test","el_chilito_test_app"):
        raise SystemExit("Se requiere la base aislada con rol de aplicacion.")
email="stage2-browser@example.invalid"
if get_user_model().objects.filter(email=email).exists():
    raise SystemExit("Ya existe la cuenta de fixture; no se modifico.")
initial_sessions=set(Session.objects.values_list("session_key",flat=True))
with socket.socket() as probe:
    try:
        probe.bind(("127.0.0.1",8768))
    except OSError:
        raise SystemExit("El puerto temporal de pruebas esta ocupado; no se detuvo ningun proceso.")
user=None
unassigned_user=None
process=None
fixture_gardens=[]
fixture_notices=[]
try:
    # A fixture in the isolated DB is not an account provisioned in the main application.
    user=get_user_model().objects.create_user(email,"Frase exclusiva para prueba de navegador aislada 37!")
    EmailAddress.objects.create(user=user,email=email,verified=True,primary=True)
    if args.vinculacion:
        if get_user_model().objects.filter(email="unassigned-browser@example.invalid").exists():
            raise RuntimeError("Ya existe la cuenta de revision sin membresia; no se modifica.")
        unassigned_user=get_user_model().objects.create_user("unassigned-browser@example.invalid","Frase exclusiva para prueba de navegador aislada 37!")
        EmailAddress.objects.create(user=unassigned_user,email=unassigned_user.email,verified=True,primary=True)
    if stage==3:
        if Huerto.objects.filter(clave__in=["principal","stage3-ajeno"]).exists():
            raise RuntimeError("Ya existe un huerto de prueba; no se modifico.")
        garden=Huerto.objects.create(clave="principal",nombre="Huerto aislado de comprobacion")
        fixture_gardens.append(garden)
        zones=[Zona.objects.create(huerto=garden,numero=number,nombre="Planta "+str(number)+" "+("nombrelargo"*6)) for number in [1,2,3]]
        Membresia.objects.create(usuario=user,huerto=garden)
        other=Huerto.objects.create(clave="stage3-ajeno",nombre="Huerto privado ajeno")
        fixture_gardens.append(other)
        active=Aviso.objects.create(huerto=garden,zona=zones[0],severidad="advertencia",
            titulo="Aviso "+("contenidolargo"*9),descripcion='Texto <img src=x onerror="window.injection=true"> registrado solo para pruebas.',
            recomendacion="Revisar la informacion registrada.",creado_en=timezone.now()-timedelta(hours=2))
        fixture_notices.append(active)
        resolved=Aviso.objects.create(huerto=garden,severidad="informacion",titulo="Aviso resuelto aislado",
            descripcion="Contenido de prueba aislada.",recomendacion="",creado_en=timezone.now()-timedelta(hours=1),
            resuelto_en=timezone.now()-timedelta(minutes=10))
        fixture_notices.append(resolved)
        foreign=Aviso.objects.create(huerto=other,severidad="critico",titulo="Contenido ajeno",
            descripcion="Solo en otro huerto aislado.",creado_en=timezone.now())
        fixture_notices.append(foreign)
        from concurrent.futures import ThreadPoolExecutor
        def concurrent_read():
            from django.db import close_old_connections
            close_old_connections()
            try:
                current_user=get_user_model().objects.get(pk=user.pk)
                return mark_notice_read(current_user,active.pk)
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(concurrent_read) for _ in range(2)]
            results=[future.result(timeout=15) for future in futures]
        assert all(result["status"]=="accepted" for result in results)
        assert results[0]["readAt"]==results[1]["readAt"]
        assert AvisoLeido.objects.filter(aviso=active,usuario=user).count()==1
        print('{"concurrentReadChecks":3,"failed":0}',flush=True)
        AvisoLeido.objects.filter(aviso=active,usuario=user).delete()
    cache.clear()
    process=subprocess.Popen([sys.executable,"manage.py","runserver","127.0.0.1:8768","--noreload",
        "--settings=config.settings.testing"],cwd=ROOT/"backend",stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError("El servidor aislado no pudo arrancar.")
        try:
            with urlopen("http://127.0.0.1:8768/api/acceso/configuracion",timeout=1) as response:
                if response.status==200:
                    break
        except OSError:
            time.sleep(.2)
    else:
        raise RuntimeError("El servidor aislado no respondio.")
    env=os.environ.copy()
    env["ELCHILITO_UI_URL"]="http://127.0.0.1:8768"
    if args.contrasenas or args.responsive:
        from allauth.account import app_settings
        from allauth.account.utils import user_pk_to_url_str
        env["ELCHILITO_TEST_RESET_KEY"] = f"{user_pk_to_url_str(user)}-{app_settings.PASSWORD_RESET_TOKEN_GENERATOR().make_token(user)}"
    if stage==3:
        env["ELCHILITO_TEST_NOTICE"]=str(active.pk)
        env["ELCHILITO_TEST_FOREIGN_NOTICE"]=str(foreign.pk)
    if args.vinculacion:
        domain_models=[Huerto,Zona,Membresia,Aviso,AvisoLeido]
        domain_before=[list(model.objects.order_by("pk").values()) for model in domain_models]
    result=subprocess.run([r"C:\Program Files\nodejs\node.exe",str(ROOT/("backend/tests/ui_garden_link.cjs" if args.vinculacion else "backend/tests/ui_responsive.cjs" if args.responsive else "backend/tests/ui_password_help.cjs" if args.contrasenas else "backend/tests/ui_stage3.cjs" if stage==3 else "backend/tests/ui_stage2.cjs"))],env=env,cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
    if args.vinculacion:
        if domain_before != [list(model.objects.order_by('pk').values()) for model in domain_models]:
            raise RuntimeError('La revision visual modifico el dominio de huertos.')
        print('{"gardenDomainUnchanged":true,"linkingServiceCalled":false}',flush=True)
finally:
    if process:
        if os.name == "nt" and process.poll() is None:
            subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],
                           check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        elif process.poll() is None:
            process.terminate()
        process.wait(timeout=10)
    if fixture_notices:
        AvisoLeido.objects.filter(aviso__in=fixture_notices).delete()
        Aviso.objects.filter(pk__in=[notice.pk for notice in fixture_notices]).delete()
    if fixture_gardens:
        Membresia.objects.filter(usuario=user,huerto__in=fixture_gardens).delete()
        Zona.objects.filter(huerto__in=fixture_gardens).delete()
        Huerto.objects.filter(pk__in=[garden.pk for garden in fixture_gardens]).delete()
    if unassigned_user:
        unassigned_user.delete()
    if user:
        user.delete()
    Session.objects.exclude(session_key__in=initial_sessions).delete()
    cache.clear()
    connection.close()
