"""Own isolated PostgreSQL only; never adopts another container/database/volume."""
import os,sys,json,secrets,subprocess,tempfile,time,uuid
from pathlib import Path
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[2]
PYTHON=sys.executable
DB='chilito_integracion_sinteticos';TEST='test_chilito_integracion_sinteticos'
OWNER='chilito_pkg_owner';RUNTIME='chilito_pkg_runtime'

def run(args,**kw):return subprocess.run(args,check=True,capture_output=True,**kw).stdout

def child(script,env,*args):return run([PYTHON,str(ROOT/'backend'/script),*args],cwd=ROOT/'backend',env=env)

def local_connection(name):
    """Resolve the current port of our own container after a restart."""
    label=run(['docker','inspect','--format','{{index .Config.Labels "elchilito.etapa4.synthetic"}}',name]).decode().strip()
    if label!='true':raise RuntimeError('No es el contenedor propio de integración')
    binding=run(['docker','port',name,'5432/tcp']).decode().strip()
    host,separator,port=binding.partition(':')
    if host!='127.0.0.1' or not separator or not port.isascii() or not port.isdecimal() or not 1<=int(port)<=65535:
        raise RuntimeError('Se requiere un único puerto PostgreSQL en loopback')
    for _ in range(30):
        if subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],capture_output=True).returncode==0:
            return {'CHILITO_DB_HOST':host,'CHILITO_DB_PORT':port}
        time.sleep(1)
    raise RuntimeError('PostgreSQL local no listo; se conserva el entorno')

def start(persistent=False):
    name='chilito-etapa4-'+uuid.uuid4().hex[:12]
    work=Path(tempfile.mkdtemp(prefix='chilito_etapa4_'));work.chmod(0o700)
    admin=secrets.token_urlsafe(40);owner=secrets.token_urlsafe(40);runtime=secrets.token_urlsafe(40)
    f=work/'postgres.env';f.write_text('POSTGRES_PASSWORD='+admin+'\n');f.chmod(0o600)
    args=['docker','run','--detach','--name',name,'--label','elchilito.etapa4.synthetic=true','--publish','127.0.0.1::5432','--env-file',str(f)]
    if persistent:args+=['--mount',f'type=volume,source={name}-datos,target=/var/lib/postgresql/data']
    else:args+=['--rm','--tmpfs','/var/lib/postgresql/data:rw']
    args+=['postgres@sha256:b8faeff7712663c2773a190181e1246e37e364b887611c04658c28b44e2408fe']
    run(args)
    try:
        for _ in range(60):
            if subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],capture_output=True).returncode==0:break
            time.sleep(1)
        else:raise RuntimeError('PostgreSQL aislado no listo')
        binding=run(['docker','port',name,'5432/tcp']).decode().strip()
        if not binding.startswith('127.0.0.1:'):raise RuntimeError('Se requiere loopback')
        port=binding.rsplit(':',1)[1]
        with psycopg.connect(host='127.0.0.1',port=port,user='postgres',password=admin,dbname='postgres',autocommit=True) as c:
            for role,password in [(OWNER,owner),(RUNTIME,runtime)]:
                c.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
            for db in [DB,TEST]:c.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(db),sql.Identifier(OWNER)))
            version=c.execute('SELECT version()').fetchone()[0]
        env={**os.environ,'CHILITO_ENV':'testing' if not persistent else 'local','DJANGO_SETTINGS_MODULE':'config.testing' if not persistent else 'config.settings',
             'CHILITO_DB_HOST':'127.0.0.1','CHILITO_DB_PORT':port,'CHILITO_DB_NAME':DB,'CHILITO_DB_USER':OWNER,
             'CHILITO_DB_PASSWORD':owner,'CHILITO_DB_SSLMODE':'disable','CHILITO_DJANGO_KEY':secrets.token_urlsafe(48),
             'CHILITO_SUPPORT_KEY':secrets.token_urlsafe(48),'CHILITO_MAILBOX':str(work/'correo'),
             'CHILITO_ORIGIN':'http://127.0.0.1:8780','CHILITO_SMTP_ENABLED':'0'}
        child('manage.py',env,'migrate','--noinput')
        with psycopg.connect(host='127.0.0.1',port=port,user=OWNER,password=owner,dbname=DB,autocommit=True) as c:
            policy=(ROOT/'sql/privilegios.sql').read_text().replace(':"db_name"',sql.Identifier(DB).as_string(c))
            c.execute(policy,prepare=False)
        env_runtime={**env,'CHILITO_DB_USER':RUNTIME,'CHILITO_DB_PASSWORD':runtime}
        selected={k:v for k,v in env_runtime.items() if k.startswith('CHILITO_') or k=='DJANGO_SETTINGS_MODULE'}
        state=work/'runtime.json';state.write_text(json.dumps(selected));state.chmod(0o600)
        ownerstate=work/'owner.json';ownerstate.write_text(json.dumps({k:v for k,v in env.items() if k.startswith('CHILITO_') or k=='DJANGO_SETTINGS_MODULE'}));ownerstate.chmod(0o600)
        (work/'metadata.json').write_text(json.dumps({'container':name,'volume':name+'-datos' if persistent else None,'version':version,'runtime':str(state),'owner':str(ownerstate)}))
        return name,work,env,env_runtime,version
    except BaseException:
        subprocess.run(['docker','stop',name],capture_output=True)
        raise
