"""Ciclos de planta y recomendaciones (web.0007), sobre PostgreSQL."""
import importlib
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from datos.models import Actuacion, Auditoria, Cuidado, Dispositivo, GuiaCuidado, Medicion, MedicionPlanta, Notificacion
from tests import cuenta, publicar_textos

from .models import Planta, PlantaCiclo, PlantaEtapa
from .tests import AyudasHuerto, medir

MIGRACION = importlib.import_module('web.migrations.0007_ciclos_planta')
MERIDA = ZoneInfo('America/Merida')


class BaseCiclos(AyudasHuerto, TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def planta(self, huerto_id, numero=1):
        return Planta.objects.get(huerto_id=huerto_id, numero=numero)

    def ciclos(self, huerto_id, numero=1):
        return list(PlantaCiclo.objects.filter(planta=self.planta(huerto_id, numero)).order_by('numero'))

    def terminar(self, huerto_id, numero=1, cliente=None, **datos):
        return self.post(f'/api/huertos/{huerto_id}/plantas/{numero}/terminar-ciclo', {'reason': 'no_germino', **datos}, cliente)

    def ficha(self, huerto_id, numero=1):
        respuesta = self.client.get(f'/api/huertos/{huerto_id}/plantas/{numero}')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def recomendaciones(self, situacion=None):
        filas = Notificacion.objects.filter(destinatario=self.dueña, enlace__startswith='#huerto/plantas/')
        return filas.filter(titulo__contains=situacion) if situacion else filas


class Ciclos(BaseCiclos):
    def test_cada_planta_nace_con_su_ciclo_1_abierto(self):
        huerto_id = self.huerto_vinculado()
        for numero in (1, 2, 3):
            [ciclo] = self.ciclos(huerto_id, numero)
            self.assertEqual((ciclo.numero, ciclo.fin, ciclo.motivo, ciclo.nota), (1, None, None, ''))
        ficha = self.ficha(huerto_id)
        self.assertEqual((ficha['cycle']['number'], ficha['pastCycles']), (1, []))

    def test_ciclo_1_de_las_plantas_existentes(self):
        """El relleno de la migración: desde la primera etapa (medianoche de Mérida) o desde la creación del huerto.
        (Una planta sin ciclo ya no puede existir: se prueba la misma expresión que usa la migración.)"""
        huerto_id = self.huerto_vinculado()
        primera = PlantaEtapa.objects.filter(planta=self.planta(huerto_id, 1)).first()
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
            cursor.execute('ALTER TABLE huerto_planta_etapa DISABLE TRIGGER inmutable')
            PlantaEtapa.objects.filter(pk=primera.pk).update(desde=timezone.localdate() - timedelta(days=40))
            PlantaEtapa.objects.filter(planta=self.planta(huerto_id, 2)).delete()
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
            cursor.execute('ALTER TABLE huerto_planta_etapa ENABLE TRIGGER inmutable')
            consulta = f'SELECT {MIGRACION.INICIO_CICLO_1} FROM huerto_planta p JOIN huerto h ON h.id=p.huerto_id WHERE p.id=%s'
            cursor.execute(consulta, [self.planta(huerto_id, 1).pk])
            self.assertEqual(cursor.fetchone()[0], datetime.combine(timezone.localdate() - timedelta(days=40), time(), MERIDA))
            cursor.execute(consulta, [self.planta(huerto_id, 2).pk])
            from huerto.models import Huerto
            self.assertEqual(cursor.fetchone()[0], Huerto.objects.get(pk=huerto_id).creado_en)
        self.assertIn('NOT EXISTS (SELECT 1 FROM planta_ciclo c WHERE c.planta_id=p.id)', MIGRACION.CICLO_1, 'no duplica ciclos')
        self.assertEqual(set(PlantaEtapa.objects.filter(planta__huerto_id=huerto_id).values_list('ciclo__numero', flat=True)), {1},
                         'cada etapa queda ligada a su ciclo')

    def test_terminar_ciclo_sin_borrar_nada(self):
        huerto_id = self.huerto_vinculado()
        ruta = f'/api/huertos/{huerto_id}/plantas/1'
        hace_10 = (timezone.localdate() - timedelta(days=10)).isoformat()
        self.assertEqual(self.post(ruta, {'name': 'Chile bravo', 'sowingDate': hace_10, 'stage': 'germinacion'}).status_code, 200)
        hace_una_hora = (timezone.now() - timedelta(hours=1)).isoformat()
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/cuidados', {'type': 'germinacion', 'plant': 1, 'doneAt': hace_una_hora}).status_code, 200)
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/cuidados', {'type': 'sustrato', 'plant': 2, 'doneAt': hace_una_hora}).status_code, 200)
        antes = {'etapas': PlantaEtapa.objects.count(), 'cuidados': Cuidado.objects.count()}
        etapas_antes = set(PlantaEtapa.objects.values_list('pk', flat=True))
        cuidados_antes = set(Cuidado.objects.values_list('pk', flat=True))

        respuesta = self.terminar(huerto_id, reason='no_germino', note='  Nunca brotó.\nLo intento otra vez.  ')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        cuerpo = respuesta.json()
        self.assertEqual((cuerpo['cycle']['number'], cuerpo['ended']['number'], cuerpo['ended']['reason']), (2, 1, 'no_germino'))
        planta = self.planta(huerto_id)
        self.assertEqual((planta.nombre, planta.etapa, planta.etapa_desde, planta.fecha_siembra), ('Chile bravo', 'sin_sembrar', None, None))
        uno, dos = self.ciclos(huerto_id)
        self.assertEqual((uno.motivo, uno.nota, uno.cerrado_por_id, dos.fin, dos.inicio), ('no_germino', 'Nunca brotó.\nLo intento otra vez.', self.dueña.pk, None, uno.fin))
        self.assertTrue(Auditoria.objects.filter(accion='terminar_ciclo', actor=self.dueña, entidad_id=str(planta.pk)).exists())

        # Nada se borra: todas las filas anteriores siguen, y solo se añadió la etapa «sin_sembrar» del ciclo nuevo.
        self.assertTrue(etapas_antes <= set(PlantaEtapa.objects.values_list('pk', flat=True)))
        self.assertTrue(cuidados_antes <= set(Cuidado.objects.values_list('pk', flat=True)))
        self.assertEqual((PlantaEtapa.objects.count(), Cuidado.objects.count()), (antes['etapas'] + 1, antes['cuidados']))

        ficha = self.ficha(huerto_id)
        self.assertEqual(ficha['cycle']['number'], 2)
        self.assertEqual([e['stage'] for e in ficha['stages']], ['sin_sembrar'], 'solo el ciclo actual')
        self.assertEqual((ficha['care'], ficha['plant']['daysSown'], ficha['plant']['sowingDate']), ([], None, None))
        [anterior] = ficha['pastCycles']
        self.assertEqual((anterior['number'], anterior['reason'], anterior['note']), (1, 'no_germino', 'Nunca brotó.\nLo intento otra vez.'))
        self.assertEqual([e['stage'] for e in anterior['stages']], ['sin_sembrar', 'germinacion'])
        self.assertEqual([c['type'] for c in anterior['care']], ['germinacion'], 'los cuidados de otra planta no se mezclan')
        self.assertEqual(self.ficha(huerto_id, 2)['care'][0]['type'], 'sustrato', 'las otras plantas no cambian')

        # Un ciclo más: el historial sigue creciendo y los anteriores salen del más reciente al más antiguo.
        self.post(ruta, {'stage': 'germinacion'})
        self.assertEqual(self.terminar(huerto_id, reason='otro').status_code, 200)
        self.assertEqual([c['number'] for c in self.ficha(huerto_id)['pastCycles']], [2, 1])
        self.assertEqual(PlantaCiclo.objects.filter(planta=planta).count(), 3)

    def test_terminar_desde_sin_sembrar_tambien_abre_la_linea_de_vida(self):
        huerto_id = self.huerto_vinculado()
        self.assertEqual(self.terminar(huerto_id, reason='otro').status_code, 200)
        self.assertEqual([e['stage'] for e in self.ficha(huerto_id)['stages']], ['sin_sembrar'])

    def test_solo_el_dueno_y_datos_validos(self):
        huerto_id = self.huerto_vinculado()
        self.crear_huerto(cliente=self.cliente(self.otra))         # la otra cuenta tiene su propio huerto
        self.assertEqual(self.terminar(huerto_id, cliente=self.cliente(self.otra)).status_code, 404)
        self.assertEqual(self.terminar(huerto_id, cliente=self.cliente()).status_code, 401)
        for datos, codigo in (({'reason': 'aburrida'}, 'motivo-no-valido'), ({'reason': None}, 'motivo-no-valido'),
                              ({'note': 'a\x07b'}, 'caracteres-no-validos'), ({'note': 'x' * 501}, 'largo-no-valido')):
            with self.subTest(datos=datos):
                respuesta = self.terminar(huerto_id, **datos)
                self.assertEqual((respuesta.status_code, respuesta.json()['code']), (400, codigo))
        self.assertEqual(self.terminar(huerto_id, numero=4).status_code, 404)
        self.assertEqual(len(self.ciclos(huerto_id)), 1)

    def test_la_base_exige_al_dueno_y_no_deja_cambiar_ni_borrar(self):
        huerto_id = self.huerto_vinculado()
        planta = self.planta(huerto_id)
        for actor in (None, self.otra.pk):
            with self.subTest(actor=actor), self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("SELECT set_config('chilito.actor_id', %s, true)", [str(actor or '')])
                cursor.execute("SELECT chilito_terminar_ciclo(%s, 'otro', '')", [planta.pk])
        self.assertEqual(self.terminar(huerto_id).status_code, 200)
        uno, dos = self.ciclos(huerto_id)
        for intento in (lambda: PlantaCiclo.objects.filter(pk=uno.pk).update(motivo='otro'),
                        lambda: PlantaCiclo.objects.filter(pk=uno.pk).delete(),
                        lambda: PlantaCiclo.objects.filter(pk=dos.pk).update(nota='abierto'),
                        lambda: PlantaCiclo.objects.create(planta=planta, numero=5, inicio=timezone.now())):
            with self.assertRaises(DatabaseError), transaction.atomic():
                intento()
        with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT set_config('chilito.actor_id', %s, true)", [str(self.dueña.pk)])
            cursor.execute("SELECT chilito_terminar_ciclo(%s, 'se_aburrio', '')", [planta.pk])

    def test_un_cuidado_no_se_fecha_antes_del_ciclo_actual(self):
        huerto_id = self.huerto_vinculado()
        ayer = (timezone.now() - timedelta(days=1)).isoformat()
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/cuidados', {'type': 'sustrato', 'plant': 1, 'doneAt': ayer}).status_code, 200,
                         'en el ciclo 1 se admite (abarca lo anterior)')
        self.assertEqual(self.terminar(huerto_id).status_code, 200)
        respuesta = self.post(f'/api/huertos/{huerto_id}/cuidados', {'type': 'sustrato', 'plant': 1, 'doneAt': ayer})
        self.assertEqual((respuesta.status_code, respuesta.json()['code']), (409, 'cuidado-ciclo-anterior'))
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/cuidados', {'type': 'sustrato', 'plant': 2, 'doneAt': ayer}).status_code, 200,
                         'las otras plantas siguen en su ciclo 1')
        self.assertEqual(self.post(f'/api/huertos/{huerto_id}/cuidados', {'type': 'sustrato', 'plant': 1}).status_code, 200)


class Recomendaciones(BaseCiclos):
    def setUp(self):
        super().setUp()
        self.huerto_id = self.huerto_con_equipo()

    def etapa(self, etapa, dias, numero=1):
        Planta.objects.filter(huerto_id=self.huerto_id, numero=numero).update(etapa=etapa, etapa_desde=timezone.localdate() - timedelta(days=dias))

    def abrir_mi_huerto(self):
        """Abrir «Mi huerto» y que pase la tarea periódica. Desde B-1 el GET ya no revisa nada: lo hace la tarea."""
        self.assertEqual(self.client.get(f'/api/huertos/{self.huerto_id}').status_code, 200)
        with connection.cursor() as cursor:
            cursor.execute('SELECT chilito_revisar_recomendaciones()')

    def test_abrir_mi_huerto_no_escribe(self):
        """B-1: un GET no crea avisos aunque haya una recomendación pendiente; la crea la tarea periódica."""
        self.etapa('germinacion', 30)
        for ruta in (f'/api/huertos/{self.huerto_id}', f'/api/huertos/{self.huerto_id}/plantas/1'):
            self.assertEqual(self.client.get(ruta).status_code, 200)
        self.assertFalse(self.recomendaciones().exists(), 'el GET no escribe')
        with connection.cursor() as cursor:
            cursor.execute('SELECT chilito_revisar_recomendaciones()')
        self.assertEqual(self.recomendaciones().count(), 1)

    def test_germinacion_de_mas_de_21_dias_una_vez_por_ciclo(self):
        self.etapa('germinacion', 21)
        self.abrir_mi_huerto()
        self.assertFalse(self.recomendaciones().exists(), '21 días aún no')
        self.etapa('germinacion', 22)
        self.abrir_mi_huerto()
        self.abrir_mi_huerto()
        [aviso] = self.recomendaciones()
        self.assertEqual((aviso.titulo, aviso.texto, aviso.enlace, aviso.severidad),
                         ('Planta 1 lleva más de 21 días en germinación', 'Tu semilla aún no germina. Si no brota pronto, considera volver a sembrar.',
                          '#huerto/plantas/1', 'advertencia'))
        enlace = self.client.get('/api/avisos').json()['items'][0]['link']
        self.assertEqual(enlace, f'#huerto/plantas/1?h={self.huerto_id}', 'el aviso lleva a la ficha de la planta')
        # Tarea periódica: tampoco repite.
        with connection.cursor() as cursor:
            cursor.execute('SELECT chilito_revisar_recomendaciones()')
            self.assertEqual(cursor.fetchone()[0], 0)
        # Ciclo nuevo: la misma situación se puede volver a avisar.
        self.assertEqual(self.terminar(self.huerto_id).status_code, 200)
        self.etapa('germinacion', 30)
        with connection.cursor() as cursor:
            cursor.execute('SELECT chilito_revisar_recomendaciones()')
            self.assertEqual(cursor.fetchone()[0], 1)
        self.assertEqual(self.recomendaciones('germinación').count(), 2)

    def test_sustrato_saturado_12_horas(self):
        self.etapa('crecimiento', 5)
        for minutos in (13 * 60, 8 * 60, 1):
            medir(self.huerto_id, minutos, humedad=89)           # planta 1: 90 %, planta 2: 91 %, planta 3: 92 %
        self.assertEqual(self.recomendaciones().count(), 1, 'solo la planta 1 está sembrada')
        aviso = self.recomendaciones().get()
        self.assertEqual((aviso.titulo, aviso.origen), ('Riesgo de pudrición de raíz en Planta 1', 'sistema'))
        self.assertIn('pudrir las raíces', aviso.texto)
        medir(self.huerto_id, 0, humedad=95)
        self.assertEqual(self.recomendaciones().count(), 1, 'no se repite en el mismo ciclo')

    def test_sustrato_alto_pero_menos_de_12_horas_o_con_una_baja(self):
        self.etapa('crecimiento', 5)
        for minutos, humedad in ((13 * 60, 89), (6 * 60, 80), (1, 89)):   # la baja corta la racha
            medir(self.huerto_id, minutos, humedad=humedad)
        medir(self.huerto_id, 0, humedad=97)
        self.assertFalse(self.recomendaciones().exists())

    def riego(self, horas):
        Actuacion.objects.create(dispositivo=Dispositivo.objects.get(huerto_id=self.huerto_id), huerto_id=self.huerto_id, actuador='bomba',
                                 planta_numero=1, accion='encendido', duracion_s=8, origen='automatico',
                                 ocurrido_en=timezone.now() - timedelta(hours=horas))

    def secas(self):
        """Una lectura «Seca» a mediodía de antier y de ayer (Mérida) y otra ahora."""
        hoy = timezone.now().astimezone(MERIDA)
        for dias in (2, 1):
            momento = datetime.combine(hoy.date() - timedelta(days=dias), time(12), MERIDA)
            medir(self.huerto_id, (timezone.now() - momento).total_seconds() / 60, humedad=20)
        medir(self.huerto_id, 0, humedad=20)

    def test_seca_tres_dias_a_pesar_de_los_riegos(self):
        self.etapa('floracion', 30)
        self.riego(30)
        self.riego(5)
        self.secas()
        aviso = self.recomendaciones().get()
        self.assertEqual(aviso.titulo, 'Planta 1 sigue seca a pesar de los riegos')
        self.assertIn('Revisa si sigue viva', aviso.texto)
        self.assertIn('termina su ciclo', aviso.texto)

    def test_seca_sin_riegos_suficientes_no_avisa(self):
        self.etapa('floracion', 30)
        self.riego(5)
        self.secas()
        self.assertFalse(self.recomendaciones().exists())

    def test_sin_sembrar_no_recibe_recomendaciones(self):
        for minutos in (13 * 60, 1):
            medir(self.huerto_id, minutos, humedad=96)
        self.abrir_mi_huerto()
        self.assertFalse(self.recomendaciones().exists())

    def test_las_lecturas_no_se_borran_al_terminar_el_ciclo(self):
        medir(self.huerto_id, 10)
        lecturas = (Medicion.objects.count(), MedicionPlanta.objects.count())
        self.assertEqual(self.terminar(self.huerto_id).status_code, 200)
        self.assertEqual((Medicion.objects.count(), MedicionPlanta.objects.count()), lecturas)


class GuiasDeCiclo(TestCase):
    @classmethod
    def setUpTestData(cls):
        publicar_textos()

    def test_dos_guias_nuevas_publicadas(self):
        guias = {g.clave: g for g in GuiaCuidado.objects.filter(clave__in=('ciclo-habanero-fin', 'planta-muriendo-senales'))}
        self.assertEqual(set(guias), {'ciclo-habanero-fin', 'planta-muriendo-senales'})
        self.assertEqual(guias['ciclo-habanero-fin'].pregunta, '¿Cuándo termina el ciclo de mi habanero?')
        self.assertEqual(guias['planta-muriendo-senales'].pregunta, 'Señales de que mi planta está muriendo')
        self.assertTrue(all(g.estado == 'publicada' for g in guias.values()))
        self.assertIn('perenne', guias['ciclo-habanero-fin'].respuesta)
        self.assertIn('lo terminas tú', guias['ciclo-habanero-fin'].respuesta)
        cliente = AyudasHuerto.cliente(None, cuenta('guias-ciclo@example.test'))
        claves = [g['key'] for g in cliente.get('/api/guias').json()['guides']]
        self.assertIn('ciclo-habanero-fin', claves)
        self.assertIn('planta-muriendo-senales', claves)
