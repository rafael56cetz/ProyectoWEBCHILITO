"""Bitácora de consentimientos para quien tiene `ver_consentimientos`: solo lectura sobre `v_bitacora_consentimientos`, su resumen, la
exportación a CSV y el padrón de cuentas (activas e inactivas, con su fecha de creación). La IP ya viene recortada de la base (V14). Lo exportado se audita y toda celda se protege contra fórmulas."""
import csv
import re
from datetime import date

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Count, Exists, OuterRef, Q
from django.http import HttpResponse

from datos import services as s
from datos.paginacion import paginar, paginar_sql
from web.respuestas import ReglaDeNegocio
from web import validacion as v

from . import politicas, services
from .models import Decision, Preferencia

CAPACIDAD = 'ver_consentimientos'
DOCUMENTOS = {'terminos': 'Términos y condiciones', 'aviso': 'Aviso de privacidad', 'cookies': 'Cookies'}
DECISIONES = {'acepto': 'Aceptó', 'rechazo': 'Rechazó'}
VERSION = re.compile(r'^[0-9]{1,3}(\.[0-9]{1,3}){1,2}$')
# Solo AAAA-MM-DD en cifras ASCII: fromisoformat también acepta otras formas (p. ej. «2026-W47-1», fecha por semana).
FECHA = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
COLUMNAS = ('registrada_en, registrada_en_merida, cuenta, ambito, que, version_documento, decision, finalidad, ip_recortada, navegador, decision_id')
ORIGEN = 'v_bitacora_consentimientos'
MAXIMO_FILAS_CSV = 50000
ENCABEZADOS = ('Fecha y hora (Mérida)', 'Cuenta', 'Ámbito', 'Qué', 'Versión', 'Decisión', 'Finalidad', 'IP', 'Navegador')
PELIGROSAS = ('=', '+', '-', '@', '\t', '\r')


def _fecha(valor):
    return valor.isoformat() if valor else None


def _dia(valor):
    if valor in (None, ''):
        return None
    if not isinstance(valor, str) or not FECHA.fullmatch(valor):
        raise ValidationError('Fecha no válida')
    return date.fromisoformat(valor)


def _like(texto):
    return '%' + re.sub(r'([\\%_])', r'\\\1', texto) + '%'


def _filtros(documento, decision, desde, hasta, cuenta, version):
    if documento not in (None, '', *DOCUMENTOS) or decision not in (None, '', *DECISIONES):
        raise ValidationError('Filtro no válido')
    cuenta = v.texto_libre(cuenta, 'cuenta', maximo=60)
    version = v.formato(version, 'version', VERSION, 'Escribe la versión como 1.2 o 1.2.3.', requerido=False)
    desde, hasta = _dia(desde), _dia(hasta)
    if desde and hasta and desde > hasta:
        raise ValidationError('Rango de fechas no válido')
    donde, parametros = [], []
    for condicion, valor in (('que = %s', DOCUMENTOS.get(documento)), ('decision = %s', DECISIONES.get(decision)), ('version_documento = %s', version or None),
                             ('cuenta ILIKE %s', _like(cuenta.strip()) if cuenta and cuenta.strip() else None),
                             ('registrada_en_merida::date >= %s', desde), ('registrada_en_merida::date <= %s', hasta)):
        if valor:
            donde.append(condicion)
            parametros.append(valor)
    return (' WHERE ' + ' AND '.join(donde)) if donde else '', parametros


def _dto(fila):
    return {'id': str(fila['decision_id']), 'at': _fecha(fila['registrada_en']), 'account': fila['cuenta'], 'scope': fila['ambito'], 'what': fila['que'],
            'version': fila['version_documento'], 'decision': fila['decision'], 'purpose': fila['finalidad'], 'ip': fila['ip_recortada'] or None,
            'browser': fila['navegador'] or None}


def bitacora(actor, documento, decision, desde, hasta, cuenta, version, pagina):
    s.require_cap(actor, CAPACIDAD)
    donde, parametros = _filtros(documento, decision, desde, hasta, cuenta, version)
    return {'status': 'ready', 'exportLimit': MAXIMO_FILAS_CSV, **paginar_sql(COLUMNAS, ORIGEN + donde, 'registrada_en DESC, decision_id DESC', parametros, pagina, _dto)}


def _aceptaciones_vigentes(tipo, acto, activas):
    vigente = services.documento_vigente(tipo)
    if vigente is None:
        return {'version': None, 'accepted': 0, 'accounts': activas.count()}
    aceptadas = Decision.objects.filter(documento=vigente, acto=acto, decision=True, usuario__in=activas).values('usuario').distinct().count()
    return {'version': vigente.version, 'accepted': aceptadas, 'accounts': activas.count()}


def resumen(actor):
    s.require_cap(actor, CAPACIDAD)
    activas = get_user_model().objects.filter(is_active=True, anonimizada_en__isnull=True)
    navegadores = Preferencia.objects.filter(finalidad__codigo=politicas.FINALIDAD_ESTADISTICAS, sujeto__ambito='navegador')
    total = navegadores.count()
    con_estadisticas = navegadores.filter(decision__decision=True).count()
    return {'status': 'ready', 'terms': _aceptaciones_vigentes('terminos', 'aceptacion_terminos', activas),
            'privacy': _aceptaciones_vigentes('aviso_privacidad', 'lectura_aviso', activas),
            'statistics': {'browsers': total, 'accepted': con_estadisticas, 'percent': round(100 * con_estadisticas / total, 1) if total else None}}


def _celda(valor):
    """Un CSV que se abre en una hoja de cálculo no debe ejecutar fórmulas: lo que empieza como una se vuelve texto."""
    texto = '' if valor is None else str(valor)
    return "'" + texto if texto.startswith(PELIGROSAS) else texto


def exportar(actor, documento, decision, desde, hasta, cuenta, version):
    usuario = s.require_cap(actor, CAPACIDAD)
    donde, parametros = _filtros(documento, decision, desde, hasta, cuenta, version)
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT count(*) FROM {ORIGEN}{donde}', parametros)
        total = cursor.fetchone()[0]
        if total > MAXIMO_FILAS_CSV:
            raise ReglaDeNegocio('exportacion-grande', f'La exportación tiene {total} filas; acota el filtro a {MAXIMO_FILAS_CSV} o menos.')
        cursor.execute(f'SELECT registrada_en_merida, cuenta, ambito, que, version_documento, decision, finalidad, ip_recortada, navegador '
                       f'FROM {ORIGEN}{donde} ORDER BY registrada_en DESC, decision_id DESC', parametros)
        filas = cursor.fetchall()
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = 'attachment; filename="consentimientos.csv"'
    respuesta.write('﻿')
    escritor = csv.writer(respuesta)
    escritor.writerow(ENCABEZADOS)
    for fila in filas:
        escritor.writerow([_celda(valor.strftime('%Y-%m-%d %H:%M:%S') if hasattr(valor, 'strftime') else valor) for valor in fila])
    s.auditar(usuario, 'exportar_consentimientos', entidad='bitacora_consentimientos', detalle={'filas': len(filas)})
    return respuesta


ESTADOS_CUENTA = ('todas', 'activas', 'inactivas')
# Solo estas columnas: nunca la contraseña (hash), el id interno ni otros datos de la cuenta.
CAMPOS_CUENTA = ('email', 'date_joined', 'last_login', 'activa', 'verificada')


def _dto_cuenta(fila):
    return {'email': fila['email'], 'status': 'activa' if fila['activa'] else 'inactiva',
            'emailVerified': fila['verificada'], 'createdAt': _fecha(fila['date_joined']), 'lastLogin': _fecha(fila['last_login'])}


def cuentas(actor, estado, busqueda, desde, hasta, pagina):
    """Padrón de cuentas. Activa = activa, sin anonimizar y con el correo verificado; inactiva = todo lo demás.

    Los totales usan la búsqueda y las fechas, pero no el estado, para que las tres pestañas cuadren entre sí."""
    s.require_cap(actor, CAPACIDAD)
    estado = estado or 'todas'
    if estado not in ESTADOS_CUENTA:
        raise ValidationError('Estado no válido')
    busqueda = v.texto_libre(busqueda, 'busqueda', maximo=254)
    desde, hasta = _dia(desde), _dia(hasta)
    if desde and hasta and desde > hasta:
        raise ValidationError('Rango de fechas no válido')
    verificada = Exists(EmailAddress.objects.filter(user_id=OuterRef('pk'), email__iexact=OuterRef('email'), verified=True))
    consulta = get_user_model().objects.annotate(verificada=verificada).annotate(
        activa=Q(is_active=True, anonimizada_en__isnull=True, verificada=True))
    if busqueda:
        consulta = consulta.filter(email__icontains=busqueda)
    if desde:
        consulta = consulta.filter(date_joined__date__gte=desde)
    if hasta:
        consulta = consulta.filter(date_joined__date__lte=hasta)
    totales = consulta.aggregate(total=Count('pk'), activas=Count('pk', filter=Q(activa=True)))
    totales['inactivas'] = totales['total'] - totales['activas']
    if estado != 'todas':
        consulta = consulta.filter(activa=estado == 'activas')
    filas = consulta.order_by('-date_joined', '-pk').values(*CAMPOS_CUENTA)
    return {'status': 'ready', 'totals': totales, **paginar(filas, pagina, _dto_cuenta)}
