"""Regresiones de las diferencias de seguridad corregidas en el cierre de código."""
import json
import logging
import secrets
import sys
import uuid

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, SimpleTestCase, TestCase

from config.registro import FormatoSeguro
from datos.models import AsignacionMantenimiento, Mantenimiento
from huerto.models import Huerto


class Registros(SimpleTestCase):
    def test_cada_aplicacion_usa_el_formato_sin_datos_personales(self):
        for nombre in ('cuentas', 'datos', 'web', 'privacidad', 'django.request', 'django.security'):
            with self.subTest(nombre):
                self.assertIn(nombre, settings.LOGGING['loggers'])
                self.assertEqual(settings.LOGGING['loggers'][nombre]['handlers'], ['consola'])
        self.assertEqual(settings.LOGGING['formatters']['seguro']['()'], 'config.registro.FormatoSeguro')

    def test_el_texto_de_la_excepcion_no_llega_al_registro(self):
        correo = '@'.join(['persona', 'example.test'])     # compuesto: el rastro muestra el código fuente
        try:
            raise ValueError(correo)
        except ValueError:
            registro = logging.LogRecord('x', logging.ERROR, __file__, 1, 'fallo', (), sys.exc_info())
        self.assertNotIn(correo, FormatoSeguro('%(message)s').format(registro))


class IdentificadoresEstrictos(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('man-c@example.test', secrets.token_urlsafe(24))
        EmailAddress.objects.create(user=self.user, email=self.user.email, verified=True, primary=True)
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label='datos', codename='gestionar_mantenimientos'))
        Authenticator.objects.create(user=self.user, type='totp', data={})
        self.huerto = Huerto.objects.create(clave='c-1', nombre='C')
        AsignacionMantenimiento.objects.create(usuario=self.user, huerto=self.huerto)
        self.cliente = Client()
        self.cliente.force_login(self.user, backend='django.contrib.auth.backends.ModelBackend')

    def crear(self, garden):
        return self.cliente.post('/api/admin/mantenimientos', json.dumps({'gardenId': garden, 'task': 'refill'}), content_type='application/json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    def test_rechaza_tipos_laxos(self):
        for valor in (True, 1.0, 1.5, None, [], 0, -1, f'{self.huerto.pk}_0', f' {self.huerto.pk}', '١', '1e3', '9' * 19):
            with self.subTest(valor):
                self.assertEqual(self.crear(valor).status_code, 400)
        self.assertFalse(Mantenimiento.objects.exists())

    def test_acepta_entero_y_digitos(self):
        for valor in (self.huerto.pk, str(self.huerto.pk)):
            self.assertEqual(self.crear(valor).status_code, 200, valor)

    def test_filtros_y_pagina(self):
        for consulta in ('page=1_0', 'page=%D9%A1', 'page=0', 'page=10001', 'garden=1_0', 'garden=-1', 'garden=%D9%A1', 'otro=1', 'state=x'):
            with self.subTest(consulta):
                self.assertEqual(self.cliente.get('/api/admin/mantenimientos?' + consulta).status_code, 400)
        cuerpo = self.cliente.get(f'/api/admin/mantenimientos?page=1&garden={self.huerto.pk}').json()
        self.assertEqual(set(cuerpo), {'status', 'items', 'page', 'total', 'gardens'})
        self.assertEqual(cuerpo['gardens'], [{'id': self.huerto.pk, 'name': 'C'}])
