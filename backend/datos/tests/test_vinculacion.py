"""Vinculación de huertos sobre PostgreSQL temporal y correo en memoria. No se envía nada real.

Cubre: éxito, cuenta incorrecta, vencido, revocado, usado, reemplazado, intentos, límite por cuenta,
concurrencia, idempotencia, reautenticación, permisos, reglas de membresía, correo y persistencia.
"""
import json
import secrets
import threading
import time
import uuid
from datetime import timedelta
from smtplib import SMTPRecipientsRefused
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, connection, connections, transaction
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone

from datos import services, vinculacion
from datos.models import Auditoria, CodigoVinculacion, Dispositivo
from huerto.models import Huerto, Membresia
from web.models import Idempotencia


def en_paralelo(*tareas):
    """Ejecuta cada tarea en su propio hilo y conexión, arrancando a la vez."""
    barrera, resultados = threading.Barrier(len(tareas)), [None] * len(tareas)

    def correr(i, tarea):
        try:
            barrera.wait()
            resultados[i] = tarea()
        except Exception as error:   # se devuelve para que la prueba lo inspeccione
            resultados[i] = error
        finally:
            connections.close_all()
    hilos = [threading.Thread(target=correr, args=(i, t)) for i, t in enumerate(tareas)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(60)
    return resultados


@override_settings(ORIGIN='https://chilito.example.test',
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class Base(TransactionTestCase):
    def setUp(self):
        if not str(connection.settings_dict['NAME']).startswith('test_chilito_integracion_sinteticos'):
            raise RuntimeError('Solo en la base temporal de pruebas.')
        cache.clear()
        self.operador = self.cuenta('operador@example.test')
        self.ana = self.cuenta('ana@example.test')
        self.beto = self.cuenta('beto@example.test')
        self.root = self.cuenta('root@example.test', is_staff=True, is_superuser=True)
        self.huerto = Huerto.objects.create(clave='vinc-a', nombre='Huerto A')
        self.huerto_b = Huerto.objects.create(clave='vinc-b', nombre='Huerto B')
        Dispositivo.objects.create(huerto=self.huerto, identificador='vinc-device-a')
        Dispositivo.objects.create(huerto=self.huerto_b, identificador='vinc-device-b')
        self.totp = self.conceder(self.operador)
        Authenticator.objects.get_or_create(user=self.root, type='totp', defaults={'data': {}})

    def cuenta(self, email, verificada=True, **campos):
        user = get_user_model().objects.create_user(email, secrets.token_urlsafe(24), **campos)
        EmailAddress.objects.create(user=user, email=email, verified=verificada, primary=True)
        return user

    def conceder(self, user):
        user.user_permissions.add(Permission.objects.get(content_type__app_label='datos', codename='vincular_huertos'))
        return Authenticator.objects.get_or_create(user=user, type='totp', defaults={'data': {}})[0]

    def registros(self, autenticador=None, hace=0, tipo='totp'):
        autenticador = autenticador or self.totp
        return [{'method': 'mfa', 'at': time.time() - hace, 'id': autenticador.pk, 'type': tipo}]

    def emitir(self, cuenta=None, huerto=None, entrega='presencial'):
        return vinculacion.emitir(self.operador, self.registros(), (huerto or self.huerto).pk,
                                  (cuenta or self.ana).email, entrega)

    def vencer(self):
        return patch('datos.vinculacion.timezone.now', return_value=timezone.now() + timedelta(minutes=11))



class VinculacionTests(Base):
    # Emisión: capacidad, factor y reautenticación efectiva -------------------------------------
    def test_emitir_exige_capacidad_factor_y_reautenticacion_reciente(self):
        for actor in (self.root, self.ana):
            with self.subTest(actor=actor.email), self.assertRaises(PermissionDenied):
                vinculacion.emitir(actor, self.registros(), self.huerto.pk, self.beto.email, 'presencial')
        sin_factor = self.cuenta('sinfactor@example.test')
        sin_factor.user_permissions.add(Permission.objects.get(codename='vincular_huertos'))
        with self.assertRaises(services.FactorRequerido):
            vinculacion.emitir(sin_factor, [], self.huerto.pk, self.ana.email, 'presencial')
        otro = self.conceder(self.beto)
        casos = {'sin registros': [], 'hace seis minutos': self.registros(hace=360),
                 'códigos de recuperación': self.registros(tipo='recovery_codes'),
                 'factor de otra cuenta': self.registros(autenticador=otro),
                 'solo contraseña': [{'method': 'password', 'at': time.time()}]}
        for nombre, registros in casos.items():
            with self.subTest(nombre), self.assertRaises(vinculacion.ReautenticacionRequerida):
                vinculacion.emitir(self.operador, registros, self.huerto.pk, self.ana.email, 'presencial')
        self.assertFalse(CodigoVinculacion.objects.exists())

    def test_formato_y_resumen_del_codigo(self):
        emitido = self.emitir()
        codigo = emitido['code']
        self.assertRegex(codigo, r'^[0-9A-HJKMNP-TV-Z]{5}(-[0-9A-HJKMNP-TV-Z]{5}){3}-[0-9A-HJKMNP-TV-Z]{6}$')
        fila = CodigoVinculacion.objects.get()
        self.assertNotIn(codigo.replace('-', ''), fila.verificador)
        self.assertEqual(fila.vence_en - fila.emitido_en, timedelta(minutes=10))
        self.assertEqual(vinculacion.normalizar(codigo.lower().replace('-', ' ')), codigo.replace('-', ''))

    # Consumo ----------------------------------------------------------------------------------
    def test_vinculacion_valida_crea_membresia_y_audita_sin_codigo(self):
        codigo = self.emitir()['code']
        resultado = vinculacion.consumir(self.ana, codigo)
        self.assertEqual(resultado['status'], 'linked')
        self.assertTrue(Membresia.objects.filter(usuario=self.ana, huerto=self.huerto, activa=True).exists())
        fila = CodigoVinculacion.objects.get()
        self.assertEqual((fila.estado, fila.membresia_id), ('consumido', resultado['membership']))
        self.assertEqual(set(Auditoria.objects.values_list('accion', flat=True)), {'binding-issued', 'binding-consumed'})
        self.assertEqual(services.garden_projection(self.ana, services.current_garden(self.ana))['status'], 'waiting')
        self.assertEqual(vinculacion.consumir(self.ana, codigo)['status'], 'already-linked')

    def test_cuenta_incorrecta_recibe_el_mismo_rechazo_y_no_gasta_el_codigo_ajeno(self):
        codigo = self.emitir()['code']
        inventado = vinculacion.generar_codigo()
        self.assertEqual(vinculacion.consumir(self.beto, codigo), {'status': 'rejected'})
        self.assertEqual(vinculacion.consumir(self.beto, inventado), {'status': 'rejected'})
        self.assertEqual(CodigoVinculacion.objects.get().intentos, 0)
        self.assertEqual(vinculacion.consumir(self.ana, codigo)['status'], 'linked')

    def test_vencido_revocado_y_reemplazado_se_rechazan_igual(self):
        codigo = self.emitir()['code']
        with self.vencer():
            self.assertEqual(vinculacion.consumir(self.ana, codigo), {'status': 'rejected'})
        nuevo = self.emitir()['code']
        self.assertEqual(CodigoVinculacion.objects.filter(estado='reemplazado').count(), 1)
        self.assertEqual(vinculacion.consumir(self.ana, codigo), {'status': 'rejected'})
        fila = CodigoVinculacion.objects.get(estado='pendiente')
        vinculacion.revocar(self.operador, self.registros(), fila.pk)
        self.assertEqual(vinculacion.consumir(self.ana, nuevo), {'status': 'rejected'})
        with self.assertRaises(services.RegistroDesactualizado):
            vinculacion.revocar(self.operador, self.registros(), fila.pk)
        self.assertFalse(Membresia.objects.exists())

    def test_cinco_intentos_bloquean_el_codigo(self):
        codigo = self.emitir()['code']
        for _ in range(4):
            self.assertEqual(vinculacion.consumir(self.ana, vinculacion.generar_codigo())['status'], 'rejected')
        self.assertEqual(vinculacion.consumir(self.ana, 'no-es-un-codigo')['status'], 'limited')
        self.assertEqual(CodigoVinculacion.objects.get().estado, 'bloqueado')
        self.assertEqual(vinculacion.consumir(self.ana, codigo)['status'], 'limited')
        self.assertFalse(Membresia.objects.exists())

    def test_limite_por_cuenta_sin_codigo_pendiente_y_antes_del_resumen(self):
        for _ in range(10):
            self.assertEqual(vinculacion.consumir(self.beto, vinculacion.generar_codigo())['status'], 'rejected')
        with patch('datos.vinculacion.check_password') as comprobar:
            self.assertEqual(vinculacion.consumir(self.beto, vinculacion.generar_codigo())['status'], 'limited')
            comprobar.assert_not_called()
        self.assertEqual(Auditoria.objects.filter(actor=self.beto, accion='binding-rejected').count(), 10)

    def test_intentos_y_auditoria_persisten_aunque_falle_lo_siguiente(self):
        self.emitir()
        with self.assertRaises(RuntimeError), transaction.atomic():
            vinculacion.consumir(self.ana, vinculacion.generar_codigo())
            raise RuntimeError('fallo posterior de la petición')
        # Un error ajeno deshace su transacción; el rechazo confirmado por sí solo sí persiste.
        vinculacion.consumir(self.ana, vinculacion.generar_codigo())
        self.assertEqual(CodigoVinculacion.objects.get().intentos, 1)
        self.assertEqual(Auditoria.objects.filter(accion='binding-rejected').count(), 1)

    # Reglas de membresía ----------------------------------------------------------------------
    def test_reglas_de_membresia(self):
        vinculacion.consumir(self.ana, self.emitir()['code'])
        self.assertEqual(self.emitir(cuenta=self.ana, huerto=self.huerto_b)['reason'], 'account-has-garden')
        self.assertEqual(self.emitir(cuenta=self.beto)['reason'], 'garden-occupied')
        Membresia.objects.filter(usuario=self.ana).update(activa=False)
        self.assertEqual(self.emitir(cuenta=self.ana)['reason'], 'previous-membership')
        nuevo = self.emitir(cuenta=self.beto)['code']
        self.assertEqual(vinculacion.consumir(self.beto, nuevo)['status'], 'linked')
        self.assertFalse(Membresia.objects.get(usuario=self.ana).activa)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Membresia.objects.bulk_create([Membresia(usuario=self.beto, huerto=self.huerto_b)])
        sin_verificar = self.cuenta('sinverificar@example.test', verificada=False)
        self.assertEqual(self.emitir(cuenta=sin_verificar, huerto=self.huerto_b)['reason'], 'account-not-eligible')

    # Concurrencia -----------------------------------------------------------------------------
    def test_dos_peticiones_con_el_mismo_codigo_crean_una_sola_membresia(self):
        codigo = self.emitir()['code']
        resultados = en_paralelo(lambda: vinculacion.consumir(self.ana, codigo), lambda: vinculacion.consumir(self.ana, codigo))
        self.assertEqual(sorted(r['status'] for r in resultados), ['already-linked', 'linked'])
        self.assertEqual(Membresia.objects.count(), 1)

    def test_dos_cuentas_y_el_mismo_huerto_a_la_vez(self):
        codigo = self.emitir()['code']
        resultados = en_paralelo(lambda: vinculacion.consumir(self.ana, codigo),
                                 lambda: vinculacion.consumir(self.beto, codigo),
                                 lambda: self.emitir(cuenta=self.beto))
        self.assertTrue(all(isinstance(r, dict) for r in resultados), resultados)
        self.assertLessEqual(Membresia.objects.filter(huerto=self.huerto, activa=True).count(), 1)
        self.assertEqual(resultados[1]['status'], 'rejected')
        if resultados[0]['status'] == 'linked':
            self.assertEqual(resultados[2], {'status': 'refused', 'reason': 'garden-occupied'})
        else:
            self.assertEqual(resultados[2]['status'], 'issued')
            self.assertEqual(vinculacion.consumir(self.beto, resultados[2]['code'])['status'], 'linked')
        self.assertEqual(Membresia.objects.filter(huerto=self.huerto, activa=True).count(), 1)

    # Correo -----------------------------------------------------------------------------------
    def test_correo_solo_tras_entrega_presencial_y_al_correo_verificado(self):
        self.assertEqual(self.emitir(entrega='correo')['reason'], 'mail-requires-in-person')
        self.emitir()
        emitido = self.emitir(entrega='correo')   # el envío ocurre al confirmar la transacción de emitir
        self.assertNotIn('code', emitido)
        self.assertEqual(emitido['binding']['mail'], 'aceptado_smtp')
        mensaje = mail.outbox[-1]
        self.assertEqual(mensaje.to, ['ana@example.test'])
        codigo = [linea.strip() for linea in mensaje.body.splitlines() if linea.startswith('    ')][0]
        self.assertNotIn(codigo, mensaje.subject)
        self.assertNotIn(codigo.replace('-', ''), mensaje.body.replace(codigo, ''))
        self.assertEqual(vinculacion.consumir(self.ana, codigo)['status'], 'linked')

    def test_envio_rechazado_o_incierto_invalida_el_codigo(self):
        self.emitir()
        for error, esperado in ((SMTPRecipientsRefused({}), 'rechazado'), (TimeoutError('sin respuesta'), 'incierto')):
            with self.subTest(esperado), patch('django.core.mail.EmailMessage.send', side_effect=error), \
                    self.assertLogs('datos.vinculacion', 'WARNING') as registro:
                emitido = self.emitir(entrega='correo')
            fila = CodigoVinculacion.objects.get(pk=emitido['binding']['id'])
            self.assertEqual((fila.envio, fila.estado), (esperado, 'revocado'))
            self.assertEqual(emitido['binding']['mail'], esperado)
            self.assertNotIn('ana@example.test', ' '.join(registro.output))

    # Historial en la base ---------------------------------------------------------------------
    def test_el_codigo_no_se_borra_ni_cambia_ni_se_reabre(self):
        self.emitir()
        fila = CodigoVinculacion.objects.get()
        vinculacion.revocar(self.operador, self.registros(), fila.pk)
        for cambio in ({'estado': 'pendiente', 'cerrado_en': None}, {'verificador': 'pbkdf2_sha256$1$a$b'}, {'intentos': 3}):
            with self.subTest(cambio), self.assertRaises(IntegrityError), transaction.atomic():
                CodigoVinculacion.objects.filter(pk=fila.pk).update(**cambio)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CodigoVinculacion.objects.filter(pk=fila.pk).delete()


class VinculacionHTTPTests(Base):
    """Las rutas: reautenticación por sesión, recibos sin secreto, repeticiones y persistencia."""

    def cliente(self, user, mfa=False):
        client = Client(HTTP_HOST='127.0.0.1')
        client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        if mfa:
            session = client.session
            session['account_authentication_methods'] = self.registros()
            session.save()
        return client

    def post(self, client, path, payload, key=None):
        return client.post(path, json.dumps(payload), content_type='application/json',
                           HTTP_IDEMPOTENCY_KEY=str(key or uuid.uuid4()))

    def test_emision_http_exige_reautenticacion_y_el_recibo_no_guarda_el_codigo(self):
        datos = {'garden': str(self.huerto.pk), 'email': self.ana.email, 'delivery': 'presencial'}
        sin_mfa = self.post(self.cliente(self.operador), '/api/admin/vinculacion/emitir', datos)
        self.assertEqual((sin_mfa.status_code, sin_mfa.json()['code']), (403, 'reauthentication-required'))
        cliente, clave = self.cliente(self.operador, mfa=True), uuid.uuid4()
        primera = self.post(cliente, '/api/admin/vinculacion/emitir', datos, key=clave).json()
        self.assertIn('code', primera)
        repetida = self.post(cliente, '/api/admin/vinculacion/emitir', datos, key=clave).json()
        self.assertIsNone(repetida.get('code'))   # el recibo guardado lo descartó
        self.assertEqual(CodigoVinculacion.objects.count(), 1)
        self.assertNotIn(primera['code'], json.dumps(list(Idempotencia.objects.values_list('respuesta', flat=True))))
        listado = cliente.get('/api/admin/vinculacion').json()
        self.assertNotIn(primera['code'], json.dumps(listado))
        self.assertNotIn('verificador', json.dumps(listado))
        self.assertEqual(self.cliente(self.ana).get('/api/admin/vinculacion').status_code, 403)

    def test_repeticiones_y_persistencia(self):
        codigo = self.emitir()['code']
        cliente, clave = self.cliente(self.ana), uuid.uuid4()
        primera = self.post(cliente, '/api/vinculacion', {'code': codigo}, key=clave).json()
        self.assertEqual(primera['status'], 'linked')
        self.assertEqual(self.post(cliente, '/api/vinculacion', {'code': codigo}, key=clave).json(), primera)
        self.assertEqual(self.post(cliente, '/api/vinculacion', {'code': codigo}).json()['status'], 'already-linked')
        self.assertEqual(Membresia.objects.count(), 1)
        # Recarga y nuevo inicio de sesión: la asociación está en la base, no en el navegador.
        self.assertEqual(self.cliente(self.ana).get('/api/huertos/actual').json()['garden']['status'], 'waiting')
        Membresia.objects.filter(usuario=self.ana).update(activa=False)
        self.assertEqual(self.post(cliente, '/api/vinculacion', {'code': codigo}, key=clave).status_code, 403)
        otro = self.post(self.cliente(self.beto), '/api/vinculacion', {'code': codigo, 'extra': 1})
        self.assertEqual(otro.status_code, 400)
