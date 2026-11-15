"""Pruebas del perfil preparatorio; no acreditan persistencia ni un flujo HTTP."""
from django.core.exceptions import ValidationError
from django.db import models
from django.test import SimpleTestCase
from django.utils import timezone

from .models import Usuario


class PerfilBienvenidaTests(SimpleTestCase):
    def test_datos_personales_son_opcionales(self):
        usuario = Usuario(email="perfil@example.test")
        for nombre in ("first_name", "last_name", "alias"):
            with self.subTest(campo=nombre):
                campo = Usuario._meta.get_field(nombre)
                self.assertTrue(campo.blank)
                self.assertEqual(campo.clean("", usuario), "")
        self.assertEqual(usuario.nombre_presentacion, "Bienvenido")

    def test_alias_admite_hasta_64_caracteres(self):
        campo = Usuario._meta.get_field("alias")
        self.assertEqual(campo.clean("á" * 64, None), "á" * 64)
        with self.assertRaises(ValidationError):
            campo.clean("á" * 65, None)

    def test_alias_no_es_identificador_unico(self):
        campo = Usuario._meta.get_field("alias")
        self.assertFalse(campo.unique)
        self.assertFalse(campo.primary_key)
        for constraint in Usuario._meta.constraints:
            if isinstance(constraint, models.UniqueConstraint):
                self.assertNotIn("alias", constraint.fields)
        uno = Usuario(email="uno@example.test", alias="Jardín")
        otro = Usuario(email="otro@example.test", alias="Jardín")
        uno.clean()
        otro.clean()
        self.assertEqual(uno.nombre_presentacion, otro.nombre_presentacion)

    def test_limpieza_normaliza_alias_sin_cambiar_nombre_apellido(self):
        usuario = Usuario(email="perfil@example.test", first_name="Ana", last_name="López", alias="  Mi huerto\t")
        usuario.clean()
        self.assertEqual(usuario.alias, "Mi huerto")
        self.assertEqual((usuario.first_name, usuario.last_name), ("Ana", "López"))

    def test_alias_compuesto_solo_por_espacios_se_normaliza_a_vacio(self):
        usuario = Usuario(email="perfil@example.test", alias=" \t\n")
        usuario.clean()
        self.assertEqual(usuario.alias, "")

    def test_presentacion_prioriza_alias_luego_nombre(self):
        usuario = Usuario(email="perfil@example.test", first_name="Ana", last_name="López", alias="Mi huerto")
        self.assertEqual(usuario.nombre_presentacion, "Mi huerto")
        usuario.alias = ""
        self.assertEqual(usuario.nombre_presentacion, "Ana")
        usuario.first_name = ""
        self.assertEqual(usuario.nombre_presentacion, "Bienvenido")

    def test_ahora_no_puede_registrarse_sin_exigir_nombres(self):
        usuario = Usuario(email="perfil@example.test")
        self.assertIsNone(usuario.bienvenida_atendida_en)
        atendida = timezone.now()
        # Estado en memoria: el servicio futuro guardará esta fecha al completar u omitir.
        usuario.bienvenida_atendida_en = atendida
        usuario.clean()
        self.assertEqual(usuario.bienvenida_atendida_en, atendida)
        self.assertEqual((usuario.first_name, usuario.last_name, usuario.alias), ("", "", ""))
