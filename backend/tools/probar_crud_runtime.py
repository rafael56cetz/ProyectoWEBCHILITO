"""Prueba con los privilegios reales lo que el rol de la aplicación no puede preparar.

Solo actúa sobre una base test_. `preparar` corre como propietario: aplica privilegios y
crea datos de prueba. `probar` corre como chilito_pkg_runtime, en transacción revertida.
"""
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.db import Error, connection, transaction
from django.test import Client

from cuentas.models import Usuario
from datos import services as s
from datos.models import (AsignacionMantenimiento, Auditoria, Dispositivo, Mantenimiento)
from huerto.models import Huerto, Membresia
from web import sesion

BASE = connection.settings_dict['NAME']
if not BASE.startswith('test_'):
    sys.exit('Esta herramienta solo actúa sobre una base test_')
CORREOS = {n: f'{n}@example.test' for n in ('autor', 'editor', 'ajeno', 'soporte', 'sinfactor', 'vinculo')}
resultados = []


def privilegios():
    """Aplica sql/privilegios.sql a la base test_ (como propietario). Lo usan `preparar` y `flujos`."""
    politica = Path(settings.PROJECT_ROOT, 'sql', 'privilegios.sql').read_text().replace(':"db_name"', f'"{BASE}"')
    with connection.cursor() as k:
        k.execute(politica)
    print('privilegios aplicados a la base temporal')


def preparar():
    privilegios()
    with transaction.atomic():
        u = {}
        for nombre, email in CORREOS.items():
            u[nombre] = Usuario.objects.create(email=email, password='pbkdf2_sha256$1$a$b')
            EmailAddress.objects.create(user=u[nombre], email=email, verified=True, primary=True)
        huerto = Huerto.objects.create(clave='principal', nombre='Prueba')
        otro = Huerto.objects.create(clave='otro', nombre='Ajeno')
        Dispositivo.objects.create(huerto=huerto, identificador='prueba-1')
        libre = Huerto.objects.create(clave='libre', nombre='Sin vincular')
        Dispositivo.objects.create(huerto=libre, identificador='prueba-libre')
        Membresia.objects.create(usuario=u['autor'], huerto=huerto)
        capacidad = lambda codigo: Permission.objects.get(content_type__app_label='datos', codename=codigo)
        u['editor'].user_permissions.add(capacidad('gestionar_mantenimientos'), capacidad('atender_consultas'), capacidad('vincular_huertos'), capacidad('gestionar_guias'))
        u['ajeno'].user_permissions.add(capacidad('gestionar_mantenimientos'))
        u['soporte'].user_permissions.add(capacidad('atender_soporte'))
        u['sinfactor'].user_permissions.add(capacidad('gestionar_mantenimientos'))
        AsignacionMantenimiento.objects.create(usuario=u['sinfactor'], huerto=huerto)
        for nombre in ('editor', 'ajeno', 'soporte'):
            Authenticator.objects.create(user=u[nombre], type='totp', data={})
        AsignacionMantenimiento.objects.create(usuario=u['editor'], huerto=huerto)
        AsignacionMantenimiento.objects.create(usuario=u['ajeno'], huerto=otro)
    print('privilegios y datos de prueba listos')


def ok(nombre, condicion, detalle=''):
    resultados.append(bool(condicion))
    print(f"{'ok   ' if condicion else 'FALLO'} {nombre}{'' if condicion else f' -> {detalle}'}")


def sqlstate(sentencia):
    try:
        with transaction.atomic(), connection.cursor() as k:
            k.execute(sentencia)
        return 'ok'
    except Error as error:
        return getattr(error.__cause__, 'sqlstate', None)


def navegador(usuario):
    c = Client(SERVER_NAME='localhost')
    c.force_login(usuario, backend='django.contrib.auth.backends.ModelBackend')
    return c


def post(c, ruta, cuerpo=None):
    return c.post(ruta, cuerpo or {}, content_type='application/json', headers={'Idempotency-Key': str(uuid.uuid4())})


def recorrer():
    autor, editor, ajeno, soporte, sinfactor, vinculo = (Usuario.objects.get(email=e) for e in CORREOS.values())
    huerto = Huerto.objects.get(clave='principal')
    ok('rol de la aplicación', connection.cursor().execute('select current_user').fetchone()[0] == 'chilito_pkg_runtime')

    # Administrador sin método fuerte, con los privilegios reales
    n = navegador(sinfactor)
    r = n.get('/api/admin/mantenimientos')
    ok('admin sin método bloqueado en el panel', (r.status_code, r.json().get('code')) == (403, 'mfa-required'), r.status_code)
    ok('admin sin método entra a su cuenta', n.get('/api/cuenta').json().get('mfaRequired') is True)
    ok('su sesión lista métodos', n.get('/_allauth/browser/v1/account/authenticators').status_code == 200)

    # Usuario
    a, e, x = navegador(autor), navegador(editor), navegador(ajeno)
    r = post(a, '/api/huertos/actual/mantenimiento', {'type': 'harvest'})
    ok('usuario registra', r.status_code == 200, r.status_code)
    rid = r.json()['record']['id']

    # Administrador por HTTP
    r = e.get('/api/admin/mantenimientos')
    ok('editor lista su huerto', r.status_code == 200 and r.json()['total'] == 1, r.status_code)
    ok('filtro por estado', e.get('/api/admin/mantenimientos?state=voided').json()['total'] == 0)
    ok('filtro desconocido rechazado', e.get('/api/admin/mantenimientos?x=1').status_code == 400)
    r = post(e, '/api/admin/mantenimientos', {'gardenId': huerto.pk, 'task': 'inspection'})
    ok('editor crea', r.status_code == 200, r.status_code)
    ok('ajeno no ve el huerto', x.get('/api/admin/mantenimientos').json()['total'] == 0)
    ok('ajeno no abre el registro', x.get(f'/api/admin/mantenimientos/{rid}').status_code == 403)
    ok('ajeno no anula', post(x, f'/api/admin/mantenimientos/{rid}/anular', {'reason': 'x', 'revision': 0}).status_code == 403)
    ok('usuario no entra al panel', a.get('/api/admin/mantenimientos').status_code == 403)

    r = post(e, f'/api/admin/mantenimientos/{rid}/corregir', {'task': 'refill', 'reason': 'Mal registrado', 'revision': 0})
    ok('corregir con rol limitado', r.status_code == 200 and r.json()['record']['type'] == 'refill', r.status_code)
    fila = next(i for i in a.get('/api/huertos/actual/mantenimiento').json()['items'] if i['id'] == rid)
    ok('el usuario ve lo corregido', fila['type'] == 'refill', fila['type'])
    ok('el original se conserva', Mantenimiento.objects.get(pk=rid).tipo == 'harvest')
    r = post(e, f'/api/admin/mantenimientos/{rid}/anular', {'reason': 'Datos viejos', 'revision': 0})
    ok('revisión vieja: 409', r.status_code == 409 and r.json()['code'] == 'stale-record', r.status_code)
    ok('motivo vacío: 400', post(e, f'/api/admin/mantenimientos/{rid}/anular', {'reason': '  ', 'revision': 1}).status_code == 400)
    r = post(e, f'/api/admin/mantenimientos/{rid}/anular', {'reason': 'Duplicado', 'revision': 1})
    ok('anular con rol limitado', r.status_code == 200 and r.json()['record']['state'] == 'voided', r.status_code)
    r = e.get(f'/api/admin/mantenimientos/{rid}')
    ok('historial completo', [v['kind'] for v in r.json()['revisions']] == ['correccion', 'anulacion'], r.status_code)
    ok('retirado de la lista del usuario', rid not in [i['id'] for i in a.get('/api/huertos/actual/mantenimiento').json()['items']])
    ok('auditoría del editor', Auditoria.objects.filter(accion='maintenance-voided', actor=editor).count() == 1)
    clave = str(uuid.uuid4())
    ruta, cuerpo = '/api/admin/mantenimientos', {'gardenId': huerto.pk, 'task': 'germination'}
    uno = e.post(ruta, cuerpo, content_type='application/json', headers={'Idempotency-Key': clave})
    dos = e.post(ruta, cuerpo, content_type='application/json', headers={'Idempotency-Key': clave})
    ok('reintento idempotente', uno.json()['record']['id'] == dos.json()['record']['id'], dos.status_code)

    # Privilegios
    ok('runtime no edita mantenimiento', sqlstate(f"update datos_mantenimiento set tipo='refill'") == '42501')
    ok('bloqueo no permite cambios', sqlstate("update datos_mantenimiento set id=id") == '23514')
    ok('runtime no se asigna huertos', sqlstate(f"insert into datos_asignacionmantenimiento(usuario_id,huerto_id,activa,asignada_en) values({ajeno.pk},{huerto.pk},true,now())") == '42501')
    ok('runtime no borra revisiones', sqlstate('delete from datos_revisionmantenimiento') == '42501')
    ok('runtime no se concede capacidades', sqlstate(f"insert into cuentas_usuario_user_permissions(usuario_id,permission_id) select {ajeno.pk},id from auth_permission limit 1") == '42501')

    # Sesión técnica al vencer
    permiso = s.issue_support(autor, huerto.pk, 'pump', True)['permission']
    tecnica = s.open_technical(soporte, permiso['ticket'], permiso['token'])
    c = navegador(soporte)
    ok('15 min no han vencido aún', c.get('/api/admin/soporte').status_code == 200)
    t = c.session
    t[sesion.VISTO] = int(t[sesion.VISTO]) - 901
    t.save()
    r = c.get('/api/admin/soporte')
    ok('admin real vence a los 15 min', r.status_code == 401, r.status_code)
    tecnica.refresh_from_db()
    ok('sesión técnica cerrada', tecnica.cerrada_en is not None and tecnica.motivo_cierre == 'expiry', tecnica.motivo_cierre)
    ok('cierre auditado', Auditoria.objects.filter(accion='technical-closed', sesion_tecnica=tecnica).count() == 1)
    ok('el permiso del usuario sigue vigente', s.permission_state(tecnica.permiso) == 'active')

    # Soporte resuelto y buzón con los privilegios reales. La transacción se revierte: no se envía ningún aviso.
    from datos.models import AvisoCorreo, ConsultaProducto, PermisoSoporte, ResolucionSoporte
    from django.utils import timezone
    caso = s.issue_support(autor, huerto.pk, 'lamp', True)['permission']
    ok('caso nuevo deja aviso pendiente', AvisoCorreo.objects.filter(caso_id=caso['ticket'], tipo='caso_nuevo').count() == 1)
    ok('solicitar token registra aviso', s.request_support_token(soporte, caso['ticket'])['status'] == 'accepted')
    s.resolve_case(soporte, caso['ticket'], 'solucionado', 'Prueba con rol limitado.')
    ok('runtime registra la resolución', ResolucionSoporte.objects.filter(caso_id=caso['ticket']).exists())
    ok('resolución revoca el permiso', s.permission_state(PermisoSoporte.objects.get(caso_id=caso['ticket'])) == 'revoked')
    ok('runtime no altera resoluciones', sqlstate("update datos_resolucionsoporte set nota='x'") == '42501')
    ok('runtime no borra resoluciones', sqlstate('delete from datos_resolucionsoporte') == '42501')
    consulta = s.record_inquiry('Prueba', 'consulta@example.test', 'Mensaje de prueba')
    ok('runtime guarda consultas', ConsultaProducto.objects.filter(pk=consulta.pk).exists())
    ok('editor atiende la consulta', s.update_inquiry(editor, consulta.pk, 'atendida').estado == 'atendida')
    ok('runtime no edita el mensaje', sqlstate("update datos_consultaproducto set mensaje='x'") == '42501')
    ok('runtime no borra consultas', sqlstate('delete from datos_consultaproducto') == '42501')
    ok('el estado no retrocede', sqlstate("update datos_consultaproducto set estado='nueva',atendida_por_id=null,atendida_en=null") == '23514')
    ok('editor archiva la consulta', s.update_inquiry(editor, consulta.pk, 'archivada').estado == 'archivada')
    ok('archivada pasa a atendida', s.update_inquiry(editor, consulta.pk, 'atendida').estado == 'atendida')
    aviso = AvisoCorreo.objects.filter(consulta=consulta).first()
    with transaction.atomic():
        AvisoCorreo.objects.select_for_update(of=('self',)).filter(pk=aviso.pk).update(estado='fallido', intentos=1, ultimo_intento_en=timezone.now())
    ok('runtime registra intentos de aviso', AvisoCorreo.objects.get(pk=aviso.pk).estado == 'fallido')
    ok('runtime no borra avisos', sqlstate('delete from datos_avisocorreo') == '42501')
    ok('runtime no cambia el tipo de aviso', sqlstate("update datos_avisocorreo set tipo='caso_nuevo'") == '42501')
    # Vinculación de huertos con los privilegios reales.
    from datos import vinculacion
    libre = Huerto.objects.get(clave='libre')
    totp = Authenticator.objects.get(user=editor, type='totp')
    reciente = [{'method': 'mfa', 'at': time.time(), 'id': totp.pk, 'type': 'totp'}]
    emitido = vinculacion.emitir(editor, reciente, libre.pk, vinculo.email, 'presencial')
    ok('runtime emite un código de vinculación', emitido['status'] == 'issued' and 'code' in emitido, emitido)
    ok('runtime no crea una membresía sin código', sqlstate(
        'SET CONSTRAINTS membresia_exige_codigo IMMEDIATE; insert into huerto_membresia(usuario_id,huerto_id,activa,asignada_en) '
        f'values ({vinculo.pk},{libre.pk},true,now())') == '23514')
    sqlstate('SET CONSTRAINTS membresia_exige_codigo DEFERRED')
    ok('runtime vincula con el código', vinculacion.consumir(vinculo, emitido['code'])['status'] == 'linked')
    ok('la membresía nueva queda respaldada por su código', sqlstate('SET CONSTRAINTS ALL IMMEDIATE') == 'ok')
    ok('runtime no borra códigos', sqlstate('delete from datos_codigovinculacion') == '42501')
    ok('runtime no cambia el resumen', sqlstate("update datos_codigovinculacion set verificador='x'") == '42501')
    ok('el código consumido no se reabre', sqlstate(
        "update datos_codigovinculacion set estado='pendiente',cerrado_en=null,membresia_id=null") == '23514')
    ok('runtime no desactiva ni reactiva membresías', sqlstate('update huerto_membresia set activa=false') == '42501')
    ok('runtime no borra membresías', sqlstate('delete from huerto_membresia') == '42501')
    ok('una sola membresía activa por cuenta', sqlstate(
        f"select 1 from huerto_membresia where usuario_id={vinculo.pk} and activa having count(*)=1") == 'ok')
    # Guías de cuidado con los privilegios reales.
    from datos import guias
    from datos.models import GuiaCuidado
    ok('la carga inicial está disponible', guias.panel(editor)['guides'][3]['key'] == 'sustrato-perlita')
    ficha = guias.crear(editor, pregunta='¿Runtime?', respuesta='Sí.', orden=500, fuente_nombre='', fuente_url='')['guide']
    ok('runtime crea un borrador', ficha['state'] == 'borrador' and ficha['version'] == 1, ficha)
    editada = guias.editar(editor, ficha['id'], 1, pregunta='¿Editada?', respuesta='Sí.', orden=500, fuente_nombre='Fuente', fuente_url='https://example.test/')['guide']
    publicada = guias.publicar(editor, ficha['id'], editada['version'])['guide']
    ok('runtime publica', publicada['state'] == 'publicada')
    ok('una lectora sin capacidad ve la ficha', any(g['question'] == '¿Editada?' for g in guias.publicadas(ajeno)['guides']))
    retirada = guias.retirar(editor, ficha['id'], publicada['version'])['guide']
    ok('runtime retira y conserva la fila', retirada['state'] == 'retirada' and GuiaCuidado.objects.filter(pk=ficha['id']).exists())
    ok('la gestión queda auditada', Auditoria.objects.filter(guia_id=ficha['id']).count() == 4)
    ok('runtime no borra guías', sqlstate('delete from datos_guiacuidado') == '42501')
    ok('runtime no cambia la clave', sqlstate("update datos_guiacuidado set clave='x'") == '42501')
    ok('runtime no cambia la autoría', sqlstate('update datos_guiacuidado set creado_por_id=null') == '42501')
    ok('runtime no cambia la fecha de creación', sqlstate('update datos_guiacuidado set creado_en=now()') == '42501')
    ok('un cambio directo sin versión se rechaza', sqlstate("update datos_guiacuidado set pregunta='x' where clave='sin-lecturas'") == '23514')
    r = n.get('/api/admin/guias')
    ok('sin capacidad ni factor no entra por la API', (r.status_code, r.json().get('code')) == (403, 'access-denied'), r.status_code)

    # Publicar documentos legales es tarea del propietario, no del rol de la aplicación.
    ok('runtime no publica documentos de privacidad', sqlstate(
        "insert into privacidad_documentoversion(id,tipo,version,contenido_ref,contenido_sha256,registrado_en) "
        "values (gen_random_uuid(),'aviso_privacidad','x','x','" + '0' * 64 + "',now())") == '42501')


def probar():
    with transaction.atomic():
        try:
            cache.clear()
            recorrer()
        finally:
            transaction.set_rollback(True)
    print(f'{sum(resultados)} de {len(resultados)} correctas')
    sys.exit(0 if all(resultados) else 1)


if __name__ == '__main__':
    {'privilegios': privilegios, 'preparar': preparar, 'probar': probar}[sys.argv[1]]()
