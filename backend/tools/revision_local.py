"""Shared local verification helpers. Output is sanitized; no secret values or HTTP bodies."""
import json
import os
import re
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESTORE_NAME = re.compile(r"el_chilito_restore_[0-9]{8}_[a-f0-9]{8}\Z")

class VerificationError(Exception):
    pass

def run(arguments, *, input=None, timeout=60):
    result = subprocess.run(arguments, input=input, text=True, encoding="utf-8",
        errors="replace", capture_output=True, cwd=ROOT, timeout=timeout)
    if result.returncode:
        raise VerificationError("No se completo una operacion local; se omiten cuerpos y respuestas privadas.")
    return result.stdout.strip()

def docker(*arguments, input=None):
    return run(["docker","compose","-f",str(ROOT/"compose.yaml"),*arguments],input=input)

def psql(query, database="postgres", role="postgres"):
    if database not in {"postgres","el_chilito","el_chilito_test"} and not RESTORE_NAME.fullmatch(database):
        raise VerificationError("Base no autorizada.")
    if role not in {"postgres","el_chilito_migrador","el_chilito_test_migrador"}:
        raise VerificationError("Rol no autorizado.")
    return docker("exec","-T","db","psql","-X","-w","-qAt","-v","ON_ERROR_STOP=1",
        "-U",role,"-d",database,input=query)

def fingerprint(database,role):
    names=json.loads(psql("SELECT coalesce(json_agg(tablename ORDER BY tablename),'[]'::json) FROM pg_tables WHERE schemaname='public'",database,role))
    table_queries=[]
    for name in names:
        if not re.fullmatch("[a-z_][a-z0-9_]*",name):
            raise VerificationError("Nombre de tabla fuera del esquema esperado.")
        table_queries.append(f"""SELECT json_build_object('rows',count(*),'digest',
md5(COALESCE(string_agg(md5(row_to_json(t)::text),'' ORDER BY md5(row_to_json(t)::text)),'')))
FROM public."{name}" t;""")
    queries={
      "columns":"SELECT json_agg(x ORDER BY table_name,ordinal_position) FROM (SELECT table_name,column_name,ordinal_position,data_type,is_nullable,column_default,character_maximum_length,numeric_precision,numeric_scale,datetime_precision,collation_name,identity_generation FROM information_schema.columns WHERE table_schema='public') x",
      "constraints":"SELECT json_agg(x ORDER BY tablename,conname) FROM (SELECT c.conrelid::regclass::text AS tablename,c.conname,pg_get_constraintdef(c.oid) AS definition FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public') x",
      "indexes":"SELECT json_agg(x ORDER BY tablename,indexname) FROM (SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public') x",
      "triggers":"SELECT json_agg(x ORDER BY name) FROM (SELECT tgname AS name,pg_get_triggerdef(oid) AS definition FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN (SELECT oid FROM pg_class WHERE relnamespace='public'::regnamespace)) x",
      "functions":"SELECT json_agg(x ORDER BY name) FROM (SELECT p.proname AS name,pg_get_functiondef(p.oid) AS definition FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prokind='f') x",
      "sequences":"SELECT json_agg(x ORDER BY sequencename) FROM (SELECT sequencename,data_type,start_value,min_value,max_value,increment_by,cycle,cache_size,last_value FROM pg_sequences WHERE schemaname='public') x",
    }
    batch="SET TIME ZONE 'UTC';\n"+"\n".join(table_queries+[query+";" for query in queries.values()])
    raw=psql(batch,database,role)
    values=[]
    decoder=json.JSONDecoder()
    while raw.strip():
        raw=raw.lstrip()
        value,position=decoder.raw_decode(raw)
        values.append(value)
        raw=raw[position:]
    if len(values)!=len(names)+len(queries):
        raise VerificationError("Respuesta de catalogo incompleta.")
    tables=dict(zip(names,values[:len(names)]))
    schema={}
    import hashlib
    for key,value in zip(queries,values[len(names):]):
        if key=="columns":
            # A logical dump compacts attnums of dropped columns; preserve relative order/types.
            for column in value:
                column.pop("ordinal_position")
        if key=="constraints":
            # Exact known equivalent varchar[] -> text[] cast after PostgreSQL reparses a dump.
            original="(ARRAY['informacion'::character varying, 'advertencia'::character varying, 'critico'::character varying])::text[]"
            canonical="ARRAY[('informacion'::character varying)::text, ('advertencia'::character varying)::text, ('critico'::character varying)::text]"
            for constraint in value:
                if constraint["conname"]=="aviso_severidad_valida":
                    constraint["definition"]=constraint["definition"].replace(original,canonical)
        schema[key]=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return {"tables":tables,"schema":schema}

def save_result(filename,result):
    path=ROOT/"revision"/filename
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def require_test_database(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),current_user")
        if cursor.fetchone()!=("el_chilito_test","el_chilito_test_app"):
            raise VerificationError("Se requiere la base aislada de pruebas.")

@contextmanager
def test_server():
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1",8768))
        except OSError:
            raise VerificationError("El puerto temporal de pruebas esta ocupado.") from None
    environment=os.environ.copy()
    environment["DJANGO_SETTINGS_MODULE"]="config.settings.testing"
    environment["ELCHILITO_DB_SCOPE"]="test"
    environment["ELCHILITO_DB_ROLE"]="app"
    process=subprocess.Popen([sys.executable,"manage.py","runserver","127.0.0.1:8768",
        "--noreload","--settings=config.settings.testing"],cwd=ROOT/"backend",env=environment,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        from urllib.request import urlopen
        for _ in range(100):
            if process.poll() is not None:
                raise VerificationError("El servidor aislado no pudo iniciar.")
            try:
                with urlopen("http://127.0.0.1:8768/api/acceso/configuracion",timeout=1) as response:
                    if response.status==200:
                        break
            except OSError:
                time.sleep(.2)
        else:
            raise VerificationError("El servidor aislado no respondio.")
        yield
    finally:
        if process.poll() is None:
            if os.name=="nt":
                subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
            else:
                process.terminate()
        process.wait(timeout=10)
