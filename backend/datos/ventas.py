"""Ventas de equipos para quien tiene `gestionar_ventas`. La base calcula el estado del pago y no deja borrar ventas, solo cancelarlas;
aquí se validan las entradas y lo razonable que la base no cubre (el importe no baja, la entrega cae entre la venta y hoy)."""
import re
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import Http404

from web import validacion as v
from web.respuestas import ReglaDeNegocio

from . import services as s
from .models import Dispositivo, Venta
from .paginacion import paginar

CAPACIDAD = 'gestionar_ventas'
MODALIDADES = ('domicilio', 'recogida')
PAGOS = ('pendiente', 'parcial', 'completo')
ENTREGAS = ('por_entregar', 'entregada')
ESTADOS = ('vigente', 'cancelada')
CORREO = re.compile(r'^[^@\s]+@[^@\s]+$')
PRECIO_MAXIMO = Decimal('99999999.99')
MAXIMO_EQUIPOS_VENDIBLES = 500
# Los 106 municipios de Yucatán, tal como los lista el Decreto 169/2026 del Congreso del Estado.
MUNICIPIOS_YUCATAN = (
    'Abalá', 'Acanceh', 'Akil', 'Baca', 'Bokobá', 'Buctzotz', 'Cacalchén', 'Calotmul', 'Cansahcab', 'Cantamayec', 'Celestún', 'Cenotillo',
    'Chacsinkín', 'Chankom', 'Chapab', 'Chemax', 'Chichimilá', 'Chicxulub Pueblo', 'Chikindzonot', 'Chocholá', 'Chumayel', 'Conkal',
    'Cuncunul', 'Cuzamá', 'Dzan', 'Dzemul', 'Dzidzantún', 'Dzilam de Bravo', 'Dzilam González', 'Dzitás', 'Dzoncauich', 'Espita',
    'Halachó', 'Hocabá', 'Hoctún', 'Homún', 'Huhí', 'Hunucmá', 'Ixil', 'Izamal', 'Kanasín', 'Kantunil', 'Kaua', 'Kinchil', 'Kopomá',
    'Mama', 'Maní', 'Maxcanú', 'Mayapán', 'Mérida', 'Mocochá', 'Motul', 'Muna', 'Muxupip', 'Opichén', 'Oxkutzcab', 'Panabá', 'Peto',
    'Progreso', 'Quintana Roo', 'Río Lagartos', 'Sacalum', 'Samahil', 'San Felipe', 'Sanahcat', 'Santa Elena', 'Seyé', 'Sinanché',
    'Sotuta', 'Sucilá', 'Sudzal', 'Suma', 'Tahdziú', 'Tahmek', 'Teabo', 'Tecoh', 'Tekal de Venegas', 'Tekantó', 'Tekax', 'Tekit',
    'Tekom', 'Telchac Pueblo', 'Telchac Puerto', 'Temax', 'Temozón', 'Tepakán', 'Tetiz', 'Teya', 'Ticul', 'Timucuy', 'Tinum', 'Tixcacalcupul',
    'Tixkokob', 'Tixméhuac', 'Tixpéual', 'Tizimín', 'Tunkás', 'Tzucacab', 'Uayma', 'Ucú', 'Umán', 'Valladolid', 'Xocchel', 'Yaxcabá',
    'Yaxkukul', 'Yobaín')


def _hoy():
    return datetime.now(ZoneInfo('America/Merida')).date()


def _fecha(valor):
    return valor.isoformat() if valor else None


def _dinero(valor):
    return f'{valor:.2f}'


def _texto(valor, maximo, campo, *, requerido=True, multilinea=False):
    return v.texto_libre(valor, campo, maximo=maximo, requerido=requerido, multilinea=multilinea)


def _importe(valor, campo):
    """Dinero: decimal con hasta 2 decimales y ≥ 0 (solo dígitos ASCII)."""
    return v.dinero(valor, campo)


def _dia(valor, *, requerido=True):
    if valor is None or valor == '':
        if requerido:
            raise ValidationError('Fecha requerida')
        return None
    if not isinstance(valor, str) or len(valor) != 10:
        raise ValidationError('Fecha no válida')
    return date.fromisoformat(valor)


def _dto(venta):
    entregada = venta.entregada_en is not None
    return {'id': str(venta.pk), 'device': {'id': str(venta.dispositivo_id), 'identifier': venta.dispositivo.identificador},
            'buyer': venta.comprador_nombre, 'email': venta.comprador_correo, 'accountLinked': venta.comprador_usuario_id is not None,
            'municipality': venta.municipio, 'price': _dinero(venta.precio_mxn), 'received': _dinero(venta.importe_recibido_mxn),
            'reference': venta.referencia_pago or None, 'payment': venta.estado_pago, 'delivery': 'entregada' if entregada else 'por_entregar',
            'method': venta.modalidad_entrega, 'plannedDelivery': _fecha(venta.entrega_prevista_en), 'deliveredAt': _fecha(venta.entregada_en),
            'soldAt': _fecha(venta.vendida_en), 'state': venta.estado, 'cancelledAt': _fecha(venta.cancelada_en), 'note': venta.nota or None}


def _filtradas(desde, hasta, pago, entrega, municipio, busqueda, estado):
    if pago not in (None, *PAGOS) or entrega not in (None, *ENTREGAS) or estado not in (None, *ESTADOS) or municipio not in (None, *MUNICIPIOS_YUCATAN):
        raise ValidationError('Filtro no válido')
    desde, hasta = _dia(desde, requerido=False), _dia(hasta, requerido=False)
    if desde and hasta and desde > hasta:
        raise ValidationError('Rango de fechas no válido')
    busqueda = _texto(busqueda, 60, 'busqueda', requerido=False)
    consulta = Venta.objects.select_related('dispositivo')
    for campo, valor in (('vendida_en__gte', desde), ('vendida_en__lte', hasta), ('estado_pago', pago), ('municipio', municipio), ('estado', estado)):
        if valor:
            consulta = consulta.filter(**{campo: valor})
    if entrega:
        consulta = consulta.filter(entregada_en__isnull=entrega == 'por_entregar')
    if busqueda:
        consulta = consulta.filter(Q(comprador_nombre__icontains=busqueda) | Q(comprador_correo__icontains=busqueda) | Q(dispositivo__identificador__icontains=busqueda))
    return consulta


def listar(actor, desde, hasta, pago, entrega, municipio, busqueda, estado, pagina):
    s.require_cap(actor, CAPACIDAD)
    consulta = _filtradas(desde, hasta, pago, entrega, municipio, busqueda, estado).order_by('-vendida_en', '-registrada_en')
    vendibles = (Dispositivo.objects.exclude(estado='retirado').exclude(pk__in=Venta.objects.filter(estado='vigente').values('dispositivo_id'))
                 .order_by('identificador')[:MAXIMO_EQUIPOS_VENDIBLES])
    return {'status': 'ready', 'municipalities': list(MUNICIPIOS_YUCATAN),
            'sellable': [{'id': str(equipo.pk), 'identifier': equipo.identificador} for equipo in vendibles], **paginar(consulta, pagina, _dto)}


@transaction.atomic
def registrar(actor, datos):
    usuario = s.require_cap(actor, CAPACIDAD)
    nombre = v.nombre_persona(datos.get('buyer'), 'buyer')
    correo = _texto(datos.get('email'), 254, 'email')
    if not CORREO.match(correo):
        raise v.CampoInvalido('email', 'correo-no-valido', 'Escribe un correo como nombre@dominio.com.')
    if datos.get('municipality') not in MUNICIPIOS_YUCATAN or datos.get('method') not in MODALIDADES:
        raise ValidationError('Datos de la venta no válidos')
    precio, recibido = _importe(datos.get('price'), 'price'), _importe(datos.get('received', '0'), 'received')
    vendida, prevista = _dia(datos.get('soldAt')), _dia(datos.get('plannedDelivery'), requerido=False)
    if not 0 < precio <= PRECIO_MAXIMO or recibido > precio or vendida > _hoy() or (prevista and prevista < vendida):
        raise ValidationError('Importes o fechas no válidos')
    equipo = Dispositivo.objects.select_for_update().filter(pk=datos.get('device') if isinstance(datos.get('device'), str) and datos['device'].isdigit() else None).first()
    if equipo is None or equipo.estado == 'retirado':
        raise ValidationError('Equipo no válido')
    if Venta.objects.filter(dispositivo_id=equipo.pk, estado='vigente').exists():
        raise ReglaDeNegocio('equipo-vendido', 'Ese equipo ya tiene una venta vigente.')
    cuenta = get_user_model().objects.filter(email__iexact=correo, is_active=True).first()
    venta = Venta.objects.create(dispositivo=equipo, comprador_nombre=nombre, comprador_correo=correo, comprador_usuario=cuenta,
                                 municipio=datos['municipality'], precio_mxn=precio, importe_recibido_mxn=recibido,
                                 referencia_pago=_texto(datos.get('reference'), 120, 'reference', requerido=False), modalidad_entrega=datos['method'],
                                 vendida_en=vendida, entrega_prevista_en=prevista, nota=_texto(datos.get('note'), 500, 'note', requerido=False, multilinea=True),
                                 registrada_por=usuario)
    s.auditar(usuario, 'registrar_venta', entidad='venta', entidad_id=venta.pk)
    return {'status': 'accepted', 'sale': _dto(Venta.objects.select_related('dispositivo').get(pk=venta.pk))}


def _venta(venta_id):
    venta = Venta.objects.select_for_update().select_related('dispositivo').filter(pk=venta_id).first()
    if venta is None:
        raise Http404
    if venta.estado != 'vigente':
        raise ReglaDeNegocio('venta-cancelada', 'Esta venta está cancelada y ya no cambia.')
    return venta


@transaction.atomic
def registrar_pago(actor, venta_id, importe, referencia):
    usuario = s.require_cap(actor, CAPACIDAD)
    venta, nuevo = _venta(venta_id), _importe(importe, 'received')
    if nuevo < venta.importe_recibido_mxn or nuevo > venta.precio_mxn:
        raise ReglaDeNegocio('importe-no-valido', 'El importe recibido no puede bajar ni superar el precio.')
    venta.importe_recibido_mxn = nuevo
    venta.referencia_pago = _texto(referencia, 120, 'reference', requerido=False) or venta.referencia_pago
    venta.save(update_fields=['importe_recibido_mxn', 'referencia_pago'])
    s.auditar(usuario, 'registrar_pago', entidad='venta', entidad_id=venta.pk)
    return {'status': 'accepted', 'sale': _dto(Venta.objects.select_related('dispositivo').get(pk=venta.pk))}


@transaction.atomic
def entregar(actor, venta_id, fecha):
    usuario = s.require_cap(actor, CAPACIDAD)
    venta, dia = _venta(venta_id), _dia(fecha)
    if venta.entregada_en is not None:
        raise ReglaDeNegocio('venta-entregada', 'Esta venta ya se marcó como entregada.')
    if dia < venta.vendida_en or dia > _hoy():
        raise ReglaDeNegocio('fecha-no-valida', 'La entrega debe caer entre la fecha de venta y hoy.')
    venta.entregada_en = dia
    venta.save(update_fields=['entregada_en'])
    s.auditar(usuario, 'entregar_venta', entidad='venta', entidad_id=venta.pk)
    return {'status': 'accepted', 'sale': _dto(Venta.objects.select_related('dispositivo').get(pk=venta.pk))}


@transaction.atomic
def editar_nota(actor, venta_id, nota):
    usuario = s.require_cap(actor, CAPACIDAD)
    venta = _venta(venta_id)
    venta.nota = _texto(nota, 500, 'note', requerido=False, multilinea=True)
    venta.save(update_fields=['nota'])
    s.auditar(usuario, 'editar_nota_venta', entidad='venta', entidad_id=venta.pk)
    return {'status': 'accepted', 'sale': _dto(Venta.objects.select_related('dispositivo').get(pk=venta.pk))}


@transaction.atomic
def cancelar(actor, venta_id):
    usuario = s.require_cap(actor, CAPACIDAD)
    venta = _venta(venta_id)
    venta.estado = 'cancelada'
    venta.save(update_fields=['estado'])
    s.auditar(usuario, 'cancelar_venta', entidad='venta', entidad_id=venta.pk)
    return {'status': 'accepted', 'sale': _dto(Venta.objects.select_related('dispositivo').get(pk=venta.pk))}


def resumen(actor, desde, hasta):
    s.require_cap(actor, CAPACIDAD)
    desde, hasta = _dia(desde, requerido=False), _dia(hasta, requerido=False)
    if desde and hasta and desde > hasta:
        raise ValidationError('Rango de fechas no válido')
    vigentes = Venta.objects.filter(estado='vigente')
    if desde:
        vigentes = vigentes.filter(vendida_en__gte=desde)
    if hasta:
        vigentes = vigentes.filter(vendida_en__lte=hasta)
    cero = Decimal('0')
    totales = vigentes.aggregate(n=Count('id'), vendido=Sum('precio_mxn'), cobrado=Sum('importe_recibido_mxn'))
    por_municipio = vigentes.values('municipio').annotate(n=Count('id'), vendido=Sum('precio_mxn'), cobrado=Sum('importe_recibido_mxn')).order_by('-vendido', 'municipio')
    fila = lambda n, vendido, cobrado: {'sales': n, 'sold': _dinero(vendido or cero), 'collected': _dinero(cobrado or cero), 'pending': _dinero((vendido or cero) - (cobrado or cero))}
    return {'status': 'ready', **fila(totales['n'], totales['vendido'], totales['cobrado']),
            'byMunicipality': [{'municipality': item['municipio'], **fila(item['n'], item['vendido'], item['cobrado'])} for item in por_municipio]}
