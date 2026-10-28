"""Own local synthetic application. External secrets; retained own Docker volume."""
import os,sys,json,subprocess,signal
from pathlib import Path
from entorno import start,ROOT,child,local_connection
from correo_config import load_smtp_file
state=ROOT/'evidencias/entorno-local.json'
def serve(env,metadata):
    smtp_file=os.environ.get("CHILITO_SMTP_CONFIG")
    if smtp_file:
        env.update(load_smtp_file(smtp_file))
    process=subprocess.Popen([sys.executable,str(ROOT/'backend/manage.py'),'runserver','127.0.0.1:8780','--noreload'],env=env)
    metadata['server_pid']=process.pid
    state.write_text(json.dumps(metadata,indent=2)+'\n')
    return process.wait()

command=sys.argv[1] if len(sys.argv)>1 else 'start'
if command=='start':
    if state.exists():
        meta=json.loads(state.read_text())
        label=subprocess.run(['docker','inspect','--format','{{index .Config.Labels "elchilito.etapa4.synthetic"}}',meta['container']],capture_output=True,text=True)
        if label.returncode==0 and label.stdout.strip()=='true':
            subprocess.run(['docker','start',meta['container']],check=True,capture_output=True)
            env={**os.environ,**json.loads(Path(meta['runtime']).read_text()),**local_connection(meta['container'])}
            print('Aplicación local: http://127.0.0.1:8780/index.html',flush=True)
            raise SystemExit(serve(env,meta))
        raise SystemExit('El entorno registrado no está disponible. Conservar datos; revisar antes de crear otro.')
    name,work,env,runtime,version=start(persistent=True)
    metadata=json.loads((work/'metadata.json').read_text());metadata['date']='2026-10-27'
    state.write_text(json.dumps(metadata,indent=2)+'\n')
    print('Aplicación local: http://127.0.0.1:8780/index.html',flush=True)
    print('Correo de pruebas externo: '+runtime['CHILITO_MAILBOX'],flush=True)
    print('No hay cuentas ni huertos creados automáticamente. Registro público disponible; operador asigna después recursos/capacidades.',flush=True)
    raise SystemExit(serve(runtime,metadata))
elif command=='stop':
    meta=json.loads(state.read_text())
    label=subprocess.run(['docker','inspect','--format','{{index .Config.Labels "elchilito.etapa4.synthetic"}}',meta['container']],capture_output=True,text=True,check=True)
    if label.stdout.strip()!='true':raise SystemExit('No es el contenedor propio de integración')
    pid=meta.get('server_pid')
    if isinstance(pid,int):
        cmd=Path(f'/proc/{pid}/cmdline')
        if cmd.exists() and str(ROOT/'backend/manage.py').encode() in cmd.read_bytes().split(b'\x00'):
            os.kill(pid,signal.SIGTERM)
    subprocess.run(['docker','stop',meta['container']],check=True,capture_output=True)
    print('Aplicación y PostgreSQL locales detenidos; volumen conservado.')
else:raise SystemExit('Uso: local.py start|stop')
