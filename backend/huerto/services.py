"""Huertos, plantas, órdenes y vinculación del equipo. Todo recurso se busca por la cuenta que lo pide:
un huerto ajeno o archivado es igual de inexistente que uno que no está (404)."""
import hashlib
import hmac
import re
import secrets
from functools import cache
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import BooleanField, Case, CharField, F, OuterRef, Q, SmallIntegerField, Subquery, Value, When
from django.http import Http404
from django.utils import timezone

from datos import services as s
from datos.models import (Actuacion, Autodiagnostico, CodigoVinculacion, Comando, Cuidado, CuidadoRevision, DepositoDeteccion,
                          Dispositivo, DispositivoEvento, IaResumen, Medicion, MedicionPlanta, ResumenHoraHuerto, ResumenHoraPlanta)
from datos.paginacion import paginar
from web import validacion as v
from web.respuestas import ReglaDeNegocio

from .models import Huerto, Planta, PlantaCiclo, PlantaEtapa

ALFABETO_CODIGO = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
LARGO_CODIGO = 8
ETAPAS = ('sin_sembrar', 'germinacion', 'plantula', 'crecimiento', 'floracion', 'fructificacion')
TIPOS_COMANDO = ('regar', 'lampara_apagar', 'lampara_automatico', 'autodiagnostico')
DURACIONES_RIEGO = (5, 8, 10, 15, 20)
TIPOS_CUIDADO = ('rellenar_deposito', 'sustrato', 'germinacion', 'cosecha', 'inspeccion')
TIPOS_CUIDADO_DE_PLANTA = ('sustrato', 'germinacion', 'cosecha')
RANGOS = {'1h': timedelta(hours=1), '24h': timedelta(hours=24), '7d': timedelta(days=7), '30d': timedelta(days=30)}
DIAS_RESUMEN_IA = 30
MAXIMO_PUNTOS = 1500
ZONA_MERIDA = ZoneInfo('America/Merida')
TIPOS_BITACORA = ('ordenes', 'actuaciones', 'eventos')


@cache
def _hash_ficticio():
    """Hash de una credencial inexistente: un identificador desconocido tarda lo mismo que uno conocido."""
    return make_password('sin-equipo')


def _numero(valor):
    return None if valor is None else float(valor)


def _fecha(valor):
    return valor.isoformat() if valor else None


def _equipo_de(huerto):
    return Dispositivo.objects.filter(huerto_id=huerto.pk).first()


def _equipo_dto(equipo):
    if equipo is None:
        return None
    ultima = Medicion.objects.filter(dispositivo=equipo).order_by('-medida_en').values_list('medida_en', flat=True).first()
    return {'id': str(equipo.pk), 'identifier': equipo.identificador, 'connection': equipo.conexion,
            'lastConnectionAt': _fecha(equipo.ultima_conexion_en), 'linkedAt': _fecha(equipo.vinculado_en),
            'firmware': equipo.firmware_version or None, 'lastReadingAt': _fecha(ultima)}


def _huerto_dto(huerto, equipo):
    return {'id': str(huerto.pk), 'name': huerto.nombre, 'createdAt': _fecha(huerto.creado_en), 'device': _equipo_dto(equipo)}


def _nombre_huerto(nombre):
    """Nombre de cosa: letras, números, espacios y guion (1 a 60). Al crear se puede omitir (la base pone «Mi huerto»),
    pero si llega, no puede estar vacío."""
    return None if nombre is None else v.nombre_cosa(nombre, 'name', maximo=60)


def listar(actor):
    huertos = Huerto.objects.filter(propietario_id=actor.pk, estado='activo').order_by('id')
    return {'status': 'ready', 'items': [_huerto_dto(huerto, _equipo_de(huerto)) for huerto in huertos]}


@transaction.atomic
def crear(actor, nombre):
    nombre = _nombre_huerto(nombre)
    huerto = Huerto.objects.create(propietario_id=actor.pk, **({'nombre': nombre} if nombre else {}))
    huerto.refresh_from_db()
    s.auditar(actor, 'crear_huerto', entidad='huerto', entidad_id=huerto.pk)
    return {'status': 'accepted', 'garden': _huerto_dto(huerto, None)}


@transaction.atomic
def renombrar(actor, huerto_id, nombre):
    huerto = s.huerto_propio(actor, huerto_id, bloquear=True)
    huerto.nombre = v.nombre_cosa(nombre, 'name', maximo=60)
    huerto.save(update_fields=['nombre'])
    s.auditar(actor, 'renombrar_huerto', entidad='huerto', entidad_id=huerto.pk)
    return {'status': 'accepted', 'garden': _huerto_dto(huerto, _equipo_de(huerto))}


@transaction.atomic
def archivar(actor, huerto_id):
    huerto = s.huerto_propio(actor, huerto_id, bloquear=True)
    huerto.estado = 'archivado'
    huerto.save(update_fields=['estado'])
    s.auditar(actor, 'archivar_huerto', entidad='huerto', entidad_id=huerto.pk)
    return {'status': 'accepted'}


# ── Lectura de «Mi huerto» ──

def _planta_dto(planta, lectura):
    hoy = datetime.now(ZONA_MERIDA).date()
    return {'number': planta.numero, 'name': planta.nombre, 'stage': planta.etapa, 'stageSince': _fecha(planta.etapa_desde),
            'sowingDate': _fecha(planta.fecha_siembra),
            'daysSown': (hoy - planta.fecha_siembra).days if planta.fecha_siembra else None,
            'moisture': _numero(lectura.humedad_sustrato_pct) if lectura else None,
            'measuredAt': _fecha(lectura.medicion.medida_en) if lectura else None}


def _ultima_lectura_planta(huerto, numero):
    return (MedicionPlanta.objects.filter(medicion__huerto_id=huerto.pk, planta_numero=numero)
            .select_related('medicion').order_by('-medicion__medida_en').first())


def _metricas(huerto):
    medicion = Medicion.objects.filter(huerto_id=huerto.pk).order_by('-medida_en').first()
    if medicion is None:
        return None
    return {'measuredAt': _fecha(medicion.medida_en), 'temperature': _numero(medicion.temperatura_c),
            'airHumidity': _numero(medicion.humedad_aire_pct), 'light': _numero(medicion.luz_lux),
            'tankHasWater': medicion.deposito_con_agua}


def _lampara(huerto):
    actuacion = Actuacion.objects.filter(huerto_id=huerto.pk, actuador='lampara').order_by('-ocurrido_en').first()
    orden = (Comando.objects.filter(huerto_id=huerto.pk, tipo__in=('lampara_apagar', 'lampara_automatico'), estado='confirmado')
             .order_by('-creado_en').first())
    return {'state': {'encendido': 'on', 'apagado': 'off'}[actuacion.accion] if actuacion else None,
            'stateAt': _fecha(actuacion.ocurrido_en) if actuacion else None,
            'mode': 'manual-off' if orden and orden.tipo == 'lampara_apagar' else 'automatic'}


def _resumen_ia_dto(resumen):
    return {'content': resumen.contenido, 'generatedAt': _fecha(resumen.generado_en), 'dataUntil': _fecha(resumen.datos_hasta)}


def detalle(actor, huerto_id):
    # B-1: un GET no escribe. Las recomendaciones salen con cada lectura del equipo (trigger de web.0007) y con la
    # tarea periódica (`manage.py tareas_periodicas` o `revisar_recomendaciones`).
    huerto = s.huerto_propio(actor, huerto_id)
    equipo = _equipo_de(huerto)
    plantas = Planta.objects.filter(huerto_id=huerto.pk).order_by('numero')
    resumen = IaResumen.objects.filter(huerto_id=huerto.pk).order_by('-generado_en').first()
    return {'status': 'ready', 'garden': _huerto_dto(huerto, equipo),
            'plants': [_planta_dto(planta, _ultima_lectura_planta(huerto, planta.numero)) for planta in plantas],
            'metrics': _metricas(huerto) if equipo else None, 'lamp': _lampara(huerto) if equipo else None,
            'summary': _resumen_ia_dto(resumen) if resumen else None, 'tank': _deposito(huerto, equipo)[0]}


def resumenes_ia(actor, huerto_id, pagina):
    huerto = s.huerto_propio(actor, huerto_id)
    desde = timezone.now() - timedelta(days=DIAS_RESUMEN_IA)
    filas = IaResumen.objects.filter(huerto_id=huerto.pk, generado_en__gte=desde).order_by('-generado_en')
    return {'status': 'ready', **paginar(filas, pagina, _resumen_ia_dto)}


# ── Plantas ──

def _planta(huerto, numero, *, bloquear=False):
    consulta = Planta.objects.select_for_update() if bloquear else Planta.objects
    planta = consulta.filter(huerto_id=huerto.pk, numero=numero).first() if type(numero) is int else None
    if planta is None:
        raise Http404
    return planta


def _serie(huerto, numero, rango):
    ahora = timezone.now()
    desde = ahora - RANGOS[rango]
    if rango in ('1h', '24h'):
        filas = list(MedicionPlanta.objects.filter(medicion__huerto_id=huerto.pk, planta_numero=numero, medicion__medida_en__gte=desde)
                     .select_related('medicion').order_by('-medicion__medida_en')[:MAXIMO_PUNTOS])
        return [{'at': _fecha(fila.medicion.medida_en), 'value': _numero(fila.humedad_sustrato_pct)} for fila in reversed(filas)]
    filas = list(ResumenHoraPlanta.objects.filter(huerto_id=huerto.pk, planta_numero=numero, hora__gte=desde)
                 .order_by('-hora')[:MAXIMO_PUNTOS])
    return [{'at': _fecha(fila.hora), 'value': _numero(fila.humedad_prom)} for fila in reversed(filas)]


def _cuidados_vigentes():
    """Cuidados con el tipo, la planta y los chiles vigentes: una corrección reemplaza los tres a la vez."""
    ultima = CuidadoRevision.objects.filter(cuidado_id=OuterRef('pk')).order_by('-numero')
    vigente = lambda original, corregido, campo: Case(When(rev_tipo='correccion', then=F(corregido)), default=F(original), output_field=campo)
    return (Cuidado.objects
            .annotate(rev_tipo=Subquery(ultima.values('tipo')[:1]), rev_tipo_c=Subquery(ultima.values('tipo_corregido')[:1]),
                      rev_planta=Subquery(ultima.values('planta_corregida')[:1]), rev_chiles=Subquery(ultima.values('chiles_corregidos')[:1]),
                      rev_motivo=Subquery(ultima.values('motivo')[:1]), rev_numero=Subquery(ultima.values('numero')[:1]))
            .annotate(tipo_vigente=vigente('tipo', 'rev_tipo_c', CharField()), planta_vigente=vigente('planta_numero', 'rev_planta', SmallIntegerField()),
                      chiles_vigentes=vigente('chiles_cosechados', 'rev_chiles', SmallIntegerField()),
                      por_dueno=Case(When(registrado_por_id=F('huerto__propietario_id'), then=Value(True)), default=Value(False),
                                     output_field=BooleanField())))


def _cuidado_dto(cuidado):
    # Recarga del equipo: «confirmed» si alguien la confirmó (las de la 0004 no tienen autor); «byOwner», si fue el dueño.
    return {'id': str(cuidado.pk), 'type': cuidado.tipo_vigente, 'plant': cuidado.planta_vigente, 'chiles': cuidado.chiles_vigentes, 'origin': cuidado.origen,
            'confirmed': cuidado.origen == 'equipo' and cuidado.registrado_por_id is not None, 'byOwner': cuidado.por_dueno,
            'doneAt': _fecha(cuidado.realizado_en), 'voided': cuidado.rev_tipo == 'anulacion', 'corrected': cuidado.rev_tipo == 'correccion',
            'reason': cuidado.rev_motivo if cuidado.rev_tipo else None}


def _ultimo_riego(huerto, numero):
    riego = (Actuacion.objects.filter(huerto_id=huerto.pk, actuador='bomba', planta_numero=numero, accion='encendido')
             .order_by('-ocurrido_en').first())
    return {'at': _fecha(riego.ocurrido_en), 'origin': riego.origen, 'duration': riego.duracion_s} if riego else None


# ── Ciclos de la planta ──
# Siempre hay un ciclo abierto (web.0007). La línea de vida y los cuidados no se borran al terminar un ciclo: cada etapa
# guarda su ciclo (lo fija la base) y los cuidados se reparten por fecha: lo anterior al fin de un ciclo es de ese ciclo.
MOTIVOS_FIN_CICLO = ('cosecha_terminada', 'planta_murio', 'no_germino', 'pudricion_plaga', 'otro')
MAXIMO_NOTA_CICLO = 500
CUIDADOS_POR_CICLO = 50


def _ciclos(planta):
    return list(PlantaCiclo.objects.filter(planta_id=planta.pk).order_by('numero'))


def _del_ciclo(filas, campo, ciclos, indice):
    """Las filas (ya ordenadas) cuyo `campo` cae en el ciclo `indice`: desde el fin del anterior y antes de su propio fin."""
    desde = ciclos[indice - 1].fin if indice else None
    hasta = ciclos[indice].fin
    return [fila for fila in filas if (desde is None or getattr(fila, campo) >= desde) and (hasta is None or getattr(fila, campo) < hasta)]


def _etapa_dto(fila):
    return {'stage': fila.etapa, 'since': _fecha(fila.desde)}


def _ciclo_dto(ciclo):
    return {'number': ciclo.numero, 'startedAt': _fecha(ciclo.inicio), 'endedAt': _fecha(ciclo.fin), 'reason': ciclo.motivo,
            'note': ciclo.nota or None}


def detalle_planta(actor, huerto_id, numero, rango):
    if rango not in RANGOS:
        raise ValidationError('Rango no válido')
    huerto = s.huerto_propio(actor, huerto_id)
    planta = _planta(huerto, numero)
    ciclos = _ciclos(planta)
    etapas = list(PlantaEtapa.objects.filter(planta_id=planta.pk).order_by('desde', 'id'))
    cuidados = list(_cuidados_vigentes().filter(huerto_id=huerto.pk, planta_vigente=numero).order_by('-realizado_en'))
    actual = len(ciclos) - 1
    etapas_de = lambda i: [_etapa_dto(f) for f in etapas if f.ciclo_id == ciclos[i].pk]   # noqa: E731
    anteriores = [{**_ciclo_dto(ciclos[i]), 'stages': etapas_de(i),
                   'care': [_cuidado_dto(c) for c in _del_ciclo(cuidados, 'realizado_en', ciclos, i)[:CUIDADOS_POR_CICLO]]}
                  for i in range(actual - 1, -1, -1)]
    return {'status': 'ready', 'plant': _planta_dto(planta, _ultima_lectura_planta(huerto, numero)),
            'cycle': _ciclo_dto(ciclos[actual]), 'pastCycles': anteriores,
            'stages': etapas_de(actual),
            'series': _serie(huerto, numero, rango), 'range': rango,
            'care': [_cuidado_dto(c) for c in _del_ciclo(cuidados, 'realizado_en', ciclos, actual)[:10]],
            'lastWatering': _ultimo_riego(huerto, numero), 'hasDevice': _equipo_de(huerto) is not None}


@transaction.atomic
def terminar_ciclo(actor, huerto_id, numero, motivo, nota):
    """Solo el dueño: cierra el ciclo con su motivo y abre el siguiente (la base lo hace en chilito_terminar_ciclo).
    La planta vuelve a «sin_sembrar» sin fecha de siembra y conserva su nombre; no se borra nada."""
    huerto = s.huerto_propio(actor, huerto_id)
    planta = _planta(huerto, numero, bloquear=True)
    if motivo not in MOTIVOS_FIN_CICLO:
        raise v.CampoInvalido('reason', 'motivo-no-valido', 'Elige por qué termina el ciclo.')
    nota = v.texto_libre(nota, 'note', maximo=MAXIMO_NOTA_CICLO, multilinea=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT chilito_terminar_ciclo(%s, %s, %s)', [planta.pk, motivo, nota])
    ciclos = _ciclos(planta)
    s.auditar(actor, 'terminar_ciclo', entidad='planta', entidad_id=planta.pk, detalle={'ciclo': ciclos[-2].numero, 'motivo': motivo})
    planta.refresh_from_db()
    return {'status': 'accepted', 'plant': _planta_dto(planta, _ultima_lectura_planta(huerto, numero)),
            'cycle': _ciclo_dto(ciclos[-1]), 'ended': _ciclo_dto(ciclos[-2])}


def _nombre_planta(nombre):
    """Nombre de cosa (1 a 40): «Planta 1», el de fábrica, sigue siendo válido."""
    return v.nombre_cosa(nombre, 'name', maximo=40)


def _fecha_siembra(valor):
    if valor is None:
        return None
    siembra = date.fromisoformat(valor) if isinstance(valor, str) and len(valor) == 10 else None
    if siembra is None or siembra > datetime.now(ZONA_MERIDA).date():
        raise ValidationError('Fecha no válida')
    return siembra


@transaction.atomic
def editar_planta(actor, huerto_id, numero, datos):
    huerto = s.huerto_propio(actor, huerto_id)
    planta = _planta(huerto, numero, bloquear=True)
    cambios = {}
    if 'name' in datos:
        cambios['nombre'] = _nombre_planta(datos['name'])
    if 'sowingDate' in datos:
        cambios['fecha_siembra'] = _fecha_siembra(datos['sowingDate'])
    if 'stage' in datos:
        if datos['stage'] not in ETAPAS:
            raise ValidationError('Etapa no válida')
        cambios['etapa'] = datos['stage']
    if not cambios:
        raise ValidationError('Sin cambios')
    for campo, valor in cambios.items():
        setattr(planta, campo, valor)
    planta.save(update_fields=list(cambios))
    s.auditar(actor, 'editar_planta', entidad='planta', entidad_id=planta.pk, detalle={'campos': sorted(cambios)})
    planta.refresh_from_db()
    return {'status': 'accepted', 'plant': _planta_dto(planta, _ultima_lectura_planta(huerto, numero))}


# ── Órdenes y cuidados ──

def _comando_dto(comando, con_diagnostico=False):
    dto = {'id': str(comando.pk), 'type': comando.tipo, 'plant': comando.planta_numero, 'duration': comando.duracion_s,
           'origin': comando.origen, 'state': comando.estado, 'createdAt': _fecha(comando.creado_en), 'sentAt': _fecha(comando.enviado_en),
           'resolvedAt': _fecha(comando.resuelto_en), 'error': comando.detalle_error or None}
    if con_diagnostico and comando.tipo == 'autodiagnostico':
        dto['diagnosticId'] = str(Autodiagnostico.objects.filter(comando_id=comando.pk).values_list('pk', flat=True).first())
    return dto


@transaction.atomic
def crear_comando(actor, huerto_id, tipo, planta, duracion):
    huerto = s.huerto_propio(actor, huerto_id)
    if tipo not in TIPOS_COMANDO:
        raise ValidationError('Orden no válida')
    if tipo == 'regar':
        v.entero(planta, 'plant', 1, 3)
        if duracion not in DURACIONES_RIEGO or type(duracion) is not int:
            raise ValidationError('Duración no válida')
    elif planta is not None or duracion is not None:
        raise ValidationError('Datos que sobran')
    equipo = _equipo_de(huerto)
    if equipo is None:
        raise ValidationError('El huerto no tiene equipo')
    comando = Comando.objects.create(huerto=huerto, dispositivo=equipo, tipo=tipo, planta_numero=planta, duracion_s=duracion,
                                     origen='usuario', solicitado_por_id=actor.pk)
    comando.refresh_from_db()
    s.auditar(actor, 'crear_comando', entidad='comando', entidad_id=comando.pk, detalle={'tipo': tipo})
    return {'status': 'accepted', 'command': _comando_dto(comando, con_diagnostico=True)}


def estado_comando(actor, comando_id):
    # B-10: como `huerto_propio`, solo de un huerto activo de la cuenta; uno archivado responde lo mismo que uno inexistente.
    comando = Comando.objects.filter(pk=comando_id, solicitado_por_id=actor.pk, origen='usuario',
                                     huerto__propietario_id=actor.pk, huerto__estado='activo').first()
    if comando is None:
        raise Http404
    return {'status': 'ready', 'command': _comando_dto(comando, con_diagnostico=True)}


def _momento_cuidado(valor):
    """Fecha real del cuidado (ISO con zona): no futura y de hasta 7 días atrás; la base vuelve a exigirlo."""
    if valor is None:
        return None
    if not isinstance(valor, str) or len(valor) > 40:
        raise ValidationError('Fecha no válida')
    momento = datetime.fromisoformat(valor)
    ahora = timezone.now()
    if momento.tzinfo is None or momento > ahora + timedelta(minutes=5) or momento < ahora - timedelta(days=7):
        raise ValidationError('Fecha no válida')
    return momento


def _validar_cuidado(tipo, planta, chiles):
    if tipo not in TIPOS_CUIDADO:
        raise ValidationError('Cuidado no válido')
    if tipo == 'rellenar_deposito' and planta is not None:
        raise ValidationError('Datos que sobran')
    if tipo in TIPOS_CUIDADO_DE_PLANTA or (tipo == 'inspeccion' and planta is not None):
        v.entero(planta, 'plant', 1, 3)
    if chiles is not None:
        if tipo != 'cosecha':
            raise ValidationError('Datos que sobran')
        v.entero(chiles, 'chiles', 0, 999)


def _crear_cuidado(actor, huerto, tipo, planta, chiles, realizado_en):
    _validar_cuidado(tipo, planta, chiles)
    momento = _momento_cuidado(realizado_en)
    if tipo == 'rellenar_deposito':
        _exigir_recarga_permitida(huerto, momento or timezone.now())
    cuidado = Cuidado.objects.create(huerto=huerto, tipo=tipo, planta_numero=planta, chiles_cosechados=chiles,
                                     registrado_por_id=actor.pk, **({'realizado_en': momento} if momento else {}))
    s.auditar(actor, 'registrar_cuidado', entidad='cuidado', entidad_id=cuidado.pk, detalle={'tipo': tipo})
    return cuidado


@transaction.atomic
def registrar_cuidado(actor, huerto_id, tipo, planta, chiles, realizado_en=None):
    huerto = s.huerto_propio(actor, huerto_id)
    cuidado = _crear_cuidado(actor, huerto, tipo, planta, chiles, realizado_en)
    return {'status': 'accepted', 'care': _cuidado_dto(_cuidados_vigentes().get(pk=cuidado.pk))}


def _dia(valor):
    if valor is None:
        return None
    if not isinstance(valor, str) or len(valor) != 10:
        raise ValidationError('Fecha no válida')
    return date.fromisoformat(valor)


def _filtrar_cuidados(consulta, planta, tipo, desde, hasta):
    if planta not in (None, 'huerto', '1', '2', '3') or (tipo is not None and tipo not in TIPOS_CUIDADO):
        raise ValidationError('Filtro no válido')
    desde, hasta = _dia(desde), _dia(hasta)
    if desde and hasta and desde > hasta:
        raise ValidationError('Rango de fechas no válido')
    if tipo:
        consulta = consulta.filter(tipo_vigente=tipo)
    if planta:
        consulta = consulta.filter(planta_vigente__isnull=True) if planta == 'huerto' else consulta.filter(planta_vigente=int(planta))
    if desde:
        consulta = consulta.filter(realizado_en__gte=datetime.combine(desde, time.min, ZONA_MERIDA))
    if hasta:
        consulta = consulta.filter(realizado_en__lt=datetime.combine(hasta + timedelta(days=1), time.min, ZONA_MERIDA))
    return consulta


# Tipos de las fichas «Último…» de Mantenimiento.
TIPOS_RESUMEN = ('rellenar_deposito', 'cosecha', 'sustrato', 'inspeccion')


def _ultimos_cuidados(vigentes):
    """El último cuidado no anulado de cada tipo de las fichas, sin depender de la página del historial."""
    validos = vigentes.filter(Q(rev_tipo__isnull=True) | ~Q(rev_tipo='anulacion')).order_by('-realizado_en', '-registrado_en')
    ultimos = {}
    for tipo in TIPOS_RESUMEN:
        cuidado = validos.filter(tipo_vigente=tipo).first()
        ultimos[tipo] = _cuidado_dto(cuidado) if cuidado else None
    return ultimos


def cuidados(actor, huerto_id, planta, tipo, desde, hasta, pagina):
    huerto = s.huerto_propio(actor, huerto_id)
    vigentes = _cuidados_vigentes().filter(huerto_id=huerto.pk)
    consulta = _filtrar_cuidados(vigentes, planta, tipo, desde, hasta)
    respuesta = {'status': 'ready', **paginar(consulta.order_by('-realizado_en', '-registrado_en'), pagina, _cuidado_dto)}
    # El resumen solo acompaña al historial sin filtros, página 1: es lo que pinta las fichas «Último…».
    if pagina == 1 and not any((planta, tipo, desde, hasta)):
        respuesta['latest'] = _ultimos_cuidados(vigentes)
    return respuesta


# ── Depósito: estado del flotador, reglas de la recarga manual y duración de cada carga ──
# Las mismas reglas las impone la base (web.0004, web.0005 y web.0006): aquí se calculan para mostrarlas y dar un mensaje claro
# antes de escribir. Una recarga que detecta el flotador queda pendiente (deposito_deteccion) hasta que el dueño la confirma:
# solo entonces hay cuidado. Con una pendiente, registrar la recarga a mano es confirmarla, así que no se aplican las reglas
# manuales. Con equipo, la recarga manual exige nivel bajo y cuenta una sola vez por cada nivel bajo (web.0006).
ESPERA_SIN_EQUIPO = timedelta(hours=12)
CARGA_MINIMA = timedelta(hours=1)        # menos que esto es rebote del flotador
CARGAS_PARA_PROMEDIO = 5
CARGAS_EN_HISTORIAL = 10


def _hora_merida(momento):
    return momento.astimezone(ZONA_MERIDA).strftime('%d/%m/%Y a las %H:%M')


def _recargas(huerto):
    """Recargas vigentes (no anuladas y con tipo vigente rellenar_deposito), de la más antigua a la más reciente."""
    return list(_cuidados_vigentes().filter(huerto_id=huerto.pk, tipo_vigente='rellenar_deposito')
                .filter(Q(rev_tipo__isnull=True) | Q(rev_tipo='correccion'))
                .order_by('realizado_en', 'registrado_en').values('realizado_en', 'registrado_en', 'origen', 'registrado_por_id'))


def _deteccion_pendiente(huerto):
    return DepositoDeteccion.objects.filter(huerto_id=huerto.pk, estado='pendiente').first()


def _lecturas_flotador(huerto):
    return Medicion.objects.filter(huerto_id=huerto.pk, deposito_con_agua__isnull=False)


def _bajo_desde(huerto):
    """Inicio del nivel bajo en curso: la primera lectura baja después de la última con agua (None si la última tiene agua)."""
    lecturas = _lecturas_flotador(huerto)
    con_agua = lecturas.filter(deposito_con_agua=True).order_by('-medida_en').values_list('medida_en', flat=True).first()
    bajas = lecturas.filter(deposito_con_agua=False)
    if con_agua is not None:
        bajas = bajas.filter(medida_en__gt=con_agua)
    return bajas.order_by('medida_en').values_list('medida_en', flat=True).first()


def _recarga_desde(recargas, desde):
    """La recarga vigente más reciente hecha desde `desde`; la de una persona también si la registró desde entonces
    (como chilito_recarga_desde)."""
    if desde is None:
        return None
    dentro = [r for r in recargas if r['realizado_en'] >= desde or (r['origen'] == 'persona' and r['registrado_en'] >= desde)]
    return max(dentro, key=lambda r: r['realizado_en']) if dentro else None


def _bloqueo_recarga(huerto, equipo, recargas, momento, pendiente=None):
    """None si se permite una recarga manual en `momento`; si no, (código, mensaje, próxima fecha permitida o None)."""
    if pendiente is not None:
        return None
    ultima = recargas[-1]['realizado_en'] if recargas else None
    if equipo is not None and _lecturas_flotador(huerto).exists():
        bajo_desde = _bajo_desde(huerto)
        if bajo_desde is None:
            if ultima is None:
                return ('deposito-con-agua', 'Tu depósito tiene agua: podrás registrar una recarga cuando el flotador marque nivel bajo.', None)
            return ('deposito-con-agua', f'Tu depósito tiene agua desde tu última recarga ({_hora_merida(ultima)}). '
                    'Podrás registrar otra cuando el flotador marque nivel bajo.', None)
        registrada = _recarga_desde(recargas, bajo_desde)
        if registrada is not None:
            return ('deposito-repetida', f'Ya registraste esta recarga ({_hora_merida(registrada["realizado_en"])}): no hace falta registrar otra.', None)
        return None
    cercanas = [r['realizado_en'] for r in recargas if abs(r['realizado_en'] - momento) < ESPERA_SIN_EQUIPO]
    if not cercanas:
        return None
    proxima = max(cercanas) + ESPERA_SIN_EQUIPO
    return ('deposito-espera', f'Ya registraste una recarga hace menos de 12 horas: podrás registrar otra a partir del {_hora_merida(proxima)}.', proxima)


def _exigir_recarga_permitida(huerto, momento):
    bloqueo = _bloqueo_recarga(huerto, _equipo_de(huerto), _recargas(huerto), momento, _deteccion_pendiente(huerto))
    if bloqueo:
        raise ReglaDeNegocio(bloqueo[0], bloqueo[1])


def _cargas(recargas, bajos):
    """Una carga va de la última recarga vigente antes de un «deposito_bajo» (y después del anterior) a ese evento.

    Devuelve (completas de la más antigua a la más reciente, sin las de menos de 1 hora; recarga de la carga abierta o None)."""
    completas, anterior = [], None
    for bajo in bajos:
        candidatas = [r for r in recargas if r['realizado_en'] < bajo and (anterior is None or r['realizado_en'] > anterior)]
        if candidatas and bajo - candidatas[-1]['realizado_en'] >= CARGA_MINIMA:
            completas.append({**candidatas[-1], 'bajo': bajo})
        anterior = bajo
    abiertas = [r for r in recargas if anterior is None or r['realizado_en'] > anterior]
    return completas, (abiertas[-1] if abiertas else None)


def _carga_dto(carga, dueno_id):
    duracion = carga['bajo'] - carga['realizado_en'] if carga.get('bajo') else None
    return {'refilledAt': _fecha(carga['realizado_en']), 'origin': carga['origen'], 'confirmed': carga['origen'] == 'equipo' and carga['registrado_por_id'] is not None,
            'byOwner': carga['registrado_por_id'] == dueno_id, 'lowAt': _fecha(carga.get('bajo')),
            'seconds': int(duracion.total_seconds()) if duracion else None}


def _fase_deposito(huerto, equipo, lectura, recargas, pendiente):
    """Qué muestra la tarjeta Depósito: con_agua | rellenar | detectada | esperando_lectura | sigue_bajo | sin_lectura | sin_equipo."""
    if equipo is None:
        return 'sin_equipo'
    if lectura is None:
        return 'sin_lectura'
    if lectura.deposito_con_agua:
        return 'detectada' if pendiente is not None and pendiente.detectada_en <= lectura.medida_en else 'con_agua'
    registrada = _recarga_desde(recargas, _bajo_desde(huerto))
    if registrada is None:
        return 'rellenar'
    # Registró la recarga en este nivel bajo: ¿llegó otra lectura (baja) después de registrarla?
    despues = max(registrada['realizado_en'], registrada['registrado_en']) if registrada['origen'] == 'persona' else registrada['realizado_en']
    return 'sigue_bajo' if lectura.medida_en > despues else 'esperando_lectura'


def _deposito(huerto, equipo):
    """(estado del depósito para la interfaz, cargas para el historial: la abierta primero y luego las completas, recientes primero)."""
    ahora = timezone.now()
    recargas = _recargas(huerto)
    ultima = recargas[-1] if recargas else None
    lectura = _lecturas_flotador(huerto).order_by('-medida_en').first() if equipo else None
    bajo_desde = None
    if lectura is not None and lectura.deposito_con_agua is False:
        evento = (DispositivoEvento.objects.filter(huerto_id=huerto.pk, tipo='deposito_bajo').order_by('-ocurrido_en')
                  .values_list('ocurrido_en', flat=True).first())
        bajo_desde = evento or lectura.medida_en
    pendiente = _deteccion_pendiente(huerto)
    bloqueo = _bloqueo_recarga(huerto, equipo, recargas, ahora, pendiente)
    fase = _fase_deposito(huerto, equipo, lectura, recargas, pendiente)
    estado = {'hasDevice': equipo is not None, 'hasWater': lectura.deposito_con_agua if lectura else None, 'lowSince': _fecha(bajo_desde),
              'state': fase,
              # La pregunta «¿Ya lo rellenaste?» solo con una detección real: pendiente y la última lectura con agua.
              'pendingRefill': {'id': str(pendiente.pk), 'detectedAt': _fecha(pendiente.detectada_en)} if fase == 'detectada' else None,
              'lastRefill': {'at': _fecha(ultima['realizado_en']), 'origin': ultima['origen'],
                             'confirmed': ultima['origen'] == 'equipo' and ultima['registrado_por_id'] is not None,
                             'byOwner': ultima['registrado_por_id'] == huerto.propietario_id} if ultima else None,
              'canRefill': bloqueo is None, 'refillBlock': bloqueo[0].removeprefix('deposito-') if bloqueo else None,
              'nextRefillAt': _fecha(bloqueo[2]) if bloqueo else None,
              'averageSeconds': None, 'averageLoads': 0, 'estimatedLowAt': None, 'completedLoads': 0, 'refillEverySeconds': None}
    if equipo is None:
        ultimas = [r['realizado_en'] for r in recargas[-CARGAS_PARA_PROMEDIO:]]
        if len(ultimas) >= 2:
            estado['refillEverySeconds'] = int((ultimas[-1] - ultimas[0]).total_seconds() / (len(ultimas) - 1))
        return estado, []
    bajos = list(DispositivoEvento.objects.filter(huerto_id=huerto.pk, tipo='deposito_bajo').order_by('ocurrido_en')
                 .values_list('ocurrido_en', flat=True))
    completas, abierta = _cargas(recargas, bajos)
    estado['completedLoads'] = len(completas)
    if completas:
        recientes = completas[-CARGAS_PARA_PROMEDIO:]
        promedio = sum(((c['bajo'] - c['realizado_en']) for c in recientes), timedelta()) / len(recientes)
        estado['averageSeconds'] = int(promedio.total_seconds())
        estado['averageLoads'] = len(recientes)
        if abierta is not None and lectura is not None and lectura.deposito_con_agua:
            estado['estimatedLowAt'] = _fecha(ultima['realizado_en'] + promedio)
    historial = ([abierta] if abierta else []) + completas[::-1]
    return estado, historial[:CARGAS_EN_HISTORIAL]


def deposito(actor, huerto_id):
    huerto = s.huerto_propio(actor, huerto_id)
    estado, cargas = _deposito(huerto, _equipo_de(huerto))
    return {'status': 'ready', 'tank': estado, 'loads': [_carga_dto(carga, huerto.propietario_id) for carga in cargas]}


def _deteccion_a_decidir(actor, huerto_id, deteccion_id):
    """La detección pendiente del huerto propio, con el huerto y la detección bloqueados (en ese orden, como la base)."""
    huerto = s.huerto_propio(actor, huerto_id, bloquear=True)
    deteccion = DepositoDeteccion.objects.select_for_update().filter(pk=deteccion_id, huerto_id=huerto.pk).first()
    if deteccion is None:
        raise Http404
    if deteccion.estado != 'pendiente':
        raise ReglaDeNegocio('deposito-resuelta', 'Esta recarga detectada ya se confirmó, se descartó o quedó sin confirmar.')
    return huerto, deteccion


@transaction.atomic
def confirmar_recarga(actor, huerto_id, deteccion_id):
    """Solo el dueño: registra la recarga, que la base convierte en la detectada (su hora, origen «equipo»)."""
    huerto, deteccion = _deteccion_a_decidir(actor, huerto_id, deteccion_id)
    cuidado = Cuidado.objects.create(huerto=huerto, tipo='rellenar_deposito', registrado_por_id=actor.pk)
    s.auditar(actor, 'confirmar_recarga', entidad='deposito_deteccion', entidad_id=deteccion.pk, detalle={'cuidado': str(cuidado.pk)})
    return {'status': 'accepted', 'care': _cuidado_dto(_cuidados_vigentes().get(pk=cuidado.pk)), 'tank': _deposito(huerto, _equipo_de(huerto))[0]}


@transaction.atomic
def descartar_recarga(actor, huerto_id, deteccion_id):
    """Solo el dueño: «No fue una recarga». No crea cuidado."""
    huerto, deteccion = _deteccion_a_decidir(actor, huerto_id, deteccion_id)
    DepositoDeteccion.objects.filter(pk=deteccion.pk, estado='pendiente').update(estado='descartada', decidida_por_id=actor.pk,
                                                                               decidida_en=timezone.now())
    s.auditar(actor, 'descartar_recarga', entidad='deposito_deteccion', entidad_id=deteccion.pk)
    return {'status': 'accepted', 'tank': _deposito(huerto, _equipo_de(huerto))[0]}


# ── Mantenimientos de todos los huertos (`gestionar_mantenimientos`) ──
CAPACIDAD_MANTENIMIENTOS = 'gestionar_mantenimientos'
ESTADOS_CUIDADO = {'vigente': None, 'corregido': 'correccion', 'anulado': 'anulacion'}
MAXIMO_BUSQUEDA = 60
MAXIMO_MOTIVO = 500


def _mantenimientos():
    return _cuidados_vigentes().select_related('huerto__propietario')


def _mantenimiento_dto(cuidado):
    return {**_cuidado_dto(cuidado), 'gardenId': str(cuidado.huerto_id), 'garden': cuidado.huerto.nombre,
            'owner': cuidado.huerto.propietario.email, 'revision': cuidado.rev_numero or 0, 'registeredAt': _fecha(cuidado.registrado_en)}


def _id_numerico(valor, campo='garden'):
    """N.º de huerto: entero positivo o solo dígitos (hasta 18)."""
    if type(valor) is int and valor > 0:
        return valor
    return int(v.entero_texto(valor, campo, maximo_digitos=18))


def _busqueda(texto):
    return v.texto_libre(texto, 'busqueda', maximo=MAXIMO_BUSQUEDA) or None


def mantenimientos(actor, busqueda, huerto, planta, tipo, estado, desde, hasta, pagina):
    s.require_cap(actor, CAPACIDAD_MANTENIMIENTOS)
    if estado is not None and estado not in ESTADOS_CUIDADO:
        raise ValidationError('Filtro no válido')
    consulta = _filtrar_cuidados(_mantenimientos(), planta, tipo, desde, hasta)
    if busqueda := _busqueda(busqueda):
        consulta = consulta.filter(Q(huerto__nombre__icontains=busqueda) | Q(huerto__propietario__email__icontains=busqueda))
    if huerto:
        consulta = consulta.filter(huerto_id=_id_numerico(huerto, 'huerto'))
    if estado:
        consulta = consulta.filter(rev_tipo=ESTADOS_CUIDADO[estado]) if ESTADOS_CUIDADO[estado] else consulta.filter(rev_tipo__isnull=True)
    return {'status': 'ready', **paginar(consulta.order_by('-realizado_en', '-registrado_en', 'id'), pagina, _mantenimiento_dto)}


def _revision_dto(revision):
    return {'number': revision.numero, 'type': revision.tipo, 'correctedType': revision.tipo_corregido, 'correctedPlant': revision.planta_corregida,
            'correctedChiles': revision.chiles_corregidos, 'reason': revision.motivo, 'editor': revision.editor.email, 'at': _fecha(revision.registrada_en)}


def _mantenimiento(cuidado_id):
    cuidado = _mantenimientos().filter(pk=cuidado_id).first()
    if cuidado is None:
        raise Http404
    return cuidado


def detalle_mantenimiento(actor, cuidado_id):
    s.require_cap(actor, CAPACIDAD_MANTENIMIENTOS)
    cuidado = _mantenimiento(cuidado_id)
    revisiones = CuidadoRevision.objects.select_related('editor').filter(cuidado_id=cuidado.pk).order_by('numero')
    return {'status': 'ready', 'record': _mantenimiento_dto(cuidado), 'revisions': [_revision_dto(revision) for revision in revisiones]}


@transaction.atomic
def registrar_mantenimiento(actor, huerto_id, tipo, planta, chiles, realizado_en):
    admin = s.require_cap(actor, CAPACIDAD_MANTENIMIENTOS)
    huerto = Huerto.objects.filter(pk=_id_numerico(huerto_id), estado='activo').first()
    if huerto is None:
        raise Http404
    cuidado = _crear_cuidado(admin, huerto, tipo, planta, chiles, realizado_en)
    return {'status': 'accepted', 'record': _mantenimiento_dto(_mantenimiento(cuidado.pk))}


def _motivo_de_revision(motivo):
    return v.texto_libre(motivo, 'reason', maximo=MAXIMO_MOTIVO, multilinea=True, requerido=True)


def _revisar(editor, cuidado_id, revision, motivo, accion, **campos):
    """Agrega la revisión siguiente. `revision` es la que la persona vio: si otra se adelantó, el registro está desactualizado."""
    motivo = _motivo_de_revision(motivo)
    cuidado = _mantenimiento(cuidado_id)
    if cuidado.rev_tipo == 'anulacion':
        raise ReglaDeNegocio('cuidado-anulado', 'Este registro ya está anulado y no admite más cambios.')
    if type(revision) is not int or revision < 0:
        raise ValidationError('Revisión no válida')
    if revision != (cuidado.rev_numero or 0):
        raise s.RegistroDesactualizado
    CuidadoRevision.objects.create(cuidado_id=cuidado.pk, numero=revision + 1, motivo=motivo, editor_id=editor.pk, **campos)
    s.auditar(editor, accion, entidad='cuidado', entidad_id=cuidado.pk, detalle={'revision': revision + 1})
    return {'status': 'accepted', 'record': _mantenimiento_dto(_mantenimiento(cuidado.pk))}


@transaction.atomic
def corregir_mantenimiento(actor, cuidado_id, revision, tipo, planta, chiles, motivo):
    editor = s.require_cap(actor, CAPACIDAD_MANTENIMIENTOS)
    _validar_cuidado(tipo, planta, chiles)
    return _revisar(editor, cuidado_id, revision, motivo, 'corregir_cuidado', tipo='correccion',
                    tipo_corregido=tipo, planta_corregida=planta, chiles_corregidos=chiles)


@transaction.atomic
def anular_mantenimiento(actor, cuidado_id, revision, motivo):
    editor = s.require_cap(actor, CAPACIDAD_MANTENIMIENTOS)
    return _revisar(editor, cuidado_id, revision, motivo, 'anular_cuidado', tipo='anulacion')


# ── Panel técnico y bitácora ──
def _punto(momento, valor, minimo=None, maximo=None):
    return {'at': _fecha(momento), 'value': _numero(valor), 'min': _numero(minimo), 'max': _numero(maximo)}


def _series_crudas(huerto, desde):
    mediciones = list(Medicion.objects.filter(huerto_id=huerto.pk, medida_en__gte=desde).order_by('-medida_en')[:MAXIMO_PUNTOS])
    mediciones.reverse()
    lecturas = (MedicionPlanta.objects.filter(medicion_id__in=[medicion.pk for medicion in mediciones]).select_related('medicion'))
    plantas = {1: [], 2: [], 3: []}
    for fila in sorted(lecturas, key=lambda fila: fila.medicion.medida_en):
        plantas[fila.planta_numero].append(_punto(fila.medicion.medida_en, fila.humedad_sustrato_pct))
    serie = lambda campo: [_punto(m.medida_en, getattr(m, campo)) for m in mediciones if getattr(m, campo) is not None]
    return {'plants': [{'number': numero, 'points': puntos} for numero, puntos in plantas.items()],
            'temperature': serie('temperatura_c'), 'humidity': serie('humedad_aire_pct'), 'light': serie('luz_lux')}


def _series_por_hora(huerto, desde):
    horas = list(ResumenHoraHuerto.objects.filter(huerto_id=huerto.pk, hora__gte=desde).order_by('-hora')[:MAXIMO_PUNTOS])
    horas.reverse()
    plantas = {1: [], 2: [], 3: []}
    filas = ResumenHoraPlanta.objects.filter(huerto_id=huerto.pk, hora__gte=desde).order_by('hora')
    for fila in filas:
        plantas[fila.planta_numero].append(_punto(fila.hora, fila.humedad_prom, fila.humedad_min, fila.humedad_max))
    return {'plants': [{'number': numero, 'points': puntos[-MAXIMO_PUNTOS:]} for numero, puntos in plantas.items()],
            'temperature': [_punto(h.hora, h.temperatura_prom, h.temperatura_min, h.temperatura_max) for h in horas if h.temperatura_prom is not None],
            'humidity': [_punto(h.hora, h.humedad_aire_prom, h.humedad_aire_min, h.humedad_aire_max) for h in horas if h.humedad_aire_prom is not None],
            'light': [_punto(h.hora, h.luz_prom, None, h.luz_max) for h in horas if h.luz_prom is not None]}


def _lectura_planta_dto(planta, lectura):
    return {'number': planta.numero, 'name': planta.nombre, 'moisture': _numero(lectura.humedad_sustrato_pct) if lectura else None,
            'adc': lectura.adc_crudo if lectura else None, 'measuredAt': _fecha(lectura.medicion.medida_en) if lectura else None}


def telemetria(actor, huerto_id, rango):
    if rango not in RANGOS:
        raise ValidationError('Rango no válido')
    huerto = s.huerto_propio(actor, huerto_id)
    desde = timezone.now() - RANGOS[rango]
    series = _series_crudas(huerto, desde) if rango in ('1h', '24h') else _series_por_hora(huerto, desde)
    plantas = Planta.objects.filter(huerto_id=huerto.pk).order_by('numero')
    return {'status': 'ready', 'range': rango, 'garden': _huerto_dto(huerto, _equipo_de(huerto)), 'latest': _metricas(huerto),
            'hasLight': Medicion.objects.filter(huerto_id=huerto.pk, luz_lux__isnull=False).exists(),
            'plants': [_lectura_planta_dto(planta, _ultima_lectura_planta(huerto, planta.numero)) for planta in plantas],
            'series': series}


def _actuacion_dto(actuacion):
    return {'actuator': actuacion.actuador, 'plant': actuacion.planta_numero, 'action': actuacion.accion,
            'duration': actuacion.duracion_s, 'origin': actuacion.origen, 'at': _fecha(actuacion.ocurrido_en)}


def _evento_dto(evento):
    return {'type': evento.tipo, 'detail': evento.detalle or None, 'at': _fecha(evento.ocurrido_en)}


def bitacora(actor, huerto_id, tipo, pagina):
    if tipo not in TIPOS_BITACORA:
        raise ValidationError('Bitácora no válida')
    huerto = s.huerto_propio(actor, huerto_id)
    consulta, adaptador = {
        'ordenes': (Comando.objects.filter(huerto_id=huerto.pk).order_by('-creado_en'), _comando_dto),
        'actuaciones': (Actuacion.objects.filter(huerto_id=huerto.pk).order_by('-ocurrido_en', '-id'), _actuacion_dto),
        'eventos': (DispositivoEvento.objects.filter(huerto_id=huerto.pk).order_by('-ocurrido_en', '-id'), _evento_dto)}[tipo]
    return {'status': 'ready', 'type': tipo, **paginar(consulta, pagina, adaptador)}


# ── Vinculación del equipo ──

def normalizar_codigo(texto):
    """Código XXXX-XXXX sin guiones ni espacios; las letras confundibles se leen como Crockford (O→0, I y L→1)."""
    if not isinstance(texto, str) or len(texto) > 20:
        return None
    limpio = re.sub(r'[\s-]', '', texto.upper()).translate(str.maketrans('OIL', '011'))
    return limpio if len(limpio) == LARGO_CODIGO and set(limpio) <= set(ALFABETO_CODIGO) else None


def huella_codigo(codigo):
    return hmac.new(settings.CHILITO_VINCULACION_SECRETO.encode(), codigo.encode(), hashlib.sha256).hexdigest()


def _nuevo_codigo():
    return ''.join(secrets.choice(ALFABETO_CODIGO) for _ in range(LARGO_CODIGO))


@transaction.atomic
def generar_codigo(actor, huerto_id):
    huerto = s.huerto_propio(actor, huerto_id, bloquear=True)
    CodigoVinculacion.objects.filter(huerto_id=huerto.pk, estado='pendiente').update(estado='cancelado', cerrado_en=timezone.now())
    codigo = _nuevo_codigo()
    registro = CodigoVinculacion.objects.create(huerto=huerto, generado_por_id=actor.pk, codigo_hash=huella_codigo(codigo))
    registro.refresh_from_db()
    s.auditar(actor, 'generar_codigo', entidad='huerto', entidad_id=huerto.pk)
    # La clave se llama `code`: el recibo de idempotencia la guarda vacía y el código no queda en la base.
    return {'status': 'accepted', 'code': f'{codigo[:4]}-{codigo[4:]}', 'expiresAt': _fecha(registro.vence_en)}


def estado_vinculacion(actor, huerto_id):
    huerto = s.huerto_propio(actor, huerto_id)
    equipo = _equipo_de(huerto)
    codigo = CodigoVinculacion.objects.filter(huerto_id=huerto.pk).order_by('-generado_en').first()
    if codigo and codigo.estado == 'pendiente' and codigo.vence_en <= timezone.now():
        estado = 'expirado'
    else:
        estado = codigo.estado if codigo else None
    return {'status': 'ready', 'linked': equipo is not None, 'device': _equipo_dto(equipo), 'codeState': estado,
            'expiresAt': _fecha(codigo.vence_en) if codigo else None}


@transaction.atomic
def desvincular(actor, huerto_id):
    huerto = s.huerto_propio(actor, huerto_id, bloquear=True)
    equipo = _equipo_de(huerto)
    if equipo is None:
        raise Http404
    with connection.cursor() as cursor:
        cursor.execute('SELECT chilito_desvincular_dispositivo(%s)', [equipo.pk])
    s.auditar(actor, 'desvincular_dispositivo', entidad='dispositivo', entidad_id=equipo.pk)
    return {'status': 'accepted'}


def vincular_dispositivo(identificador, credencial, codigo):
    """Equipo sin sesión: devuelve solo el resultado de la base. Credencial inválida y equipo desconocido son iguales."""
    equipo = Dispositivo.objects.filter(identificador=identificador).first()
    credencial_valida = check_password(credencial, equipo.credencial_hash if equipo else _hash_ficticio())
    normalizado = normalizar_codigo(codigo)
    if equipo is None or not credencial_valida:
        return 'credencial_invalida'
    if normalizado is None:
        return 'codigo_invalido'
    with connection.cursor() as cursor:
        cursor.execute('SELECT resultado FROM chilito_vincular_dispositivo(%s, %s)', [identificador, huella_codigo(normalizado)])
        return cursor.fetchone()[0]
