"""Check persistence across actual PostgreSQL and Django restarts; fixtures only in test DB."""
import json
import os
import sys
import subprocess
import time
import uuid
from pathlib import Path
from urllib.request import Request,build_opener,HTTPCookieProcessor,urlopen
from urllib.error import HTTPError
from http.cookiejar import CookieJar
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.revision_local import ROOT,VerificationError,run,docker,psql,fingerprint,save_result,require_test_database,test_server

def restart_canonical_server():
    with urlopen("http://127.0.0.1:8766/index.html",timeout=5) as response:
        if response.read()!=(ROOT/"dist/index.html").read_bytes():
            raise VerificationError("La carpeta servida no coincide; no se reinicia.")
    # Inspect all target processes before stopping exactly the matching Django listener and launcher.
    script=r"""
$ErrorActionPreference='Stop'
$chilitoListeners=@(Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction Stop)
if($chilitoListeners.Count -ne 1 -or $chilitoListeners[0].LocalAddress -ne '127.0.0.1') { throw 'Servidor inesperado.' }
$chilitoProcess=Get-CimInstance Win32_Process -Filter ('ProcessId='+$chilitoListeners[0].OwningProcess)
$chilitoPython=Join-Path $env:LOCALAPPDATA 'ElChilito\venvs\backend\Scripts\python.exe'
$chilitoPattern='manage\.py"?.*runserver\s+127\.0\.0\.1:8766\s+--noreload'
$chilitoExecutables=@($chilitoPython,'C:\Python313\python.exe')
$chilitoCommandPrefix='"'+$chilitoPython+'"'
if($chilitoProcess.ExecutablePath -notin $chilitoExecutables -or -not $chilitoProcess.CommandLine.StartsWith($chilitoCommandPrefix) -or $chilitoProcess.CommandLine -notmatch $chilitoPattern) { throw 'Proceso inesperado.' }
$chilitoParent=Get-CimInstance Win32_Process -Filter ('ProcessId='+$chilitoProcess.ParentProcessId)
$chilitoStopParent=$chilitoParent -and $chilitoParent.ExecutablePath -in $chilitoExecutables -and $chilitoParent.CommandLine.StartsWith($chilitoCommandPrefix) -and $chilitoParent.CommandLine -match $chilitoPattern
Stop-Process -Id $chilitoProcess.ProcessId
if($chilitoStopParent) { Stop-Process -Id $chilitoParent.ProcessId -ErrorAction SilentlyContinue }
$env:ELCHILITO_DB_SCOPE='local'
$env:ELCHILITO_DB_ROLE='app'
$env:DJANGO_SETTINGS_MODULE='config.settings.local'
$chilitoRoot='C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web'
Start-Process -FilePath $chilitoPython -ArgumentList @('manage.py','runserver','127.0.0.1:8766','--noreload') -WorkingDirectory (Join-Path $chilitoRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $chilitoRoot 'revision\django-local.log') -RedirectStandardError (Join-Path $chilitoRoot 'revision\django-local-error.log') | Out-Null
"""
    launched=subprocess.run(["powershell.exe","-NoProfile","-Command",script],timeout=20,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL)
    if launched.returncode:
        raise VerificationError("No se pudo reiniciar el proceso Django verificado.")
    for _ in range(75):
        try:
            with urlopen("http://127.0.0.1:8766/api/acceso/configuracion",timeout=1) as response:
                if response.status==200:
                    return
        except OSError:
            time.sleep(.2)
    raise VerificationError("Django no respondio despues del reinicio.")

def main():
    os.environ["DJANGO_SETTINGS_MODULE"]="config.settings.testing"
    os.environ["ELCHILITO_DB_SCOPE"]="test"
    os.environ["ELCHILITO_DB_ROLE"]="app"
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.contrib.sessions.models import Session
    from django.db import connection
    from django.core.cache import cache
    from django.utils import timezone
    from allauth.account.models import EmailAddress
    from huerto.models import Huerto,Zona,Membresia,Aviso,AvisoLeido
    require_test_database(connection)
    if any(model.objects.exists() for model in [get_user_model(),Huerto,Membresia,Aviso,AvisoLeido]):
        raise VerificationError("La base aislada no esta vacia; no se modifica.")
    before=fingerprint("el_chilito","el_chilito_migrador")
    original_sessions=set(Session.objects.values_list("session_key",flat=True))
    cache_key="stage4-restart-"+uuid.uuid4().hex
    user=garden=notice=None
    jar=CookieJar()
    client=build_opener(HTTPCookieProcessor(jar))
    def call(path,method="GET",body=None):
        headers={"Accept":"application/json"}
        if method!="GET":
            headers["Content-Type"]="application/json"
            headers["X-CSRFToken"]=next(cookie.value for cookie in jar if cookie.name=="csrftoken")
        request=Request("http://127.0.0.1:8768"+path,
            data=json.dumps(body).encode() if body is not None else None,method=method,headers=headers)
        try:
            response=client.open(request,timeout=10)
        except HTTPError as error:
            response=error
        with response:
            return response.status,json.loads(response.read())
    checks=0
    def expect(condition):
        nonlocal checks
        if not condition: raise VerificationError("No paso una comprobacion de persistencia.")
        checks+=1
    try:
        password="Frase exclusiva para persistencia aislada 73!"
        user=get_user_model().objects.create_user("restart-"+uuid.uuid4().hex+"@example.invalid",password)
        EmailAddress.objects.create(user=user,email=user.email,verified=True,primary=True)
        garden=Huerto.objects.create(clave="principal",nombre="Persistencia aislada")
        for number in (1,2,3):
            Zona.objects.create(huerto=garden,numero=number,nombre="Planta "+str(number))
        Membresia.objects.create(usuario=user,huerto=garden)
        notice=Aviso.objects.create(huerto=garden,severidad="informacion",titulo="Persistencia aislada",
            descripcion="Solo para verificar reinicio; se retira al terminar.",creado_en=timezone.now())
        cache.set(cache_key,"retained",timeout=600)
        with test_server():
            expect(call("/api/acceso/configuracion")[0]==200)
            status,body=call("/_allauth/browser/v1/auth/login","POST",{"email":user.email,"password":password})
            expect(status==200 and body["meta"]["is_authenticated"] is True)
            cookie=next(cookie for cookie in jar if cookie.name=="sessionid")
            expect(cookie.has_nonstandard_attr("HttpOnly"))
            status,receipt=call(f"/api/huertos/actual/avisos/{notice.pk}/lectura","PUT",{})
            expect(status==200 and receipt["read"] is True)
            expected_profile=call("/api/cuenta")[1]
            expected_garden=call("/api/huertos/actual")[1]
            expected_notice=call(f"/api/huertos/actual/avisos/{notice.pk}")[1]
        connection.close()
        docker("restart","-t","10","db")
        for _ in range(90):
            state=docker("ps","--format","json","db")
            entries=json.loads(state) if state.startswith("[") else [json.loads(line) for line in state.splitlines()]
            if entries and entries[0].get("Health")=="healthy":
                break
            time.sleep(.3)
        else:
            raise VerificationError("PostgreSQL no termino de reiniciar.")
        restart_canonical_server()
        with test_server():
            expect(call("/_allauth/browser/v1/auth/session")[1]["meta"]["is_authenticated"] is True)
            expect(call("/api/cuenta")[1]==expected_profile)
            expect(call("/api/huertos/actual")[1]==expected_garden)
            expect(call(f"/api/huertos/actual/avisos/{notice.pk}")[1]==expected_notice)
            expect(call(f"/api/huertos/actual/avisos/{notice.pk}/lectura","PUT",{})[1]["readAt"]==receipt["readAt"])
            expect(call("/api/huertos/actual")[1]["tank"]=={"state":"unknown","at":None})
            expect(cache.get(cache_key)=="retained")
            expect(AvisoLeido.objects.filter(aviso=notice,usuario=user).count()==1)
            status,body=call("/_allauth/browser/v1/auth/session","DELETE")
            expect(status==401 and body["meta"]["is_authenticated"] is False)
            expect(call("/api/cuenta")[0]==401)
        after=fingerprint("el_chilito","el_chilito_migrador")
        expect(before==after)
        result={"checks":checks,"failed":0,"postgresRestarted":True,"canonicalDjangoRestarted":True,
            "isolatedDjangoRestarted":True,"mainDatabaseUnchanged":True,"sessionSurvived":True,
            "readReceiptSurvived":True,"rateCacheSurvived":True,"fixturesOnlyIn":"el_chilito_test"}
        save_result("etapa4-reinicio.json",result)
        print(json.dumps(result))
    finally:
        connection.close()
        if notice:
            AvisoLeido.objects.filter(aviso=notice).delete()
            Aviso.objects.filter(pk=notice.pk).delete()
        if garden:
            Membresia.objects.filter(huerto=garden).delete()
            Zona.objects.filter(huerto=garden).delete()
            Huerto.objects.filter(pk=garden.pk).delete()
        if user:
            user.delete()
        Session.objects.exclude(session_key__in=original_sessions).delete()
        cache.delete(cache_key)
        connection.close()

if __name__=="__main__":
    try: main()
    except Exception as error:
        print(str(error) if isinstance(error,VerificationError) else "Fallo la verificacion de reinicio; se omiten datos privados.",file=sys.stderr)
        sys.exit(1)
