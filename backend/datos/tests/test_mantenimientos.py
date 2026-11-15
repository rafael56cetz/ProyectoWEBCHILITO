"""CRUD de mantenimientos contra PostgreSQL real: triggers, GRANT y bloqueos no se simulan."""
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import threading

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from datos import services as s
from datos.models import AsignacionMantenimiento, Auditoria, Mantenimiento, RevisionMantenimiento
from huerto.models import Huerto, Membresia
from privacidad import politicas
from privacidad import services as privacidad
from privacidad.models import ConteoNavegacion, DocumentoVersion, FinalidadOpcional

CAP = 'gestionar_mantenimientos'


def cuenta(email):
    usuario = get_user_model().objects.create(email=email, password='x')
    EmailAddress.objects.create(user=usuario, email=email, verified=True, primary=True)
    return usuario


class MantenimientoTests(TestCase):
    def setUp(self):
        self.autor, self.editor, self.ajeno = (cuenta(f'{n}@example.test') for n in ('autor', 'editor', 'ajeno'))
        self.huerto = Huerto.objects.create(clave='uno', nombre='Uno')
        self.otro = Huerto.objects.create(clave='dos', nombre='Dos')
        Membresia.objects.create(usuario=self.autor, huerto=self.huerto)
        permiso = Permission.objects.get(content_type__app_label='datos', codename=CAP)
        self.editor.user_permissions.add(permiso)
        self.ajeno.user_permissions.add(permiso)
        for admin in (self.editor, self.ajeno):
            Authenticator.objects.create(user=admin, type='totp', data={})
        AsignacionMantenimiento.objects.create(usuario=self.editor, huerto=self.huerto)
        AsignacionMantenimiento.objects.create(usuario=self.ajeno, huerto=self.otro)
        self.registro = s.record_maintenance(self.autor, self.huerto.pk, 'harvest')

    def lista_usuario(self):
        return list(s.maintenance_history(self.autor, self.huerto.pk))

    def test_correccion_conserva_el_original_y_cambia_lo_vigente(self):
        fila = s.correct_maintenance(self.editor, self.registro.pk, 'refill', 'Se registró mal', 0)
        self.assertEqual((fila.tipo, fila.tipo_vigente, fila.revision), ('harvest', 'refill', 1))
        self.assertEqual(self.lista_usuario()[0].tipo_vigente, 'refill')

    def test_anulacion_retira_de_la_lista_y_conserva_el_historial(self):
        s.void_maintenance(self.editor, self.registro.pk, 'Duplicado', 0)
        self.assertEqual(self.lista_usuario(), [])
        self.assertTrue(Mantenimiento.objects.filter(pk=self.registro.pk).exists())
        self.assertEqual(s.admin_maintenance(self.editor, state='voided').count(), 1)

    def test_auditoria_identifica_al_editor_y_conserva_al_autor(self):
        s.void_maintenance(self.editor, self.registro.pk, 'Duplicado', 0)
        evento = Auditoria.objects.get(accion='maintenance-voided')
        self.assertEqual(evento.actor, self.editor)
        self.assertEqual(Mantenimiento.objects.get(pk=self.registro.pk).actor, self.autor)

    def test_motivo_obligatorio(self):
        for motivo in ['', '   ', 'x' * 501, None]:
            with self.assertRaises(ValidationError):
                s.void_maintenance(self.editor, self.registro.pk, motivo, 0)

    def test_sin_capacidad_rechazado(self):
        with self.assertRaises(PermissionDenied):
            s.void_maintenance(self.autor, self.registro.pk, 'Motivo', 0)

    def test_huerto_no_asignado_rechazado(self):
        with self.assertRaises(PermissionDenied):
            s.void_maintenance(self.ajeno, self.registro.pk, 'Motivo', 0)
        with self.assertRaises(PermissionDenied):
            s.maintenance_detail(self.ajeno, self.registro.pk)
        self.assertEqual(s.admin_maintenance(self.ajeno).count(), 0)

    def test_asignacion_inactiva_retira_el_acceso(self):
        AsignacionMantenimiento.objects.filter(usuario=self.editor).update(activa=False)
        with self.assertRaises(PermissionDenied):
            s.correct_maintenance(self.editor, self.registro.pk, 'refill', 'Motivo', 0)

    def test_registro_desactualizado(self):
        s.correct_maintenance(self.editor, self.registro.pk, 'refill', 'Primera', 0)
        with self.assertRaises(s.RegistroDesactualizado):
            s.void_maintenance(self.editor, self.registro.pk, 'Sobre datos viejos', 0)

    def test_anulado_no_admite_mas_cambios(self):
        s.void_maintenance(self.editor, self.registro.pk, 'Duplicado', 0)
        with self.assertRaises(s.RegistroDesactualizado):
            s.correct_maintenance(self.editor, self.registro.pk, 'refill', 'Tarde', 1)

    def test_correccion_al_mismo_tipo_rechazada(self):
        with self.assertRaises(ValidationError):
            s.correct_maintenance(self.editor, self.registro.pk, 'harvest', 'Igual', 0)

    def test_crear_exige_asignacion_y_conserva_identidad(self):
        fila = s.admin_record_maintenance(self.editor, self.huerto.pk, 'inspection')
        self.assertEqual(fila.actor, self.editor)
        with self.assertRaises(PermissionDenied):
            s.admin_record_maintenance(self.editor, self.otro.pk, 'inspection')

    def test_capacidad_convierte_en_administrador(self):
        self.assertEqual(s.session_contract(self.editor)['role'], 'admin')
        self.assertTrue(s.is_admin(self.editor))
        self.assertFalse(s.is_admin(self.autor))

    def test_la_base_impide_borrar_revisiones(self):
        s.void_maintenance(self.editor, self.registro.pk, 'Duplicado', 0)
        with self.assertRaises(Exception), transaction.atomic():
            RevisionMantenimiento.objects.all().delete()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Mantenimiento.objects.filter(pk=self.registro.pk).update(tipo='refill')


class ConcurrenciaTests(TransactionTestCase):
    """Conexiones reales y simultáneas: el resultado no debe depender del orden."""

    def en_paralelo(self, tareas):
        barrera = threading.Barrier(len(tareas))

        def correr(tarea):
            try:
                barrera.wait(timeout=10)
                return tarea()
            except Exception as error:
                return error
            finally:
                connections.close_all()

        with ThreadPoolExecutor(len(tareas)) as grupo:
            return list(grupo.map(correr, tareas))

    def test_dos_revisiones_simultaneas_solo_una_gana(self):
        editor = cuenta('editor@example.test')
        huerto = Huerto.objects.create(clave='uno', nombre='Uno')
        editor.user_permissions.add(Permission.objects.get(content_type__app_label='datos', codename=CAP))
        Authenticator.objects.create(user=editor, type='totp', data={})
        AsignacionMantenimiento.objects.create(usuario=editor, huerto=huerto)
        registro = Mantenimiento.objects.create(actor=editor, huerto=huerto, tipo='harvest')
        resultados = self.en_paralelo([
            lambda: s.void_maintenance(editor, registro.pk, 'Duplicado', 0),
            lambda: s.correct_maintenance(editor, registro.pk, 'refill', 'Mal registrado', 0),
            lambda: s.void_maintenance(editor, registro.pk, 'Otra vez', 0),
            lambda: s.correct_maintenance(editor, registro.pk, 'inspection', 'Otro motivo', 0),
        ])
        conflictos = [r for r in resultados if isinstance(r, s.RegistroDesactualizado)]
        self.assertEqual(len(conflictos), 3, resultados)
        self.assertEqual(RevisionMantenimiento.objects.filter(mantenimiento=registro).count(), 1)
        self.assertEqual(Auditoria.objects.filter(accion__in=['maintenance-corrected', 'maintenance-voided']).count(), 1)

    def test_contador_no_pierde_visitas_simultaneas(self):
        huella = '0' * 64
        for tipo in ('aviso_privacidad', 'politica_cookies'):
            DocumentoVersion.objects.get_or_create(tipo=tipo, version='prueba', defaults={'contenido_ref': 'x', 'contenido_sha256': huella})
        FinalidadOpcional.objects.get_or_create(codigo=politicas.FINALIDAD_ESTADISTICAS, defaults={'descripcion': 'Estadísticas'})
        valor = privacidad.decidir_cookies(AnonymousUser(), None, True)
        tareas = [partial(privacidad.contar_seccion, AnonymousUser(), valor, f'identificador-{n}', 'inicio') for n in range(8)]
        self.assertEqual(self.en_paralelo(tareas), [True] * 8)
        self.assertEqual(ConteoNavegacion.objects.get(seccion='inicio').visitas, 8)
