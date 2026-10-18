"""Back up the main DB, retain the private archive and restore ONLY into a new isolated DB."""
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.revision_local import ROOT, RESTORE_NAME, VerificationError, run, docker, psql, fingerprint, save_result

def private_directory():
    local=Path(os.environ["LOCALAPPDATA"]).resolve()
    target=(local/"ElChilito"/"backups").resolve()
    if not target.is_relative_to(local) or target.is_relative_to(ROOT.resolve()):
        raise VerificationError("El respaldo debe quedar fuera del proyecto en almacenamiento privado.")
    target.mkdir(parents=True,exist_ok=True)
    sid=run(["powershell.exe","-NoProfile","-Command","[Security.Principal.WindowsIdentity]::GetCurrent().User.Value"])
    run(["icacls.exe",str(target),"/inheritance:r","/grant:r",
         "*"+sid+":(OI)(CI)F","*S-1-5-18:(OI)(CI)F"])
    return target

def main():
    stamp=datetime.now(ZoneInfo("America/Mexico_City")).strftime("%Y%m%d")
    suffix=uuid.uuid4().hex[:8]
    target="el_chilito_restore_"+stamp+"_"+suffix
    if not RESTORE_NAME.fullmatch(target):
        raise VerificationError("Nombre de restauracion invalido.")
    if psql(f"SELECT 1 FROM pg_database WHERE datname='{target}'"):
        raise VerificationError("El destino ya existe; no se reemplaza ni elimina.")
    owner=psql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='el_chilito'")
    if owner!="el_chilito_migrador":
        raise VerificationError("La base origen tiene otro propietario.")
    before=fingerprint("el_chilito","el_chilito_migrador")
    private=private_directory()
    archive=private/("el_chilito_"+stamp+"_"+suffix+".dump")
    if archive.exists():
        raise VerificationError("El archivo de respaldo ya existe; no se reemplaza.")
    container_path="/tmp/chilito_respaldo_"+suffix+".dump"
    try:
        # Static shell text with an internally generated hex filename. No credentials in arguments.
        shell="umask 077; exec pg_dump -w -U el_chilito_migrador -d el_chilito -Fc -f "+container_path
        docker("exec","-T","db","sh","-c",shell)
        docker("cp","db:"+container_path,str(archive))
        if not archive.is_file() or archive.stat().st_size==0:
            raise VerificationError("Respaldo vacio o no disponible.")
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        psql(f"CREATE DATABASE {target} OWNER el_chilito_test_migrador ENCODING 'UTF8'")
        psql(f"REVOKE ALL ON DATABASE {target} FROM PUBLIC; GRANT CONNECT ON DATABASE {target} TO el_chilito_test_app;")
        docker("exec","-T","db","pg_restore","-w","-U","el_chilito_test_migrador","-d",target,
            "--single-transaction","--exit-on-error","--no-owner","--no-privileges",container_path)
        psql("""REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO el_chilito_test_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO el_chilito_test_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO el_chilito_test_app;
ALTER DEFAULT PRIVILEGES FOR ROLE el_chilito_test_migrador IN SCHEMA public
GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO el_chilito_test_app;
ALTER DEFAULT PRIVILEGES FOR ROLE el_chilito_test_migrador IN SCHEMA public
GRANT USAGE,SELECT ON SEQUENCES TO el_chilito_test_app;""",target,"el_chilito_test_migrador")
        restored=fingerprint(target,"el_chilito_test_migrador")
        after=fingerprint("el_chilito","el_chilito_migrador")
        if before!=after:
            raise VerificationError("El origen cambio durante la verificacion; se conserva el respaldo sin declarar equivalencia.")
        if before!=restored:
            raise VerificationError("La restauracion no coincide en filas o estructura.")
        env=os.environ.copy()
        env["ELCHILITO_RESTORE_DB"]=target
        result=subprocess.run([sys.executable,str(ROOT/"backend/tools/verificar_restauracion.py")],
            cwd=ROOT/"backend",env=env,capture_output=True,text=True,timeout=60)
        if result.returncode:
            raise VerificationError("No paso la comprobacion funcional sobre la restauracion.")
        api=json.loads(result.stdout)
        final_restored=fingerprint(target,"el_chilito_test_migrador")
        if final_restored["tables"]!=restored["tables"] or any(final_restored["schema"][key]!=value for key,value in restored["schema"].items() if key!="sequences"):
            raise VerificationError("La comprobacion no revirtio sus filas de prueba.")
        evidence={"backupPath":str(archive),"bytes":archive.stat().st_size,"sha256":digest,
            "sourceDatabase":"el_chilito","restoreDatabase":target,"restoreOwner":"el_chilito_test_migrador",
            "restoredApplicationRole":"el_chilito_test_app","sourceUnchanged":True,
            "tableAndSchemaFingerprintsEqual":True,"tableCount":len(before["tables"]),
            "snapshot":before,"api":api,"globalRolesOrSecretsDumped":False,"sequencesComparedBeforeProbe":True,
            "schemaNormalization":["dropped-column attnums","equivalent varchar-to-text array cast"],
            "existingDatabasesDropped":False,"archiveEncrypted":False}
        save_result("etapa4-respaldo.json",evidence)
        print(json.dumps({"backupPath":str(archive),"bytes":archive.stat().st_size,
            "restoreDatabase":target,"tablesCompared":len(before["tables"]),
            "equivalent":True,"restoredAPIChecks":api["restoredAPIChecks"]}))
    finally:
        # Only the exact temporary archive created by this invocation is removed in the container.
        docker("exec","-T","db","rm","--",container_path)

if __name__=="__main__":
    try:
        main()
    except Exception as error:
        message=str(error) if isinstance(error,VerificationError) else "Fallo la verificacion local de respaldo; no se imprimen datos privados."
        print(message,file=sys.stderr)
        sys.exit(1)
