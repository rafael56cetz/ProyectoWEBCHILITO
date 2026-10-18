"""Exercise real signup/code/session in an isolated browser without public test endpoints."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"))
os.environ["DJANGO_SETTINGS_MODULE"]="config.settings.testing"
os.environ["ELCHILITO_TEST_LOCAL_REGISTRATION"]="1"
os.environ["ELCHILITO_DB_SCOPE"]="test"
os.environ["ELCHILITO_DB_ROLE"]="app"
import django
django.setup()
from tools.revision_local import VerificationError,require_test_database,test_server,save_result
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import connection
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification_by_code import EMAIL_VERIFICATION_CODE_SESSION_KEY
from cuentas.models import ConfirmacionRegistroLocal
from huerto.models import Membresia
from cuentas.registration import configuration_problems

def main():
    require_test_database(connection)
    if configuration_problems():
        raise VerificationError("El perfil aislado de registro no esta disponible.")
    if get_user_model().objects.exists():
        raise VerificationError("La base aislada contiene cuentas; no se modifica.")
    initial_sessions=set(Session.objects.values_list("session_key",flat=True))
    email="signup-"+uuid.uuid4().hex+"@example.invalid"
    environment=os.environ.copy()
    environment["ELCHILITO_UI_URL"]="http://127.0.0.1:8768"
    environment["ELCHILITO_FIXTURE_EMAIL"]=email
    process=None
    result=None
    try:
        cache.clear()
        with test_server():
            process=subprocess.Popen([r"C:\Program Files\nodejs\node.exe",str(ROOT/"backend/tests/ui_local_registration.cjs")],
                env=environment,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,text=True,encoding="utf-8")
            for line in process.stdout:
                item=json.loads(line)
                if item.get("event")=="fixture-code":
                    # Test-only IPC, never an HTTP route. Nothing sensitive is printed or persisted.
                    codes=[]
                    for session in Session.objects.exclude(session_key__in=initial_sessions):
                        state=session.get_decoded().get(EMAIL_VERIFICATION_CODE_SESSION_KEY,{})
                        if state.get("email")==email and state.get("user_id") and isinstance(state.get("code"),str):
                            codes.append(state["code"])
                    if len(codes)!=1:
                        raise VerificationError("No hay un unico proceso de la fixture.")
                    process.stdin.write(json.dumps({"code":codes[0]})+"\n")
                    process.stdin.flush()
                    codes.clear()
                elif item.get("event")=="result":
                    result={key:value for key,value in item.items() if key!="event"}
                else:
                    raise VerificationError("Fallo el recorrido aislado de registro en "+str(item.get("phase","unknown")))
            if process.wait(timeout=15)!=0 or result is None:
                raise VerificationError("No termino el recorrido aislado de registro.")
        user=get_user_model().objects.get(email=email)
        if not EmailAddress.objects.get(user=user,email=email).verified or Membresia.objects.filter(usuario=user).exists():
            raise VerificationError("Verificacion o permisos inesperados en la fixture.")
        confirmation=ConfirmacionRegistroLocal.objects.get(usuario=user)
        if not confirmation.casilla_marcada or not confirmation.documentos_pendientes:
            raise VerificationError("Confirmacion tecnica inesperada.")
        result["technicalConfirmationPendingDocuments"]=True
        result["realSMTPUsed"]=False
        save_result("etapaB-navegador.json",result)
        print(json.dumps(result))
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        get_user_model().objects.filter(email=email).delete()
        Session.objects.exclude(session_key__in=initial_sessions).delete()
        cache.clear()
        connection.close()

if __name__=="__main__":
    try:main()
    except Exception as error:
        print(str(error) if isinstance(error,VerificationError) else "Fallo la comprobacion aislada; datos privados omitidos.",file=sys.stderr)
        sys.exit(1)
