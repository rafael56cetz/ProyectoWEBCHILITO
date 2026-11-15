"""Inventario de equipos para quien tiene `gestionar_dispositivos` y flota para quien tiene `ver_flota`. La credencial del equipo se genera aquí, se muestra una sola
vez y en la base solo queda su hash. El detalle de qué puede hacer cada rol lo decide la base; aquí se validan las entradas y
se evita pedirle lo que ya sabemos que rechazará."""
import re
import secrets
from datetime import datetime, time, timedelta

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.http import Http404
from django.utils import timezone

from huerto.models import Huerto
from huerto.services import ZONA_MERIDA
from web.respuestas import ReglaDeNegocio

from . import services as s
from .models import Autodiagnostico, Comando, Dispositivo, DispositivoEvento, ResumenHoraHuerto, ResumenHoraPlanta, Venta
from .paginacion import paginar, paginar_sql

CAPACIDAD = 'gestionar_dispositivos'
ESTADOS = ('disponible', 'vinculado', 'retirado')
CONEXIONES = ('nunca', 'en_linea', 'desconectado')
VENDIDO = ('si', 'no')
IDENTIFICADOR = re.compile(r'^[A-Za-z0-9][A-Za-z0-9-]{3,31}$')
MAC = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')
FIRMWARE = re.compile(r'^[A-Za-z0-9._-]{1,32}$')
MAXIMO_BUSQUEDA = 60
DIAGNOSTICOS_EN_FICHA = 5
CAPACIDAD_FLOTA = 'ver_flota'
DIAS_TENDENCIA = 7
HORAS_PROBLEMAS = 24
PROBLEMAS_VISIBLES = 10
ORIGEN = ('v_estado_equipos v JOIN dispositivo d ON d.id = v.dispositivo_id '
          "LEFT JOIN venta ve ON ve.dispositivo_id = d.id AND ve.estado = 'vigente'")
COLUMNAS = ('v.dispositivo_id, v.identificador, d.mac::text AS mac, v.estado, v.conexion, v.ultima_conexion_en, v.firmware_version, '
            'v.huerto_id, v.huerto, v.dueno, ve.id AS venta_id, ve.comprador_nombre')


def _fecha(valor):
    return valor.isoformat() if valor else None


def _fila_dto(fila):
    venta = {'id': str(fila['venta_id']), 'buyer': fila['comprador_nombre']} if fila['venta_id'] else None
    return {'id': str(fila['dispositivo_id']), 'identifier': fila['identificador'], 'mac': fila['mac'], 'state': fila['estado'],
            'connection': fila['conexion'], 'lastConnectionAt': _fecha(fila['ultima_conexion_en']), 'firmware': fila['firmware_version'] or None,
            'gardenId': str(fila['huerto_id']) if fila['huerto_id'] else None, 'garden': fila['huerto'], 'owner': fila['dueno'], 'sale': venta}


def _like(texto):
    return '%' + re.sub(r'([\\%_])', r'\\\1', texto) + '%'


def _filtros(busqueda, estado, conexion, vendido):
    if busqueda is not None and (not isinstance(busqueda, str) or len(busqueda) > MAXIMO_BUSQUEDA or not busqueda.isprintable()):
        raise ValidationError('Búsqueda no válida')
    if estado not in (None, *ESTADOS) or conexion not in (None, *CONEXIONES) or vendido not in (None, *VENDIDO):
        raise ValidationError('Filtro no válido')
    donde, parametros = [], []
    if busqueda and busqueda.strip():
        donde.append('(v.identificador ILIKE %s OR d.mac::text ILIKE %s OR v.dueno ILIKE %s)')
        parametros += [_like(busqueda.strip())] * 3
    for columna, valor in (('v.estado', estado), ('v.conexion', conexion)):
        if valor:
            donde.append(f'{columna} = %s')
            parametros.append(valor)
    if vendido:
        donde.append('ve.id IS NOT NULL' if vendido == 'si' else 've.id IS NULL')
    return ('WHERE ' + ' AND '.join(donde)) if donde else '', parametros


def listar(actor, busqueda, estado, conexion, vendido, pagina):
    s.require_cap(actor, CAPACIDAD)
    donde, parametros = _filtros(busqueda, estado, conexion, vendido)
    conteo = {fila['estado']: fila['n'] for fila in Dispositivo.objects.values('estado').annotate(n=Count('id'))}
    pagina_equipos = paginar_sql(COLUMNAS, f'{ORIGEN} {donde}', 'v.identificador', parametros, pagina, _fila_dto)
    return {'status': 'ready', 'counts': {estado: conteo.get(estado, 0) for estado in ESTADOS}, **pagina_equipos}


def _credencial_nueva():
    credencial = secrets.token_urlsafe(32)
    return credencial, make_password(credencial)


@transaction.atomic
def crear(actor, identificador, mac, firmware):
    usuario = s.require_cap(actor, CAPACIDAD)
    if not isinstance(identificador, str) or not IDENTIFICADOR.match(identificador):
        raise ValidationError('Identificador no válido')
    if not isinstance(mac, str) or not MAC.match(mac):
        raise ValidationError('MAC no válida')
    if firmware not in (None, '') and (not isinstance(firmware, str) or not FIRMWARE.match(firmware)):
        raise ValidationError('Firmware no válido')
    mac = mac.lower()
    if Dispositivo.objects.filter(identificador__iexact=identificador).exists() or Dispositivo.objects.filter(mac=mac).exists():
        raise ReglaDeNegocio('equipo-duplicado', 'Ya existe un equipo con ese identificador o esa MAC.')
    credencial, hash_credencial = _credencial_nueva()
    equipo = Dispositivo.objects.create(identificador=identificador, mac=mac, credencial_hash=hash_credencial,
                                        firmware_version=firmware or '', registrado_por=usuario)
    s.auditar(usuario, 'alta_equipo', entidad='dispositivo', entidad_id=equipo.pk)
    return {'status': 'accepted', 'device': {'id': str(equipo.pk), 'identifier': equipo.identificador}, 'credential': credencial}


def _equipo(equipo_id, *, bloquear=False):
    consulta = Dispositivo.objects.select_for_update() if bloquear else Dispositivo.objects
    equipo = consulta.filter(pk=equipo_id).first()
    if equipo is None:
        raise Http404
    return equipo


def _evento_dto(evento):
    return {'type': evento.tipo, 'detail': evento.detalle or None, 'actor': evento.actor.email if evento.actor_id else None, 'at': _fecha(evento.ocurrido_en)}


def _ficha(equipo):
    huerto = Huerto.objects.select_related('propietario').filter(pk=equipo.huerto_id).first() if equipo.huerto_id else None
    venta = Venta.objects.filter(dispositivo_id=equipo.pk, estado='vigente').first()
    return {'id': str(equipo.pk), 'identifier': equipo.identificador, 'mac': equipo.mac, 'state': equipo.estado, 'connection': equipo.conexion,
            'lastConnectionAt': _fecha(equipo.ultima_conexion_en), 'firmware': equipo.firmware_version or None,
            'registeredAt': _fecha(equipo.registrado_en), 'registeredBy': equipo.registrado_por.email if equipo.registrado_por_id else None,
            'linkedAt': _fecha(equipo.vinculado_en), 'retiredAt': _fecha(equipo.retirado_en),
            'garden': {'id': str(huerto.pk), 'name': huerto.nombre} if huerto else None, 'owner': huerto.propietario.email if huerto else None,
            'sale': {'id': str(venta.pk), 'buyer': venta.comprador_nombre, 'payment': venta.estado_pago} if venta else None}


def detalle(actor, equipo_id, pagina):
    s.require_cap(actor, CAPACIDAD)
    equipo = Dispositivo.objects.select_related('registrado_por').filter(pk=equipo_id).first()
    if equipo is None:
        raise Http404
    eventos = DispositivoEvento.objects.select_related('actor').filter(dispositivo_id=equipo.pk).order_by('-ocurrido_en', '-id')
    diagnosticos = Autodiagnostico.objects.filter(dispositivo_id=equipo.pk).order_by('-iniciado_en')[:DIAGNOSTICOS_EN_FICHA]
    return {'status': 'ready', 'device': _ficha(equipo), 'events': paginar(eventos, pagina, _evento_dto),
            'diagnostics': [{'id': str(d.pk), 'state': d.estado, 'overall': d.resultado_general, 'startedAt': _fecha(d.iniciado_en)} for d in diagnosticos]}


@transaction.atomic
def desvincular(actor, equipo_id):
    s.require_cap(actor, CAPACIDAD)
    equipo = _equipo(equipo_id, bloquear=True)
    if equipo.estado != 'vinculado':
        raise ReglaDeNegocio('equipo-no-vinculado', 'Este equipo no está vinculado a ningún huerto.')
    # La función de la base también escribe la auditoría `desvincular_dispositivo`: no se repite aquí.
    with connection.cursor() as cursor:
        cursor.execute('SELECT chilito_desvincular_dispositivo(%s)', [equipo.pk])
    return {'status': 'accepted', 'device': _ficha(_equipo(equipo.pk))}


@transaction.atomic
def rotar_credencial(actor, equipo_id):
    usuario = s.require_cap(actor, CAPACIDAD)
    equipo = _equipo(equipo_id, bloquear=True)
    if equipo.estado == 'retirado':
        raise ReglaDeNegocio('equipo-retirado', 'Un equipo retirado no recibe credenciales nuevas.')
    credencial, hash_credencial = _credencial_nueva()
    equipo.credencial_hash = hash_credencial
    equipo.save(update_fields=['credencial_hash'])
    s.auditar(usuario, 'rotar_credencial', entidad='dispositivo', entidad_id=equipo.pk)
    return {'status': 'accepted', 'credential': credencial}


@transaction.atomic
def retirar(actor, equipo_id):
    usuario = s.require_cap(actor, CAPACIDAD)
    equipo = _equipo(equipo_id, bloquear=True)
    if equipo.estado != 'disponible':
        raise ReglaDeNegocio('equipo-no-disponible', 'Solo se retira un equipo disponible. Desvincúlalo primero.')
    equipo.estado, equipo.retirado_en = 'retirado', timezone.now()
    equipo.save(update_fields=['estado', 'retirado_en'])
    s.auditar(usuario, 'retirar_equipo', entidad='dispositivo', entidad_id=equipo.pk)
    return {'status': 'accepted', 'device': _ficha(_equipo(equipo.pk))}


# ── Flota (`ver_flota`) ──
COLUMNAS_FLOTA = ('v.dispositivo_id, v.identificador, v.estado, v.conexion, v.ultima_conexion_en, v.firmware_version, v.huerto_id, v.huerto, '
                  'v.dueno, v.ultima_medicion_en, '
                  '(SELECT max(a.iniciado_en) FROM autodiagnostico a WHERE a.dispositivo_id = v.dispositivo_id) AS ultima_revision_en')


def _fila_flota_dto(fila):
    return {'id': str(fila['dispositivo_id']), 'identifier': fila['identificador'], 'state': fila['estado'], 'connection': fila['conexion'],
            'lastConnectionAt': _fecha(fila['ultima_conexion_en']), 'lastReadingAt': _fecha(fila['ultima_medicion_en']),
            'firmware': fila['firmware_version'] or None, 'gardenId': str(fila['huerto_id']) if fila['huerto_id'] else None,
            'garden': fila['huerto'], 'owner': fila['dueno'], 'lastReviewAt': _fecha(fila['ultima_revision_en'])}


def _totales_flota():
    conexiones = {fila['conexion']: fila['n'] for fila in Dispositivo.objects.filter(estado='vinculado').values('conexion').annotate(n=Count('id'))}
    return {'linked': sum(conexiones.values()), 'online': conexiones.get('en_linea', 0), 'offline': conexiones.get('desconectado', 0)}


def _tendencia(modelo, campo):
    """Promedio diario de todos los huertos, ponderado por las muestras de cada hora. Un día sin muestras no tiene punto."""
    primer_dia = datetime.now(ZONA_MERIDA).date() - timedelta(days=DIAS_TENDENCIA - 1)
    ponderado = ExpressionWrapper(F(campo) * F('muestras'), output_field=DecimalField(max_digits=12, decimal_places=1))
    dias = (modelo.objects.filter(hora__gte=datetime.combine(primer_dia, time.min, ZONA_MERIDA), **{f'{campo}__isnull': False})
            .annotate(dia=TruncDate('hora', tzinfo=ZONA_MERIDA)).values('dia')
            .annotate(suma=Sum(ponderado), muestras_dia=Sum('muestras')).order_by('dia'))
    # Mediodía de Mérida: una fecha sola se leería en UTC y el navegador la mostraría el día anterior.
    return [{'at': datetime.combine(fila['dia'], time(12), ZONA_MERIDA).isoformat(), 'value': round(float(fila['suma']) / fila['muestras_dia'], 1)} for fila in dias]


def _problema(tipo, equipo_id, identificador, momento, detalle=None):
    return {'type': tipo, 'deviceId': str(equipo_id), 'identifier': identificador, 'at': _fecha(momento), 'detail': detalle}


def _problemas_recientes():
    """Autodiagnósticos con fallas, órdenes fallidas y equipos vinculados sin conexión desde hace más de un día."""
    desde = timezone.now() - timedelta(hours=HORAS_PROBLEMAS)
    diagnosticos = Autodiagnostico.objects.select_related('dispositivo').filter(resultado_general='con_fallas', completado_en__gte=desde)
    ordenes = Comando.objects.select_related('dispositivo').filter(estado='fallido', resuelto_en__gte=desde)
    ausentes = Dispositivo.objects.filter(estado='vinculado', conexion='desconectado', ultima_conexion_en__lt=desde)
    problemas = ([_problema('diagnostic', d.dispositivo_id, d.dispositivo.identificador, d.completado_en) for d in diagnosticos]
                 + [_problema('order', o.dispositivo_id, o.dispositivo.identificador, o.resuelto_en, o.tipo) for o in ordenes]
                 + [_problema('offline', e.pk, e.identificador, e.ultima_conexion_en) for e in ausentes])
    equipos = {problema['deviceId'] for problema in problemas}
    problemas.sort(key=lambda problema: problema['at'], reverse=True)
    return len(equipos), problemas[:PROBLEMAS_VISIBLES]


def flota(actor, busqueda, estado, conexion, pagina):
    s.require_cap(actor, CAPACIDAD_FLOTA)
    donde, parametros = _filtros(busqueda, estado, conexion, None)
    con_problemas, problemas = _problemas_recientes()
    return {'status': 'ready', 'totals': {**_totales_flota(), 'problems': con_problemas},
            'trends': {'moisture': _tendencia(ResumenHoraPlanta, 'humedad_prom'), 'temperature': _tendencia(ResumenHoraHuerto, 'temperatura_prom')},
            'problems': problemas, **paginar_sql(COLUMNAS_FLOTA, f'{ORIGEN} {donde}', 'v.identificador', parametros, pagina, _fila_flota_dto)}
