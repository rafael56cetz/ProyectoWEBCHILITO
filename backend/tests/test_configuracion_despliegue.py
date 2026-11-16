"""El perfil de despliegue se niega a arrancar con valores inseguros. Sin base de datos ni red."""
import json
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from django.test import SimpleTestCase

BACKEND = Path(__file__).resolve().parents[1]
LEER = ("import json,config.settings as s;print(json.dumps({'debug':s.DEBUG,'sesion':s.SESSION_COOKIE_SECURE,'csrf':s.CSRF_COOKIE_SECURE,"
        "'redir':s.SECURE_SSL_REDIRECT,'hsts':s.SECURE_HSTS_SECONDS,'origenes':s.CSRF_TRUSTED_ORIGINS,'webauthn':s.MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN,"
        "'samesite':s.SESSION_COOKIE_SAMESITE,'httponly':s.SESSION_COOKIE_HTTPONLY,'inactividad':[s.CHILITO_INACTIVIDAD_USUARIO,s.CHILITO_INACTIVIDAD_ADMIN],'absoluta':s.CHILITO_SESION_ABSOLUTA}))")


def entorno(**cambios):
    valores = {'CHILITO_ENV': 'deployment', 'CHILITO_DJANGO_KEY': 'k' * 50, 'CHILITO_IDEMPOTENCIA_SECRETO': 's' * 40, 'CHILITO_VINCULACION_SECRETO': 'v' * 40, 'CHILITO_MFA_KEY': Fernet.generate_key().decode(),
               'CHILITO_ALLOWED_HOSTS': 'chilito.example.test', 'CHILITO_ORIGIN': 'https://chilito.example.test', 'CHILITO_DB_USER': 'chilito_pkg_runtime',
               'CHILITO_SMTP_ENABLED': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    valores.update(cambios)
    return {k: v for k, v in valores.items() if v is not None}


def cargar(**cambios):
    return subprocess.run([sys.executable, '-c', LEER], cwd=BACKEND, env=entorno(**cambios), capture_output=True, text=True, timeout=30)


class PerfilDeDespliegue(SimpleTestCase):
    def test_configuracion_valida_endurecida(self):
        r = cargar()
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertEqual(json.loads(r.stdout), {'debug': False, 'sesion': True, 'csrf': True, 'redir': True, 'hsts': 31536000, 'origenes': ['https://chilito.example.test'],
                                                'webauthn': False, 'samesite': 'Lax', 'httponly': True, 'inactividad': [1800, 900], 'absoluta': 28800})

    def test_valores_inseguros_detienen_el_arranque(self):
        for nombre, cambios in {'debug': {'CHILITO_DEBUG': '1'}, 'sin hosts': {'CHILITO_ALLOWED_HOSTS': None}, 'comodin': {'CHILITO_ALLOWED_HOSTS': '*'},
                                'origen http': {'CHILITO_ORIGIN': 'http://chilito.example.test'}, 'rol propietario': {'CHILITO_DB_USER': 'chilito_pkg_owner'},
                                'tls debil': {'CHILITO_DB_SSLMODE': 'disable'}, 'clave mfa': {'CHILITO_MFA_KEY': 'no-es-fernet'}, 'sin mfa': {'CHILITO_MFA_KEY': None},
                                'sin smtp': {'CHILITO_SMTP_ENABLED': None}, 'perfil vacio': {'CHILITO_ENV': None}, 'clave corta': {'CHILITO_DJANGO_KEY': 'corta'}}.items():
            with self.subTest(nombre):
                r = cargar(**cambios)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('Improperly', r.stderr + r.stdout + 'Improperly' * (nombre == 'perfil vacio'))
