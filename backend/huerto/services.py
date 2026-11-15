"""Huertos, plantas, órdenes y vinculación del equipo. Todo recurso se busca por la cuenta que lo pide:
un huerto ajeno o archivado es igual de inexistente que uno que no está (404)."""
import hashlib
import hmac
import re
import secrets
from functools import cache
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.http import Http404
from django.utils import timezone

from datos import services as s
from datos.models import (Actuacion, CodigoVinculacion, Comando, Cuidado, Dispositivo, IaResumen, Medicion,
                          MedicionPlanta, ResumenHoraPlanta)
from datos.paginacion import paginar

from .models import Huerto, Planta, PlantaEtapa

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


@cache
def _hash_ficticio():
    """Hash de una credencial inexistente: un identificador desconocido tarda lo mismo que uno conocido."""
    return make_password('sin-equipo')


def _numero(valor):
    return None if valor is None else float(valor)


def _fecha(valor):
    return valor.isoformat() if valor else None


def _entero(valor, minimo, maximo):
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ValidationError('Número no válido')
    return valor


def _huerto(actor, huerto_id, *, bloquear=False):
    consulta = Huerto.objects.select_for_update() if bloquear else Huerto.objects
    huerto = consulta.filter(pk=huerto_id, propietario_id=actor.pk, estado='activo').first()
    if huerto is None:
        raise Http404
    return huerto


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
    if nombre is None:
        return None
    if not isinstance(nombre, str) or not nombre.isprintable() or not 1 <= len(nombre.strip()) <= 60:
        raise ValidationError('Nombre no válido')
    return nombre.strip()


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
    huerto = _huerto(actor, huerto_id, bloquear=True)
    huerto.nombre = _nombre_huerto(nombre)
    if huerto.nombre is None:
        raise ValidationError('Nombre no válido')
    huerto.save(update_fields=['nombre'])
    s.auditar(actor, 'renombrar_huerto', entidad='huerto', entidad_id=huerto.pk)
    return {'status': 'accepted', 'garden': _huerto_dto(huerto, _equipo_de(huerto))}


@transaction.atomic
def archivar(actor, huerto_id):
    huerto = _huerto(actor, huerto_id, bloquear=True)
    huerto.estado = 'archivado'
    huerto.save(update_fields=['estado'])
    s.auditar(actor, 'archivar_huerto', entidad='huerto', entidad_id=huerto.pk)
    return {'status': 'accepted'}


# ── Lectura de «Mi huerto» ──

def _planta_dto(planta, lectura):
    hoy = datetime.now(ZoneInfo('America/Merida')).date()
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
    huerto = _huerto(actor, huerto_id)
    equipo = _equipo_de(huerto)
    plantas = Planta.objects.filter(huerto_id=huerto.pk).order_by('numero')
    resumen = IaResumen.objects.filter(huerto_id=huerto.pk).order_by('-generado_en').first()
    return {'status': 'ready', 'garden': _huerto_dto(huerto, equipo),
            'plants': [_planta_dto(planta, _ultima_lectura_planta(huerto, planta.numero)) for planta in plantas],
            'metrics': _metricas(huerto) if equipo else None, 'lamp': _lampara(huerto) if equipo else None,
            'summary': _resumen_ia_dto(resumen) if resumen else None}


def resumenes_ia(actor, huerto_id, pagina):
    huerto = _huerto(actor, huerto_id)
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
        filas = (MedicionPlanta.objects.filter(medicion__huerto_id=huerto.pk, planta_numero=numero, medicion__medida_en__gte=desde)
                 .select_related('medicion').order_by('medicion__medida_en')[:MAXIMO_PUNTOS])
        return [{'at': _fecha(fila.medicion.medida_en), 'value': _numero(fila.humedad_sustrato_pct)} for fila in filas]
    filas = (ResumenHoraPlanta.objects.filter(huerto_id=huerto.pk, planta_numero=numero, hora__gte=desde)
             .order_by('hora')[:MAXIMO_PUNTOS])
    return [{'at': _fecha(fila.hora), 'value': _numero(fila.humedad_prom)} for fila in filas]


def _cuidado_dto(cuidado):
    return {'id': str(cuidado.pk), 'type': cuidado.tipo, 'plant': cuidado.planta_numero,
            'chiles': cuidado.chiles_cosechados, 'doneAt': _fecha(cuidado.realizado_en)}


def _ultimo_riego(huerto, numero):
    riego = (Actuacion.objects.filter(huerto_id=huerto.pk, actuador='bomba', planta_numero=numero, accion='encendido')
             .order_by('-ocurrido_en').first())
    return {'at': _fecha(riego.ocurrido_en), 'origin': riego.origen, 'duration': riego.duracion_s} if riego else None


def detalle_planta(actor, huerto_id, numero, rango):
    if rango not in RANGOS:
        raise ValidationError('Rango no válido')
    huerto = _huerto(actor, huerto_id)
    planta = _planta(huerto, numero)
    historial = PlantaEtapa.objects.filter(planta_id=planta.pk).order_by('desde', 'id')
    cuidados = Cuidado.objects.filter(huerto_id=huerto.pk, planta_numero=numero).order_by('-realizado_en')[:10]
    return {'status': 'ready', 'plant': _planta_dto(planta, _ultima_lectura_planta(huerto, numero)),
            'stages': [{'stage': fila.etapa, 'since': _fecha(fila.desde)} for fila in historial],
            'series': _serie(huerto, numero, rango), 'range': rango, 'care': [_cuidado_dto(c) for c in cuidados],
            'lastWatering': _ultimo_riego(huerto, numero), 'hasDevice': _equipo_de(huerto) is not None}


def _nombre_planta(nombre):
    if not isinstance(nombre, str) or not nombre.isprintable() or not 1 <= len(nombre.strip()) <= 40:
        raise ValidationError('Nombre no válido')
    return nombre.strip()


def _fecha_siembra(valor):
    if valor is None:
        return None
    siembra = date.fromisoformat(valor) if isinstance(valor, str) and len(valor) == 10 else None
    if siembra is None or siembra > datetime.now(ZoneInfo('America/Merida')).date():
        raise ValidationError('Fecha no válida')
    return siembra


@transaction.atomic
def editar_planta(actor, huerto_id, numero, datos):
    huerto = _huerto(actor, huerto_id)
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

def _comando_dto(comando):
    return {'id': str(comando.pk), 'type': comando.tipo, 'plant': comando.planta_numero, 'duration': comando.duracion_s,
            'state': comando.estado, 'createdAt': _fecha(comando.creado_en), 'sentAt': _fecha(comando.enviado_en),
            'resolvedAt': _fecha(comando.resuelto_en), 'error': comando.detalle_error or None}


@transaction.atomic
def crear_comando(actor, huerto_id, tipo, planta, duracion):
    huerto = _huerto(actor, huerto_id)
    if tipo not in TIPOS_COMANDO:
        raise ValidationError('Orden no válida')
    if tipo == 'regar':
        _entero(planta, 1, 3)
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
    return {'status': 'accepted', 'command': _comando_dto(comando)}


def estado_comando(actor, comando_id):
    comando = Comando.objects.filter(pk=comando_id, solicitado_por_id=actor.pk, origen='usuario').first()
    if comando is None:
        raise Http404
    return {'status': 'ready', 'command': _comando_dto(comando)}


@transaction.atomic
def registrar_cuidado(actor, huerto_id, tipo, planta, chiles):
    huerto = _huerto(actor, huerto_id)
    if tipo not in TIPOS_CUIDADO:
        raise ValidationError('Cuidado no válido')
    if tipo == 'rellenar_deposito' and planta is not None:
        raise ValidationError('Datos que sobran')
    if tipo in TIPOS_CUIDADO_DE_PLANTA or (tipo == 'inspeccion' and planta is not None):
        _entero(planta, 1, 3)
    if chiles is not None and (tipo != 'cosecha' or type(chiles) is not int or not 0 <= chiles <= 999):
        raise ValidationError('Cantidad no válida')
    cuidado = Cuidado.objects.create(huerto=huerto, tipo=tipo, planta_numero=planta, chiles_cosechados=chiles,
                                     registrado_por_id=actor.pk)
    cuidado.refresh_from_db()
    s.auditar(actor, 'registrar_cuidado', entidad='cuidado', entidad_id=cuidado.pk, detalle={'tipo': tipo})
    return {'status': 'accepted', 'care': _cuidado_dto(cuidado)}


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
    huerto = _huerto(actor, huerto_id, bloquear=True)
    CodigoVinculacion.objects.filter(huerto_id=huerto.pk, estado='pendiente').update(estado='cancelado', cerrado_en=timezone.now())
    codigo = _nuevo_codigo()
    registro = CodigoVinculacion.objects.create(huerto=huerto, generado_por_id=actor.pk, codigo_hash=huella_codigo(codigo))
    registro.refresh_from_db()
    s.auditar(actor, 'generar_codigo', entidad='huerto', entidad_id=huerto.pk)
    # La clave se llama `code`: el recibo de idempotencia la guarda vacía y el código no queda en la base.
    return {'status': 'accepted', 'code': f'{codigo[:4]}-{codigo[4:]}', 'expiresAt': _fecha(registro.vence_en)}


def estado_vinculacion(actor, huerto_id):
    huerto = _huerto(actor, huerto_id)
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
    huerto = _huerto(actor, huerto_id, bloquear=True)
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
