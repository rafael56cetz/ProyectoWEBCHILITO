"""Create new runtime secrets outside Git. Values are never printed."""
import os
import secrets
import subprocess
from pathlib import Path

PRIVATE_DIR = Path(os.environ["LOCALAPPDATA"]) / "ElChilito" / "secrets"

def create_private_secret(filename):
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    path = PRIVATE_DIR / filename
    if path.exists():
        return None
    value = secrets.token_urlsafe(64)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as stream:
        stream.write(value)
    if os.name == "nt":
        sid = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "[Security.Principal.WindowsIdentity]::GetCurrent().User.Value"],
            check=True, capture_output=True, text=True).stdout.strip()
        subprocess.run(["icacls.exe", str(path), "/inheritance:r", "/grant:r",
                        "*" + sid + ":(F)", "*S-1-5-18:(F)"],
                       check=True, capture_output=True)
    return value
