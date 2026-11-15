"""Recorre por HTTP los flujos de acceso con el rol de la aplicación, solo en la base temporal.

Todo ocurre en una transacción que se revierte: no deja usuarios ni sesiones.
Requiere el entorno del operador. No imprime códigos, claves ni contraseñas.
"""
import datetime
import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

import destino_temporal  # noqa: E402  aborta si el destino no es la base temporal

destino_temporal.exigir()

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.cache import cache
from django.db import connection, transaction
from django.test import Client, override_settings

from cuentas.models import Usuario
from web import sesion

P = '/_allauth/browser/v1/'
CLAVE, NUEVA = 'huerto-claro-de-prueba-01', 'huerto-claro-de-prueba-02'
resultados = []


def ok(nombre, condicion, detalle=''):
    resultados.append(bool(condicion))
    print(f"{'ok   ' if condicion else 'FALLO'} {nombre}{'' if condicion else f' -> {detalle}'}")


def post(c, ruta, **datos):
    return c.post(ruta if ruta.startswith('/') else P + ruta, datos, content_type='application/json')


def nuevo():
    return Client(SERVER_NAME='localhost')


def registrar(email):
    c = nuevo()
    mail.outbox.clear()
    r = post(c, 'auth/signup', email=email, password=CLAVE, termsAccepted=True, privacyRead=True)
    return c, r


def codigo():
    return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)


def llave():
    return re.search(r'restablecer\?key=([^\s]+)', mail.outbox[-1].body).group(1)


def alterar(c, **marcas):
    s = c.session
    for clave, valor in marcas.items():
        s[clave] = valor
    s.save()


def recorrer():
    # La base puede tener cuentas reales: se mide el cambio, no el total.
    cuentas_previas = Usuario.objects.count()
    # Cuenta nueva
    c, r = registrar('ana@gmail.com')
    forma_normal = (r.status_code, sorted(r.json()))
    ok('registro responde sin error', r.status_code == 401, r.status_code)
    r = post(c, 'auth/email/verify', key=codigo())
    ok('verificar correo inicia sesión', r.status_code == 200, r.status_code)
    s = c.session
    ok('marcas de sesión guardadas', isinstance(s.get(sesion.INICIO), int) and isinstance(s.get(sesion.VISTO), int))
    ok('perfil disponible', c.get('/api/cuenta').status_code == 200)

    # C1: cambio de contraseña con el rol limitado
    r = post(c, 'account/password/change', current_password=CLAVE, new_password=NUEVA)
    ok('cambio de contraseña', r.status_code == 200, r.status_code)
    ok('contraseña guardada', Usuario.objects.get(email='ana@gmail.com').check_password(NUEVA))
    ok('la sesión actual sigue', c.get('/api/cuenta').status_code == 200)
    c.delete(P + 'auth/session')

    # Recuperación
    cache.clear()
    mail.outbox.clear()
    a = nuevo()
    r = post(a, 'auth/password/request', email='ana@gmail.com')
    ok('solicitud de recuperación', r.status_code == 200 and mail.outbox, r.status_code)
    k = llave()
    futuro = datetime.datetime.now() + datetime.timedelta(seconds=601)
    with patch.object(PasswordResetTokenGenerator, '_now', return_value=futuro):
        r = post(a, 'auth/password/reset', key=k, password=CLAVE)
    ok('enlace vencido a los 601 s', r.status_code == 400, r.status_code)
    r = post(a, 'auth/password/reset', key=k, password=CLAVE)
    ok('restablecer no inicia sesión', r.status_code == 401, r.status_code)
    ok('contraseña restablecida', Usuario.objects.get(email='ana@gmail.com').check_password(CLAVE))
    ok('el enlace no se reutiliza', post(a, 'auth/password/reset', key=k, password=NUEVA).status_code == 400)

    # Identidad de Gmail: sin 503, misma forma y sin revelar el correo guardado
    cache.clear()
    v, r = registrar('a.n.a+etiqueta@googlemail.com')
    ok('variante no responde 503', r.status_code != 503, r.status_code)
    ok('variante responde como cuenta nueva', (r.status_code, sorted(r.json())) == forma_normal, r.status_code)
    r = v.get('/api/acceso/verificacion')
    ok('verificación muestra lo escrito', r.json().get('email') == 'a.n.a+etiqueta@googlemail.com', r.status_code)
    ok('no crea cuenta duplicada', Usuario.objects.count() == cuentas_previas + 1, Usuario.objects.count() - cuentas_previas)
    cache.clear()
    mail.outbox.clear()
    v = nuevo()
    post(v, 'auth/login', email='a.na+otra@gmail.com', password=CLAVE)
    r = post(v, 'auth/code/confirm', code=codigo())
    ok('acceso con variante', r.status_code == 200, r.status_code)
    cache.clear()
    mail.outbox.clear()
    post(nuevo(), 'auth/password/request', email='A.N.A@gmail.com')
    ok('recuperación con variante', len(mail.outbox) == 1, len(mail.outbox))
    r = post(nuevo(), 'auth/login', email='a.na@gmail.com', password='clave-equivocada-000')
    ok('contraseña errónea con variante', r.status_code in (400, 401), r.status_code)

    # Los límites no deben distinguir una cuenta existente de una que no existe
    def recuperar(usuario):
        cache.clear()
        return [post(nuevo(), 'auth/password/request', email=f'{usuario}+{n}@gmail.com').status_code for n in 'ab']

    def fallos(usuario):
        cache.clear()
        ultima = None
        for n in range(6):
            r = post(nuevo(), 'auth/login', email=f'{usuario}+{n}@gmail.com', password='clave-equivocada-000')
            ultima = [e.get('code') for e in r.json().get('errors', [])]
        return ultima

    ok('recuperación sin oráculo por variantes', recuperar('ana') == recuperar('nadie.aqui'), (recuperar('ana'), recuperar('nadie.aqui')))
    ok('acceso sin oráculo por variantes', fallos('ana') == fallos('nadie.aqui'), (fallos('ana'), fallos('nadie.aqui')))

    # Sesión
    cache.clear()
    def sesion_activa():
        c = nuevo()
        cache.clear()
        mail.outbox.clear()
        post(c, 'auth/login', email='ana@gmail.com', password=CLAVE)
        ok_login = post(c, 'auth/code/confirm', code=codigo())
        assert ok_login.status_code == 200, ok_login.status_code
        return c, int(c.session[sesion.INICIO])

    c, t = sesion_activa()
    alterar(c, **{sesion.VISTO: t - 120})
    c.get(P + 'auth/session')
    ok('consulta de sesión no renueva', c.session[sesion.VISTO] == t - 120)
    c.get('/api/cuenta', headers={'X-Chilito-Sondeo': '1'})
    ok('sondeo no renueva', c.session[sesion.VISTO] == t - 120)
    c.get('/api/guias')
    ok('actividad real renueva', c.session[sesion.VISTO] >= t)

    alterar(c, **{sesion.VISTO: t - 1801})
    llave_sesion = c.session.session_key
    r = c.get('/api/cuenta')
    ok('30 min sin actividad: 401', r.status_code == 401, r.status_code)
    ok('sesión borrada del servidor', not Session.objects.filter(session_key=llave_sesion).exists())

    c, t = sesion_activa()
    alterar(c, **{sesion.INICIO: t - 28801})
    ok('8 h absolutas: 401', c.get('/api/huertos/actual').status_code == 401)

    c, t = sesion_activa()
    alterar(c, **{sesion.VISTO: t - 901})
    ok('15 min no vencen a un usuario', c.get('/api/cuenta').status_code == 200)

    c, t = sesion_activa()
    alterar(c, **{sesion.VISTO: t - 901})
    with patch('datos.services.is_admin', return_value=True):
        ok('15 min vencen a un administrador', c.get('/api/cuenta').status_code == 401)


def main():
    with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                           ELCHILITO_REGISTRATION_ENABLED=True):
        mail.outbox = []
        with transaction.atomic():
            try:
                recorrer()
            finally:
                transaction.set_rollback(True)
    with connection.cursor() as k:
        k.execute('SELECT count(*) FROM cuentas_usuario')
        print('usuarios tras revertir:', k.fetchone()[0])
    print(f'{sum(resultados)} de {len(resultados)} correctas')
    sys.exit(0 if all(resultados) else 1)


if __name__ == '__main__':
    main()
