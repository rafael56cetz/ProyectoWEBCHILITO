"""Recorre por HTTP los tres métodos de segundo factor con el rol de la aplicación, solo en la base temporal.

Todo ocurre en una transacción que se revierte. No imprime códigos ni secretos.
"""
import base64
import os
import re
import struct
import sys
import time
import hashlib
import hmac
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

import destino_temporal  # noqa: E402  aborta si el destino no es la base temporal

destino_temporal.exigir()

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.core.cache import cache
from django.db import connection, transaction
from django.test import Client, override_settings

from cuentas.models import Usuario

P = '/_allauth/browser/v1/'
CLAVE = 'huerto-claro-de-prueba-01'
A = P + 'account/authenticators'
resultados = []


def ok(nombre, condicion, detalle=''):
    resultados.append(bool(condicion))
    print(f"{'ok   ' if condicion else 'FALLO'} {nombre}{'' if condicion else f' -> {detalle}'}")


def post(c, ruta, **datos):
    return c.post(ruta if ruta.startswith('/') else P + ruta, datos, content_type='application/json')


def nuevo():
    return Client(SERVER_NAME='localhost')


def cuenta(email):
    u = Usuario.objects.create(email=email, password=make_password(CLAVE))
    EmailAddress.objects.create(user=u, email=email, verified=True, primary=True)
    return u


def flujos(r):
    return [f['id'] for f in r.json().get('data', {}).get('flows', []) if f.get('is_pending')]


def codigo():
    return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)


def totp(secreto, desfase=0):
    # Cálculo independiente de allauth (RFC 6238) para no probarlo contra sí mismo.
    contador = (int(time.time()) // 30) + desfase
    digest = hmac.new(base64.b32decode(secreto), struct.pack('>Q', contador), hashlib.sha1).digest()
    inicio = digest[-1] & 15
    return f"{(struct.unpack('>I', digest[inicio:inicio + 4])[0] & 0x7fffffff) % 1000000:06d}"


def password(c, email='ana@example.test', clave=CLAVE, limpiar=True):
    # La caché también guarda los TOTP ya usados: no se limpia al probar su repetición.
    if limpiar:
        cache.clear()
    mail.outbox.clear()
    return post(c, 'auth/login', email=email, password=clave)


def por_codigo(email='ana@example.test'):
    c = nuevo()
    assert password(c, email).status_code == 401
    r = post(c, 'auth/code/confirm', code=codigo())
    assert r.status_code == 200, r.status_code
    return c


def recorrer():
    u = cuenta('ana@example.test')

    # Método 1: código por correo
    c = nuevo()
    r = password(c)
    ok('contraseña sola no entra', r.status_code == 401 and flujos(r) == ['login_by_code'], (r.status_code, flujos(r)))
    ok('envía un correo', len(mail.outbox) == 1, len(mail.outbox))
    ok('perfil rechazado sin segundo paso', c.get('/api/cuenta').status_code == 401)
    ok('huerto rechazado sin segundo paso', c.get('/api/huertos/actual').status_code == 401)
    ok('métodos rechazados sin segundo paso', c.get(A).status_code == 401)
    r = post(c, 'auth/code/confirm', code=codigo())
    ok('código correcto entra', r.status_code == 200 and r.json()['meta']['is_authenticated'], r.status_code)
    ok('sesión con marca de inicio', 'chilito_autenticada_en' in c.session)

    usado = codigo()
    c = nuevo()
    password(c)
    otro = codigo()
    r = post(c, 'auth/code/confirm', code=usado if usado != otro else '000000')
    ok('código anterior no sirve', r.status_code == 400, r.status_code)

    c = nuevo()
    password(c)
    bueno = codigo()
    futuro = time.time() + 301
    with patch('allauth.account.internal.flows.code_verification.time.time', return_value=futuro):
        r = post(c, 'auth/code/confirm', code=bueno)
    ok('código vencido a los 301 s', r.status_code in (400, 401, 409) and not r.json().get('meta', {}).get('is_authenticated'), r.status_code)

    c = nuevo()
    password(c)
    bueno = codigo()
    malo = '000000' if bueno != '000000' else '111111'
    for _ in range(3):
        r = post(c, 'auth/code/confirm', code=malo)
    r = post(c, 'auth/code/confirm', code=bueno)
    ok('tres fallos agotan el proceso', r.status_code != 200, r.status_code)
    ok('sigue sin sesión', c.get('/api/cuenta').status_code == 401)
    ok('no existe acceso solo por código', post(nuevo(), 'auth/code/request', email='ana@example.test').status_code == 404)

    # Método 2: TOTP
    c = por_codigo()
    r = c.get(A + '/totp')
    ok('alta de TOTP entrega secreto', r.status_code == 404 and 'secret' in r.json().get('meta', {}), r.status_code)
    secreto = r.json()['meta']['secret']
    ok('URL con emisor', 'issuer=El%20Chilito' in r.json()['meta']['totp_url'])
    r = c.get('/api/cuenta/seguridad/totp-qr')
    ok('QR generado en el servidor', r.status_code == 200 and r.json()['image'].startswith('data:image/svg+xml;base64,'), r.status_code)
    ok('código erróneo no activa', post(c, A + '/totp', code='000000').status_code == 400)
    r = post(c, A + '/totp', code=totp(secreto))
    ok('activar exige confirmar la contraseña', r.status_code == 401 and 'reauthenticate' in str(r.json()), r.status_code)
    ok('confirmación errónea rechazada', post(c, 'auth/reauthenticate', password='clave-equivocada-000').status_code == 400)
    ok('confirmar contraseña', post(c, 'auth/reauthenticate', password=CLAVE).status_code == 200)
    r = post(c, A + '/totp', code=totp(secreto))
    ok('TOTP activado', r.status_code == 200, r.status_code)
    fila = Authenticator.objects.get(user=u, type='totp')
    ok('secreto cifrado en la base', secreto not in str(fila.data), 'en claro')
    recuperacion = Authenticator.objects.get(user=u, type='recovery_codes')
    ok('semilla de recuperación cifrada', 'seed' in recuperacion.data and len(recuperacion.data['seed']) > 80, len(recuperacion.data.get('seed', '')))
    r = c.get(A + '/recovery-codes')
    codigos = r.json()['data'].get('unused_codes', [])
    ok('10 códigos de recuperación', len(codigos) == 10, len(codigos))
    r = c.get(A + '/recovery-codes')
    ok('solo se muestran una vez', not r.json()['data'].get('unused_codes'), r.status_code)
    ok('lista de métodos', {a['type'] for a in c.get(A).json()['data']} == {'totp', 'recovery_codes'})

    c = nuevo()
    r = password(c)
    ok('con TOTP no llega código por correo', r.status_code == 401 and flujos(r) == ['mfa_authenticate'] and not mail.outbox, (flujos(r), len(mail.outbox)))
    ok('sin TOTP no hay acceso', c.get('/api/cuenta').status_code == 401)
    ok('TOTP erróneo rechazado', post(c, 'auth/2fa/authenticate', code='000000').status_code == 400)
    valor = totp(secreto, 1)
    ok('TOTP de otro periodo rechazado', post(c, 'auth/2fa/authenticate', code=valor).status_code == 400)
    valor = totp(secreto)
    r = post(c, 'auth/2fa/authenticate', code=valor)
    ok('TOTP correcto entra', r.status_code == 200, r.status_code)
    d = nuevo()
    password(d, limpiar=False)
    ok('TOTP repetido rechazado', post(d, 'auth/2fa/authenticate', code=valor).status_code == 400)

    # Códigos de recuperación
    r = post(d, 'auth/2fa/authenticate', code=codigos[0])
    ok('código de recuperación entra', r.status_code == 200, r.status_code)
    e = nuevo()
    password(e, limpiar=False)
    ok('código de recuperación repetido rechazado', post(e, 'auth/2fa/authenticate', code=codigos[0]).status_code == 400)

    # Recuperar la contraseña no quita el factor
    cache.clear()
    mail.outbox.clear()
    a = nuevo()
    post(a, 'auth/password/request', email='ana@example.test')
    llave = re.search(r'restablecer\?key=([^\s]+)', mail.outbox[-1].body).group(1)
    post(a, 'auth/password/reset', key=llave, password='huerto-claro-de-prueba-02')
    ok('recuperar contraseña conserva TOTP', Authenticator.objects.filter(user=u, type='totp').exists())
    f = nuevo()
    r = password(f, clave='huerto-claro-de-prueba-02')
    ok('tras recuperar sigue pidiendo factor', flujos(r) == ['mfa_authenticate'], flujos(r))

    # Reautenticación
    r = post(f, 'auth/2fa/authenticate', code=codigos[1])
    registros = f.session.get('account_authentication_methods', [])
    s = f.session
    s['account_authentication_methods'] = [{**x, 'at': x['at'] - 3600} for x in registros]
    s.save()
    r = f.delete(A + '/totp')
    ok('desactivar exige reautenticación', r.status_code == 401 and 'reauthenticate' in str(r.json()), r.status_code)
    r = post(f, 'auth/reauthenticate', password='huerto-claro-de-prueba-02')
    ok('reautenticar con contraseña', r.status_code == 200, r.status_code)
    r = f.delete(A + '/totp')
    ok('TOTP desactivado', r.status_code == 200, r.status_code)
    ok('sin métodos fuertes, sin recuperación', not Authenticator.objects.filter(user=u).exists())
    r = password(nuevo(), clave='huerto-claro-de-prueba-02')
    ok('vuelve el código por correo', flujos(r) == ['login_by_code'], flujos(r))

    # Método 3: WebAuthn, hasta donde llega sin un autenticador físico
    c = por_codigo('segunda@example.test') if cuenta('segunda@example.test') else None
    post(c, 'auth/reauthenticate', password=CLAVE)
    r = c.get(A + '/webauthn')
    pk = r.json().get('data', {}).get('creation_options', {}).get('publicKey', {})
    ok('opciones de registro WebAuthn', r.status_code == 200 and pk.get('rp', {}).get('id') == 'localhost', (r.status_code, pk.get('rp')))
    for malformada in ({'id': 'x'}, {}, {'id': 'x', 'rawId': 'x', 'response': 1}):
        ok('credencial malformada: 400', post(c, A + '/webauthn', name='Llave', credential=malformada).status_code == 400)
    ok('credencial que no es objeto: 400', post(c, A + '/webauthn', name='Llave', credential='x').status_code == 400)


def main():
    with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
        mail.outbox = []
        with transaction.atomic():
            try:
                recorrer()
            finally:
                transaction.set_rollback(True)
    with connection.cursor() as k:
        k.execute('SELECT (SELECT count(*) FROM cuentas_usuario),(SELECT count(*) FROM mfa_authenticator)')
        print('usuarios y autenticadores tras revertir:', k.fetchone())
    print(f'{sum(resultados)} de {len(resultados)} correctas')
    sys.exit(0 if all(resultados) else 1)


if __name__ == '__main__':
    main()
