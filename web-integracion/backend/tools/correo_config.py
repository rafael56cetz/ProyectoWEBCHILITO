"""Explicit external SMTP configuration; never discovers historical secrets."""
import json,os,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FIELDS={'CHILITO_SMTP_ENABLED','CHILITO_SMTP_HOST','CHILITO_SMTP_PORT','CHILITO_SMTP_USER',
 'CHILITO_SMTP_PASSWORD','CHILITO_SMTP_RECIPIENT_MODE','CHILITO_SMTP_ALLOWED_RECIPIENTS','CHILITO_FROM_EMAIL'}
def load_smtp_file(filename):
    p=Path(filename).expanduser().resolve()
    if p==ROOT or ROOT in p.parents:raise ValueError('El archivo SMTP debe estar fuera del repositorio')
    # Read only an explicitly supplied file owned by this operator, without group/other access.
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
            raise ValueError('El archivo SMTP requiere propietario actual y modo 0600')
        value=json.load(f)
    if not isinstance(value,dict) or set(value)!=FIELDS or any(not isinstance(v,str) for v in value.values()):
        raise ValueError('Configuración SMTP inválida')
    if value['CHILITO_SMTP_ENABLED']!='1' or value['CHILITO_SMTP_RECIPIENT_MODE'] not in {'restricted','any-valid'}:
        raise ValueError('Activación y política SMTP explícitas requeridas')
    return value
