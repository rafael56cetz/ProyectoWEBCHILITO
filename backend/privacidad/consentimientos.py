"""Bitácora de consentimientos para quien tiene `ver_consentimientos`: solo lectura sobre `v_bitacora_consentimientos`, su resumen y la
exportación a CSV. La IP ya viene recortada de la base (V14). Lo exportado se audita y toda celda se protege contra fórmulas."""
import csv
import re
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import HttpResponse

from datos import services as s
from datos.paginacion import paginar_sql
from web.respuestas import ReglaDeNegocio

from . import politicas, services
from .models import Decision, Preferencia

CAPACIDAD = 'ver_consentimientos'
DOCUMENTOS = {'terminos': 'Términos y condiciones', 'aviso': 'Aviso de privacidad', 'cookies': 'Cookies'}
DECISIONES = {'acepto': 'Aceptó', 'rechazo': 'Rechazó'}
VERSION = re.compile(r'^[0-9]{1,3}(\.[0-9]{1,3}){1,2}$')
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
    if not isinstance(valor, str) or len(valor) != 10:
        raise ValidationError('Fecha no válida')
    return date.fromisoformat(valor)


def _like(texto):
    return '%' + re.sub(r'([\\%_])', r'\\\1', texto) + '%'


def _filtros(documento, decision, desde, hasta, cuenta, version):
    if documento not in (None, '', *DOCUMENTOS) or decision not in (None, '', *DECISIONES):
        raise ValidationError('Filtro no válido')
    if cuenta and (not isinstance(cuenta, str) or len(cuenta) > 60 or not cuenta.isprintable()):
        raise ValidationError('Búsqueda no válida')
    if version and (not isinstance(version, str) or not VERSION.match(version)):
        raise ValidationError('Versión no válida')
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
