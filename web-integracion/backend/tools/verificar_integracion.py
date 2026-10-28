"""Stage 4 synthetic regression/HTTP runner. Never sends SMTP or prints secrets."""
import os,sys,json,subprocess,re,hashlib
from pathlib import Path
from entorno import start,run,child,ROOT
name=None;env={};runtime={}
def redact(text):
    for values in [env,runtime]:
        for k,v in values.items():
            if any(w in k for w in ['PASSWORD','KEY']) and v:text=text.replace(v,'[REDACTED]')
    return re.sub(r"(['\"])[A-Za-z0-9_-]{43,}\1", "'[REDACTED_LONG_VALUE]'", text)
try:
    name,work,env,runtime,version=start()
    print('PostgreSQL aislado iniciado; migraciones aplicadas.',flush=True)
    checks=child('manage.py',env,'check').decode()
    state=child('manage.py',env,'makemigrations','--check','--dry-run').decode()
    completed=subprocess.run([sys.executable,str(ROOT/'backend/manage.py'),'test','datos.tests','tests','--keepdb','--noinput','--verbosity','2'],cwd=ROOT/'backend',env=env,capture_output=True)
    out=(completed.stdout+completed.stderr).decode(errors='replace')
    (ROOT/'evidencias/pruebas-integracion.txt').write_text(redact(out))
    if completed.returncode:raise RuntimeError('Suite Django/HTTP fallida; ver evidencia saneada')
    print('Suite de datos y HTTP aprobada.',flush=True)
    child('tools/seed_runtime.py',env)
    probe=child('tools/probar_runtime.py',runtime).decode()
    print('Operaciones HTTP con runtime limitado aprobadas.',flush=True)
    (ROOT/'evidencias/validacion-integracion.json').write_text(json.dumps({'date':'2026-10-27','status':'passed','version':version,'django_check':checks.strip(),'migrations':state.strip(),'suite':redact(out[-300:]),'runtime':probe.strip(),'smtp_sent':False,'real_databases_used':False,'browser_verified':False},indent=2,ensure_ascii=False)+'\n')
except BaseException as error:
    data={'date':'2026-10-27','status':'not-complete','error_type':type(error).__name__}
    if isinstance(error,subprocess.CalledProcessError):data['diagnostic']=redact((error.stderr or b'').decode(errors='replace')[-10000:])
    (ROOT/'evidencias/validacion-integracion.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print('Validación incompleta; revisar evidencias saneadas. Ningún éxito supuesto.',file=sys.stderr)
    sys.exit(1)
finally:
    if name:subprocess.run(['docker','stop',name],capture_output=True)
