"""Exercise a restored database using its ordinary test application role; fixtures roll back."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.revision_local import RESTORE_NAME, VerificationError
name=os.environ.get("ELCHILITO_RESTORE_DB","")
if not RESTORE_NAME.fullmatch(name):
    raise SystemExit("Base aislada de restauracion requerida.")
os.environ["DJANGO_SETTINGS_MODULE"]="config.settings.restoration"
os.environ["ELCHILITO_DB_SCOPE"]="test"
os.environ["ELCHILITO_DB_ROLE"]="app"
import django
django.setup()
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.db import connection,transaction,ProgrammingError,IntegrityError
from django.test import Client
from django.utils import timezone
from allauth.account.models import EmailAddress
from huerto.models import Huerto,Membresia,Aviso
from huerto.services import assign_membership
from django.contrib.sessions.models import Session
import json
import uuid

def main():
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),current_user")
        if cursor.fetchone()!=(name,"el_chilito_test_app"):
            raise VerificationError("Destino o rol de restauracion inesperado.")
        cursor.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user")
        if any(cursor.fetchone()):
            raise VerificationError("El rol de aplicacion tiene privilegios inesperados.")
    checks=0
    def expect(condition):
        nonlocal checks
        if not condition:
            raise VerificationError("No paso una comprobacion sobre la restauracion.")
        checks+=1
    with transaction.atomic():
        email="restore-"+uuid.uuid4().hex+"@example.invalid"
        password="Frase extensa de restauracion aislada 83!"
        user=get_user_model().objects.create_user(email,password)
        EmailAddress.objects.create(user=user,email=email,primary=True,verified=True)
        garden=Huerto.objects.get(clave="principal")
        client=Client(enforce_csrf_checks=True,HTTP_HOST="127.0.0.1")
        client.get("/api/acceso/configuracion")
        def post(path,data,method="post"):
            return getattr(client,method)(path,data,content_type="application/json",
                HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        expect(client.get("/api/cuenta").status_code==401)
        login=post("/_allauth/browser/v1/auth/login",{"email":email,"password":password})
        expect(login.status_code==200 and login.json()["meta"]["is_authenticated"] is True)
        expect(client.cookies["sessionid"]["httponly"])
        expect(client.get("/api/huertos/actual").status_code==403)
        assign_membership(user,garden)
        body=client.get("/api/huertos/actual").json()
        expect(body["status"]=="waiting" and len(body["plants"])==3)
        expect(all(plant["reading"]["value"] is None for plant in body["plants"]))
        expect(body["temperature"]["value"] is None and body["humidity"]["value"] is None)
        expect(body["tank"]=={"state":"unknown","at":None} and body["updatedAt"] is None)
        notice=Aviso.objects.create(huerto=garden,severidad="informacion",titulo="Comprobacion aislada",
            descripcion="Esta fila existe solamente dentro de una transaccion que se revierte.",creado_en=timezone.now())
        for severity in ["informacion","advertencia","critico"]:
            expect(Aviso.objects.filter(pk=notice.pk).update(severidad=severity)==1)
        for update in [{"severidad":"invalida"},{"resuelto_en":notice.creado_en-timedelta(seconds=1)}]:
            try:
                with transaction.atomic():
                    Aviso.objects.filter(pk=notice.pk).update(**update)
            except IntegrityError:
                checks+=1
            else:
                raise VerificationError("La restauracion no conserva una restriccion.")
        marked=post(f"/api/huertos/actual/avisos/{notice.pk}/lectura",{},method="put")
        expect(marked.status_code==200 and marked.json()["read"] is True)
        expect(client.get(f"/api/huertos/actual/avisos/{notice.pk}").json()["item"]["condition"]=="active")
        try:
            with transaction.atomic(),connection.cursor() as cursor:
                cursor.execute("ALTER TABLE huerto_aviso ADD COLUMN revision_prohibida integer")
        except ProgrammingError:
            checks+=1
        else:
            raise VerificationError("La aplicacion pudo alterar estructura.")
        logout=post("/_allauth/browser/v1/auth/session",{},method="delete")
        expect(logout.status_code==401 and logout.json()["meta"]["is_authenticated"] is False)
        expect(client.get("/api/cuenta").status_code==401)
        transaction.set_rollback(True)
    print(json.dumps({"restoredAPIChecks":checks,"fixturesRolledBack":True,"applicationRole":"el_chilito_test_app"}))

if __name__=="__main__":
    try:
        main()
    except Exception:
        print("Fallo la comprobacion funcional de restauracion; no se imprimen datos privados.",file=sys.stderr)
        sys.exit(1)
