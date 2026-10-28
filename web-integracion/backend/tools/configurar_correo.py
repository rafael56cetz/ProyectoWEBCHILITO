"""Interactive credential entry outside the repository; does not send email."""
import argparse,getpass,json,os,tempfile
from pathlib import Path
from correo_config import ROOT,FIELDS
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--archivo',required=True);p.add_argument('--remitente',required=True)
p.add_argument('--host',default='smtp.gmail.com');p.add_argument('--puerto',type=int,default=587)
p.add_argument('--destinatarios',default='');p.add_argument('--registro-publico',action='store_true')
a=p.parse_args()
destination=Path(a.archivo).expanduser().resolve()
if destination==ROOT or ROOT in destination.parents:raise SystemExit('Usa una ruta externa al proyecto')
if not a.registro_publico and not a.destinatarios:raise SystemExit('Indica destinatarios o registro público autorizado')
if not a.remitente or not a.host or not 1<=a.puerto<=65535:raise SystemExit('Datos de conexión inválidos')
if not os.isatty(0):raise SystemExit('Ejecuta en tu terminal para introducir la contraseña sin mostrarla')
password=getpass.getpass('Contraseña de aplicación SMTP (no se mostrará): ')
if not password:raise SystemExit('No se guardó configuración vacía')
value={'CHILITO_SMTP_ENABLED':'1','CHILITO_SMTP_HOST':a.host,'CHILITO_SMTP_PORT':str(a.puerto),
 'CHILITO_SMTP_USER':a.remitente,'CHILITO_SMTP_PASSWORD':password,
 'CHILITO_SMTP_RECIPIENT_MODE':'any-valid' if a.registro_publico else 'restricted',
 'CHILITO_SMTP_ALLOWED_RECIPIENTS':a.destinatarios,'CHILITO_FROM_EMAIL':'El Chilito <'+a.remitente+'>'}
destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
fd,name=tempfile.mkstemp(prefix='.smtp-',dir=destination.parent)
try:
 os.fchmod(fd,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f);f.flush();os.fsync(f.fileno())
 os.replace(name,destination)
finally:
 if os.path.exists(name):os.unlink(name)
print('Configuración externa guardada con modo 0600. No se envió correo.')
