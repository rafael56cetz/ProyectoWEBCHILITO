"""Recorre por HTTP perfil, privacidad, cookies y estadísticas con el rol de la aplicación, solo en la base temporal.

Todo ocurre en una transacción que se revierte. No imprime datos personales.
"""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

import destino_temporal  # noqa: E402  aborta si el destino no es la base temporal

destino_temporal.exigir()

from allauth.account.models import EmailAddress
from django.core.cache import cache
from django.db import connection, transaction
from django.test import Client, override_settings

from cuentas.models import Usuario
from privacidad import services
from datos.models import Auditoria
from privacidad.models import ConteoNavegacion, Decision, Sujeto
from web.models import Idempotencia

resultados = []


def ok(nombre, condicion, detalle=''):
    resultados.append(bool(condicion))
    print(f"{'ok   ' if condicion else 'FALLO'} {nombre}{'' if condicion else f' -> {detalle}'}")


def post(c, ruta, cuerpo=None):
    return c.post(ruta, cuerpo or {}, content_type='application/json',
                  headers={'Idempotency-Key': str(uuid.uuid4())})


def cuenta(email):
    u = Usuario.objects.create(email=email, password='pbkdf2_sha256$1$a$b')
    EmailAddress.objects.create(user=u, email=email, verified=True, primary=True)
    c = Client(SERVER_NAME='localhost')
    c.force_login(u, backend='django.contrib.auth.backends.ModelBackend')
    return u, c


def visitas():
    return sum(ConteoNavegacion.objects.values_list('visitas', flat=True))


def recorrer():
    # Documentos
    v = Client(SERVER_NAME='localhost')
    for tipo in ('privacidad', 'terminos', 'cookies'):
        r = v.get(f'/api/privacidad/documentos/{tipo}')
        ok(f'documento {tipo}', r.status_code == 200 and 'text' in r.json() and r.json().get('registered') is True and r.json().get('draft') is False, r.status_code)
    ok('documento desconocido', v.get('/api/privacidad/documentos/otro').status_code == 404)

    # Banner sin sesión
    r = v.get('/api/privacidad/cookies')
    ok('sin decisión previa', r.json()['decided'] is False and r.json()['statistics'] is False)
    ok('ninguna cookie antes de decidir', not v.cookies, list(v.cookies))
    ok('decisión no booleana', post(v, '/api/privacidad/cookies', {'statistics': 'si'}).status_code == 400)
    ok('campo extra rechazado', post(v, '/api/privacidad/cookies', {'statistics': True, 'x': 1}).status_code == 400)
    ok('sección sin consentimiento no cuenta', post(v, '/api/estadisticas/seccion', {'section': 'inicio'}).json()['counted'] is False)
    ok('sin cookie estadística', services.COOKIE_ESTADISTICA not in v.cookies)

    # Rechazo
    decisiones_previas = Decision.objects.count()
    r = post(v, '/api/privacidad/cookies', {'statistics': False})
    ok('rechazar guarda decisión', r.status_code == 200 and Decision.objects.count() == decisiones_previas + 1, r.status_code)
    cookie = v.cookies[services.COOKIE_PREFERENCIA]
    ok('cookie HttpOnly y Lax', cookie['httponly'] and cookie['samesite'] == 'Lax')
    ok('dura 180 días', cookie['max-age'] == 180 * 24 * 3600, cookie['max-age'])
    ok('rechazo recordado', v.get('/api/privacidad/cookies').json()['decided'] is True)
    ok('rechazo no cuenta', post(v, '/api/estadisticas/seccion', {'section': 'inicio'}).json()['counted'] is False)

    # Aceptación y conteo
    post(v, '/api/privacidad/cookies', {'statistics': True})
    antes = visitas()
    ok('sección válida cuenta', post(v, '/api/estadisticas/seccion', {'section': 'inicio'}).json()['counted'] is True)
    ok('cookie estadística de 30 min', v.cookies[services.COOKIE_ESTADISTICA]['max-age'] == 1800)
    ok('misma sección no se repite', post(v, '/api/estadisticas/seccion', {'section': 'inicio'}).json()['counted'] is False)
    ok('otra sección sí', post(v, '/api/estadisticas/seccion', {'section': 'proyecto'}).json()['counted'] is True)
    ok('totales suben 2', visitas() == antes + 2, visitas() - antes)
    ok('sección fuera de lista', post(v, '/api/estadisticas/seccion', {'section': 'admin'}).status_code == 400)
    ok('sección no textual', post(v, '/api/estadisticas/seccion', {'section': ['inicio']}).status_code == 400)
    falsa = Client(SERVER_NAME='localhost')
    falsa.cookies[services.COOKIE_PREFERENCIA] = str(Sujeto.objects.filter(ambito='navegador').first().pk)
    ok('cookie sin firma ignorada', post(falsa, '/api/estadisticas/seccion', {'section': 'avisos'}).json()['counted'] is False)

    # Revocar
    r = post(v, '/api/privacidad/cookies', {'statistics': False})
    ok('retira la cookie opcional', v.cookies[services.COOKIE_ESTADISTICA]['max-age'] == 0)
    ok('rechazo posterior detiene', post(v, '/api/estadisticas/seccion', {'section': 'soporte'}).json()['counted'] is False)

    # Sin sesión no hay acceso a datos
    ok('perfil exige sesión', post(v, '/api/cuenta/perfil', {'alias': 'x'}).status_code == 401)
    ok('mis datos exige sesión', post(v, '/api/privacidad/mis-datos').status_code == 401)

    # Bienvenida
    u, c = cuenta('titular@example.test')
    otro, d = cuenta('otra@example.test')
    ok('bienvenida pendiente', c.get('/api/cuenta').json()['profile']['welcomePending'] is True)
    ok('saludo de respaldo', c.get('/api/cuenta').json()['profile']['greeting'] == 'Bienvenido')
    ok('«Ahora no» cierra el paso', post(c, '/api/cuenta/bienvenida').status_code == 200)
    ok('bienvenida atendida', c.get('/api/cuenta').json()['profile']['welcomePending'] is False)

    # Rectificación
    # La auditoría guarda qué campo cambió, nunca su valor.
    n = Auditoria.objects.filter(accion='rectificar_perfil').count()
    r = post(c, '/api/cuenta/perfil', {'firstName': ' Ana ', 'alias': 'Chile'})
    ok('rectificar perfil', r.status_code == 200, r.status_code)
    u.refresh_from_db()
    ok('recorta y guarda', (u.first_name, u.alias) == ('Ana', 'Chile'), u.first_name)
    ok('saludo por alias', c.get('/api/cuenta').json()['profile']['greeting'] == 'Chile')
    ok('un registro por campo cambiado', Auditoria.objects.filter(accion='rectificar_perfil').count() == n + 2)
    ok('la auditoría no guarda valores', 'Ana' not in str(list(Auditoria.objects.filter(accion='rectificar_perfil').values_list('detalle', flat=True))))
    n = Auditoria.objects.filter(accion='rectificar_perfil').count()
    post(c, '/api/cuenta/perfil', {'firstName': 'Ana', 'alias': 'Chile'})
    ok('sin cambios no hay registro', Auditoria.objects.filter(accion='rectificar_perfil').count() == n)
    ok('campo no permitido', post(c, '/api/cuenta/perfil', {'is_staff': True}).status_code == 400)
    ok('alias muy largo', post(c, '/api/cuenta/perfil', {'alias': 'x' * 65}).status_code == 400)
    ok('texto con control', post(c, '/api/cuenta/perfil', {'alias': 'a\nb'}).status_code == 400)
    ok('alias de solo espacios queda vacío', post(c, '/api/cuenta/perfil', {'alias': '   '}).status_code == 200)

    # Acceso
    n = Auditoria.objects.filter(accion='consultar_mis_datos').count()
    r = post(c, '/api/privacidad/mis-datos')
    ok('consulta propia', r.json()['data']['email'] == 'titular@example.test', r.status_code)
    ok('deja registro de acceso', Auditoria.objects.filter(accion='consultar_mis_datos').count() == n + 1)
    ok('no guarda datos en idempotencia', 'titular' not in str(list(Idempotencia.objects.filter(actor=u).values_list('respuesta', flat=True))))

    # Oposición con sesión
    post(c, '/api/privacidad/cookies', {'statistics': True})
    n = Decision.objects.count()
    r = post(c, '/api/privacidad/cookies', {'statistics': False})
    ok('oposición registrada', r.status_code == 200 and Decision.objects.count() == n + 1, r.status_code)
    ok('guarda IP recortada y navegador resumido', Decision.objects.filter(usuario=u, acto='cookies').exclude(ip_recortada='').exists())
    sujeto = Sujeto.objects.filter(usuario=u, ambito='navegador').first()
    ok('navegador vinculado a la cuenta', sujeto is not None)
    # Otra cuenta en el mismo navegador pide su propia decisión
    d.cookies[services.COOKIE_PREFERENCIA] = c.cookies[services.COOKIE_PREFERENCIA].value
    ok('otra cuenta no hereda la decisión', d.get('/api/privacidad/cookies').json()['decided'] is False)
    post(d, '/api/privacidad/cookies', {'statistics': True})
    sujeto.refresh_from_db()
    ok('el sujeto no se reasigna', sujeto.usuario_id == u.pk)

    # La autorización de una cuenta no sirve a otra ni a una sesión cerrada
    from django.contrib.auth.models import AnonymousUser
    _, a = cuenta('autoriza@example.test')
    _, b = cuenta('ajena@example.test')
    post(a, '/api/privacidad/cookies', {'statistics': True})
    firmado = a.cookies[services.COOKIE_PREFERENCIA].value
    ok('la propia cuenta sí cuenta', post(a, '/api/estadisticas/seccion', {'section': 'avisos'}).json()['counted'] is True)
    b.cookies[services.COOKIE_PREFERENCIA] = firmado
    ok('otra cuenta no cuenta con decisión ajena', post(b, '/api/estadisticas/seccion', {'section': 'cuenta'}).json()['counted'] is False)
    ajena = Client(SERVER_NAME='localhost')
    ajena.cookies[services.COOKIE_PREFERENCIA] = firmado
    ok('la decisión sobrevive al cierre de sesión', ajena.get('/api/privacidad/cookies').json()['decided'] is True)
    ok('sin sesión cuenta con la decisión del navegador', post(ajena, '/api/estadisticas/seccion', {'section': 'huerto'}).json()['counted'] is True)
    ok('el servicio aplica la misma regla', services.estado_cookies(firmado, AnonymousUser())['decided'] is True)

    # Administración: sin capacidad
    ok('sin capacidad no entra', c.get('/api/admin/guias').status_code == 403)
    ok('sin capacidad no publica', post(c, f'/api/admin/guias/{uuid.uuid4()}/publicar', {'version': 1}).status_code == 403)


def main():
    # Como en los otros flujos: ningún correo sale del proceso, aunque estas rutas no envían.
    with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'), transaction.atomic():
        try:
            cache.clear()
            recorrer()
        finally:
            transaction.set_rollback(True)
    with connection.cursor() as k:
        k.execute('SELECT (SELECT count(*) FROM cuentas_usuario),(SELECT count(*) FROM privacidad_sujeto),(SELECT count(*) FROM conteo_navegacion)')
        print('usuarios, sujetos y conteos tras revertir:', k.fetchone())
    print(f'{sum(resultados)} de {len(resultados)} correctas')
    sys.exit(0 if all(resultados) else 1)


if __name__ == '__main__':
    main()
