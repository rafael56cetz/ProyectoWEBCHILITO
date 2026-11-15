"""Administradores: quién tiene qué capacidad, su historial y su actividad. Solo para `gestionar_administradores`.

Cambiar capacidades es insertar o borrar filas de permisos; la base exige el actor, el motivo (`chilito.motivo`), que nadie se
cambie las propias y que `gestionar_administradores` solo se asigne desde pgAdmin. Aquí se rechaza todo eso antes de llegar a ella."""
import re
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import connection, transaction

from web.respuestas import ReglaDeNegocio

from . import services as s
from .models import Auditoria
from .paginacion import paginar, paginar_sql

CAPACIDAD = 'gestionar_administradores'
EDITABLES = tuple(sorted(s.CAPS - {CAPACIDAD}))
MAXIMO_MOTIVO = 300
MAXIMO_BUSQUEDA = 60
ORIGEN_ADMINISTRADORES = 'v_administradores'
ORIGEN_HISTORIAL = 'v_capacidad_historial'


def _fecha(valor):
    return valor.isoformat() if valor else None


def _texto_opcional(valor, maximo):
    if valor is None or valor == '':
        return None
    if not isinstance(valor, str) or len(valor) > maximo or not valor.isprintable():
        raise ValidationError('Texto no válido')
    return valor.strip() or None


def _dia(valor):
    texto = _texto_opcional(valor, 10)
    if texto is None:
        return None
    if len(texto) != 10:
        raise ValidationError('Fecha no válida')
    return date.fromisoformat(texto)


def _like(texto):
    return '%' + re.sub(r'([\\%_])', r'\\\1', texto) + '%'


def _administrador_dto(fila):
    return {'id': str(fila['usuario_id']), 'email': fila['email'], 'name': fila['nombre'], 'superAdmin': fila['es_super_admin'],
            'capabilities': fila['capacidades'].split(', ') if fila['capacidades'] else [], 'secondFactor': fila['segundo_factor'],
            'lastAccess': _fecha(fila['ultimo_acceso'])}


def listar(actor, pagina):
    s.require_cap(actor, CAPACIDAD)
    return {'status': 'ready', 'editable': list(EDITABLES),
            **paginar_sql('usuario_id, email, nombre, es_super_admin, capacidades, segundo_factor, ultimo_acceso', ORIGEN_ADMINISTRADORES, 'email', [], pagina, _administrador_dto)}


def _historial_dto(fila):
    return {'at': _fecha(fila['realizada_en']), 'account': fila['cuenta'], 'capability': fila['capacidad'], 'action': fila['accion'],
            'by': fila['realizada_por'], 'reason': fila['motivo'] or None}


def historial(actor, cuenta, capacidad, desde, hasta, pagina):
    s.require_cap(actor, CAPACIDAD)
    cuenta, capacidad = _texto_opcional(cuenta, MAXIMO_BUSQUEDA), _texto_opcional(capacidad, 40)
    if capacidad and capacidad not in s.CAPS:
        raise ValidationError('Capacidad no válida')
    desde, hasta = _dia(desde), _dia(hasta)
    if desde and hasta and desde > hasta:
        raise ValidationError('Rango de fechas no válido')
    donde, parametros = [], []
    if cuenta:
        donde.append('cuenta ILIKE %s')
        parametros.append(_like(cuenta))
    if capacidad:
        donde.append('capacidad = %s')
        parametros.append(capacidad)
    if desde:
        donde.append("(realizada_en AT TIME ZONE 'America/Merida')::date >= %s")
        parametros.append(desde)
    if hasta:
        donde.append("(realizada_en AT TIME ZONE 'America/Merida')::date <= %s")
        parametros.append(hasta)
    origen = ORIGEN_HISTORIAL + (' WHERE ' + ' AND '.join(donde) if donde else '')
    return {'status': 'ready', **paginar_sql('realizada_en, cuenta, capacidad, accion, realizada_por, motivo', origen, 'realizada_en DESC', parametros, pagina, _historial_dto)}


def _actividad_dto(fila):
    return {'at': _fecha(fila.creada_en), 'actor': fila.actor.email if fila.actor_id else None, 'action': fila.accion,
            'entity': fila.entidad or None, 'result': fila.resultado}


def actividad(actor, cuenta, pagina):
    s.require_cap(actor, CAPACIDAD)
    cuenta = _texto_opcional(cuenta, MAXIMO_BUSQUEDA)
    consulta = Auditoria.objects.select_related('actor').order_by('-creada_en', '-id')
    if cuenta:
        consulta = consulta.filter(actor__email__iexact=cuenta)
    else:
        administradores = get_user_model().objects.filter(user_permissions__codename__in=s.CAPS).values('pk')
        consulta = consulta.filter(actor_id__in=administradores)
    return {'status': 'ready', **paginar(consulta, pagina, _actividad_dto)}


def _capacidades_pedidas(valor):
    if not isinstance(valor, list) or len(valor) > len(EDITABLES) or not all(isinstance(item, str) for item in valor):
        raise ValidationError('Capacidades no válidas')
    if CAPACIDAD in valor:
        raise ReglaDeNegocio('capacidad-reservada', 'La capacidad de super administrador solo se asigna desde la base de datos.')
    if len(set(valor)) != len(valor) or not set(valor) <= set(EDITABLES):
        raise ValidationError('Capacidades no válidas')
    return set(valor)


def _cuenta_objetivo(correo):
    if not isinstance(correo, str) or not 3 <= len(correo) <= 254 or '@' not in correo:
        raise ValidationError('Correo no válido')
    cuenta = get_user_model().objects.select_for_update().filter(email__iexact=correo.strip()).first()
    if cuenta is None:
        raise ReglaDeNegocio('cuenta-no-encontrada', 'No hay una cuenta con ese correo.')
    return cuenta


def _permisos(codigos):
    return list(Permission.objects.filter(content_type__app_label='cuentas', codename__in=codigos))


@transaction.atomic
def cambiar_capacidades(actor, correo, capacidades, motivo):
    """Deja a la cuenta con exactamente `capacidades` (de las editables). Altas y bajas van juntas, con un solo motivo."""
    administrador = s.require_cap(actor, CAPACIDAD)
    finales = _capacidades_pedidas(capacidades)
    if not isinstance(motivo, str) or not 1 <= len(motivo.strip()) <= MAXIMO_MOTIVO or not motivo.isprintable():
        raise ValidationError('Motivo no válido')
    cuenta = _cuenta_objetivo(correo)
    if cuenta.pk == administrador.pk:
        raise ReglaDeNegocio('capacidad-propia', 'No puedes cambiar tus propias capacidades.')
    actuales = set(cuenta.user_permissions.filter(content_type__app_label='cuentas', codename__in=EDITABLES).values_list('codename', flat=True))
    altas, bajas = sorted(finales - actuales), sorted(actuales - finales)
    if not altas and not bajas:
        raise ValidationError('No hay cambios')
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('chilito.motivo', %s, true)", [motivo.strip()])
    cuenta.user_permissions.add(*_permisos(altas))
    cuenta.user_permissions.remove(*_permisos(bajas))
    s.auditar(administrador, 'cambiar_capacidades', entidad='cuenta', entidad_id=cuenta.pk, detalle={'concedidas': altas, 'retiradas': bajas})
    return {'status': 'accepted', 'granted': altas, 'revoked': bajas}
