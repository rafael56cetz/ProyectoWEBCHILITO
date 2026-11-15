"""Frontera de persistencia de confianza (no es una API HTTP): se llama con el `request.user` ya autenticado.

Los ID del navegador solo identifican recursos; el actor y el rol nunca se toman de lo que envía el cliente."""
import logging
from datetime import timedelta

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, connection, transaction
from django.db.models import Count
from django.db.models.functions import Now
from django.http import Http404
from django.utils import timezone

from huerto.models import Huerto
from web.respuestas import ReglaDeNegocio

from . import avisos_correo
from .models import (Auditoria, Autodiagnostico, AutodiagnosticoRevision, Comando, ConsultaProducto, Dispositivo, DispositivoEvento,
                     Medicion, MedicionPlanta, Notificacion, SoporteCaso, SoporteSesion)
from .paginacion import paginar

logger = logging.getLogger(__name__)

CAPS = {'ver_flota', 'atender_soporte', 'gestionar_mantenimientos', 'atender_consultas', 'gestionar_dispositivos',
        'gestionar_ventas', 'gestionar_guias', 'gestionar_legales', 'ver_consentimientos', 'gestionar_administradores'}
ESTADOS_CONSULTA = {'nueva', 'atendida', 'archivada'}
INCIDENTES = ('bomba', 'humedad', 'lampara', 'conexion', 'otro')
CASOS_ACTIVOS = ('abierto', 'en_atencion')
HISTORIAL_CASOS = 20
ESTADOS_BANDEJA = ('abierto', 'en_atencion', 'resuelto')
RESULTADOS_SOPORTE = ('solucionado', 'sin_falla', 'sin_respuesta', 'otro')
# Órdenes que soporte puede dar dentro de una sesión técnica; `probar_bomba` pide planta y de 1 a 5 s.
ACCIONES_SOPORTE = ('lectura_inmediata', 'autodiagnostico', 'probar_bomba', 'lampara_apagar', 'lampara_automatico',
                    'ventilador_encender', 'ventilador_apagar', 'reiniciar')
SEGUNDOS_PRUEBA_BOMBA = (1, 5)
EVENTOS_DE_SESION = timedelta(hours=24)
MAXIMO_LISTA_SESION = 50
# La base anonimiza a los 15 días de la solicitud; aquí solo se usa para mostrar la fecha.
DIAS_PARA_ELIMINAR = 15
# Orden de las revisiones del autodiagnóstico en pantalla (3.7).
COMPONENTES = ('conexion', 'sensor_ambiente', 'sensor_luz', 'sensor_sustrato_1', 'sensor_sustrato_2', 'sensor_sustrato_3',
               'flotador', 'bomba_1', 'bomba_2', 'bomba_3', 'lampara', 'ventilador')
FILTROS_AVISOS = {'todos': None, 'no_leidos': None, 'equipo': ('dispositivo', 'vinculacion'), 'ia': ('ia',),
                  'soporte': ('soporte',), 'legales': ('legal',)}


class FactorRequerido(PermissionDenied):
    """Administrador sin TOTP ni WebAuthn: puede entrar a su cuenta, no al panel."""


class RegistroDesactualizado(Exception):
    """Otra persona revisó el registro después de que este editor lo consultara."""


def identity(actor):
    if not getattr(actor, 'is_authenticated', False) or not getattr(actor, 'pk', None):
        raise PermissionDenied('Sesión requerida')
    user = get_user_model().objects.get(pk=actor.pk)
    if not user.is_active or not EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists():
        raise PermissionDenied('Cuenta activa y verificada requerida')
    return user


def capabilities(actor):
    user = identity(actor)
    # Solo concesiones explícitas de la cuenta: el acceso implícito de superusuario de Django no se usa.
    return set(Permission.objects.filter(user=user, content_type__app_label='cuentas', codename__in=CAPS)
               .values_list('codename', flat=True))


def strong_factor(user):
    return Authenticator.objects.filter(user=user, type__in=[Authenticator.Type.TOTP, Authenticator.Type.WEBAUTHN]).exists()


def require_cap(actor, cap):
    user = identity(actor)
    if cap not in capabilities(user):
        raise PermissionDenied('Capacidad requerida')
    if not strong_factor(user):
        raise FactorRequerido('Segundo factor requerido')
    return user


def session_contract(actor):
    user = identity(actor)
    caps = sorted(capabilities(user))
    return {'status': 'authenticated', 'sessionConfirmed': True, 'role': 'admin' if caps else 'user',
            'capabilities': caps, 'mfaRequired': bool(caps) and not strong_factor(user),
            'deletionRequestedAt': user.anonimizacion_solicitada_en.isoformat() if user.anonimizacion_solicitada_en else None,
            'deletionDate': (user.anonimizacion_solicitada_en + timedelta(days=DIAS_PARA_ELIMINAR)).isoformat() if user.anonimizacion_solicitada_en else None,
            'profile': {'id': str(user.pk), 'email': user.email, 'verified': True, 'status': 'ready',
                        'firstName': user.first_name, 'lastName': user.last_name, 'alias': user.alias,
                        'greeting': user.nombre_presentacion, 'welcomePending': user.bienvenida_atendida_en is None}}


def aceptaciones_pendientes(actor):
    """Textos legales vigentes que la cuenta aún no acepta. La base decide cuáles."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT tipo, documento_id, version, titulo FROM chilito_aceptaciones_pendientes(%s)', [actor.pk])
        return [{'type': tipo, 'documentId': str(documento), 'version': version, 'title': titulo}
                for tipo, documento, version, titulo in cursor.fetchall()]


def has_garden(actor):
    return Huerto.objects.filter(propietario=identity(actor), estado='activo').exists()


def huerto_propio(actor, huerto_id, *, bloquear=False):
    """Huerto activo de la cuenta. Uno ajeno, archivado o inexistente es el mismo 404."""
    consulta = Huerto.objects.select_for_update() if bloquear else Huerto.objects
    huerto = consulta.filter(pk=huerto_id, propietario_id=actor.pk, estado='activo').first()
    if huerto is None:
        raise Http404
    return huerto


def auditar(actor, accion, *, entidad='', entidad_id='', detalle=None):
    """Quién hizo qué y sobre qué. `detalle` nombra datos técnicos (p. ej. un campo), nunca valores personales."""
    return Auditoria.objects.create(actor=actor, accion=accion, entidad=entidad, entidad_id=str(entidad_id),
                                    detalle=detalle or {})


def is_admin(actor):
    # Mismo criterio que session_contract. Una cuenta sin verificar no es administradora.
    try:
        return bool(capabilities(actor))
    except (PermissionDenied, get_user_model().DoesNotExist):
        return False


# Buzón de consultas del producto. Solo con la capacidad explícita atender_consultas y segundo factor.
VENTANA_CONSULTA = timedelta(minutes=10)


@transaction.atomic
def record_inquiry(nombre, correo, mensaje):
    """Guarda la consulta. El aviso por correo y las notificaciones a administradores los crea la base.

    Repetir el mismo correo y mensaje en 10 minutos no duplica."""
    huella = avisos_correo.huella_consulta(correo, mensaje)
    reciente = (ConsultaProducto.objects.select_for_update()
                .filter(huella=huella, recibida_en__gte=timezone.now() - VENTANA_CONSULTA).first())
    if reciente:
        return reciente
    consulta = ConsultaProducto.objects.create(nombre=nombre, correo=correo, mensaje=mensaje, huella=huella)
    transaction.on_commit(lambda: avisos_correo.enviar_de_consulta(consulta))
    return consulta


def admin_inquiries(actor, estado=None):
    require_cap(actor, 'atender_consultas')
    filas = ConsultaProducto.objects.select_related('atendida_por').order_by('-recibida_en')
    if estado is not None:
        if estado not in ESTADOS_CONSULTA:
            raise ValidationError('Estado no válido')
        filas = filas.filter(estado=estado)
    return filas


@transaction.atomic
def update_inquiry(actor, inquiry_id, estado):
    """Atención de una consulta: nueva -> atendida|archivada, atendida -> archivada, archivada -> atendida.

    Nunca vuelve a «nueva». Marcarla atendida registra quién la atendió y cuándo; archivarla
    después conserva ese dato. Si se archivó sin responder, guarda quién la archivó hasta que se atienda."""
    admin = require_cap(actor, 'atender_consultas')
    consulta = ConsultaProducto.objects.select_for_update().get(pk=inquiry_id)
    permitidos = {'nueva': {'atendida', 'archivada'}, 'atendida': {'archivada'}, 'archivada': {'atendida'}}.get(consulta.estado, set())
    if estado not in permitidos:
        raise RegistroDesactualizado('Transición no válida')
    if consulta.estado == 'nueva' or estado == 'atendida':
        consulta.atendida_por, consulta.atendida_en = admin, timezone.now()
    consulta.estado = estado
    consulta.save(update_fields=['estado', 'atendida_por', 'atendida_en'])
    return consulta


def inquiry_dto(fila):
    return {'id': str(fila.pk), 'folio': fila.folio, 'receivedAt': fila.recibida_en.isoformat(),
            'name': fila.nombre, 'email': fila.correo, 'message': fila.mensaje, 'state': fila.estado,
            'attendedBy': fila.atendida_por.email if fila.atendida_por_id else None,
            'attendedAt': fila.atendida_en.isoformat() if fila.atendida_en else None,
            'notice': avisos_correo.estado_de_consulta(fila)}


# Soporte técnico sin token: la persona abre el caso y autoriza; solo ella lo revoca o lo cancela (lo exige también la base).
def _fecha(valor):
    return valor.isoformat() if valor else None


def _caso_dto(caso):
    return {'id': str(caso.pk), 'folio': caso.folio, 'incident': caso.incidente, 'note': caso.nota, 'state': caso.estado,
            'createdAt': _fecha(caso.creado_en), 'authorizedUntil': _fecha(caso.autorizacion_vence_en),
            'revokedAt': _fecha(caso.autorizacion_revocada_en), 'closedAt': _fecha(caso.cerrado_en),
            'result': caso.resultado, 'resolutionNote': caso.nota_resolucion or None,
            'diagnosticId': str(caso.autodiagnostico_id) if caso.autodiagnostico_id else None}


def _orden_de_soporte_dto(comando):
    return {'id': str(comando.pk), 'type': comando.tipo, 'plant': comando.planta_numero, 'duration': comando.duracion_s,
            'state': comando.estado, 'createdAt': _fecha(comando.creado_en), 'error': comando.detalle_error or None}


def _revision_dto(revision):
    return {'component': revision.componente, 'result': revision.resultado, 'detail': revision.detalle or None}


def autodiagnostico_dto(diagnostico):
    orden = {componente: indice for indice, componente in enumerate(COMPONENTES)}
    revisiones = sorted(AutodiagnosticoRevision.objects.filter(autodiagnostico_id=diagnostico.pk),
                        key=lambda revision: orden.get(revision.componente, len(orden)))
    return {'id': str(diagnostico.pk), 'state': diagnostico.estado, 'overall': diagnostico.resultado_general,
            'startedAt': _fecha(diagnostico.iniciado_en), 'completedAt': _fecha(diagnostico.completado_en),
            'checks': [_revision_dto(revision) for revision in revisiones]}


def soporte(actor, huerto_id):
    huerto = huerto_propio(actor, huerto_id)
    casos = list(SoporteCaso.objects.filter(huerto_id=huerto.pk, solicitante_id=actor.pk).order_by('-creado_en')[:HISTORIAL_CASOS + 1])
    activo = next((caso for caso in casos if caso.estado in CASOS_ACTIVOS), None)
    ordenes = (Comando.objects.filter(sesion__caso_id=activo.pk, origen='soporte').order_by('-creado_en')[:50] if activo else [])
    ultimo = Autodiagnostico.objects.filter(huerto_id=huerto.pk, solicitado_por_id=actor.pk).order_by('-iniciado_en').first()
    return {'status': 'ready', 'hasDevice': Dispositivo.objects.filter(huerto_id=huerto.pk).exists(),
            'active': _caso_dto(activo) if activo else None,
            'history': [_caso_dto(caso) for caso in casos if caso is not activo][:HISTORIAL_CASOS],
            'orders': [_orden_de_soporte_dto(orden) for orden in ordenes],
            'lastDiagnostic': autodiagnostico_dto(ultimo) if ultimo else None}


def _nota_de_caso(nota):
    if nota is None:
        return ''
    if not isinstance(nota, str) or len(nota) > 500 or not nota.replace('\n', ' ').isprintable():
        raise ValidationError('Nota no válida')
    return nota.strip()


def _diagnostico_adjunto(actor, huerto, valor):
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ValidationError('Revisión no válida')
    diagnostico = Autodiagnostico.objects.filter(pk=valor, huerto_id=huerto.pk, solicitado_por_id=actor.pk).first()
    if diagnostico is None:
        raise ValidationError('Revisión no válida')
    return diagnostico


@transaction.atomic
def abrir_caso(actor, huerto_id, incidente, nota, diagnostico, consentimiento):
    huerto = huerto_propio(actor, huerto_id, bloquear=True)
    if incidente not in INCIDENTES or consentimiento is not True:
        raise ValidationError('Solicitud no válida')
    equipo = Dispositivo.objects.filter(huerto_id=huerto.pk).first()
    if equipo is None:
        raise ValidationError('El huerto no tiene equipo')
    caso = SoporteCaso.objects.create(huerto=huerto, dispositivo=equipo, solicitante_id=actor.pk, incidente=incidente,
                                      nota=_nota_de_caso(nota), consentimiento=True,
                                      autodiagnostico=_diagnostico_adjunto(actor, huerto, diagnostico))
    caso.refresh_from_db()
    auditar(actor, 'abrir_caso', entidad='soporte_caso', entidad_id=caso.pk, detalle={'incidente': incidente})
    return {'status': 'accepted', 'case': _caso_dto(caso)}


def _caso_propio(actor, caso_id):
    caso = SoporteCaso.objects.select_for_update().filter(pk=caso_id, solicitante_id=actor.pk).first()
    if caso is None:
        raise Http404
    if caso.estado not in CASOS_ACTIVOS:
        raise ValidationError('El caso ya está cerrado')
    return caso


@transaction.atomic
def revocar_caso(actor, caso_id):
    caso = _caso_propio(actor, caso_id)
    if caso.autorizacion_revocada_en is not None:
        raise ValidationError('El acceso ya estaba revocado')
    caso.autorizacion_revocada_en = timezone.now()
    caso.save(update_fields=['autorizacion_revocada_en'])
    auditar(actor, 'revocar_soporte', entidad='soporte_caso', entidad_id=caso.pk)
    caso.refresh_from_db()
    return {'status': 'accepted', 'case': _caso_dto(caso)}


@transaction.atomic
def cancelar_caso(actor, caso_id):
    caso = _caso_propio(actor, caso_id)
    caso.estado = 'cancelado'
    caso.save(update_fields=['estado'])
    auditar(actor, 'cancelar_caso', entidad='soporte_caso', entidad_id=caso.pk)
    caso.refresh_from_db()
    return {'status': 'accepted', 'case': _caso_dto(caso)}


def autodiagnostico(actor, diagnostico_id):
    diagnostico = Autodiagnostico.objects.filter(pk=diagnostico_id, solicitado_por_id=actor.pk).first()
    if diagnostico is None:
        raise Http404
    return {'status': 'ready', 'diagnostic': autodiagnostico_dto(diagnostico)}


# Consola remota (`atender_soporte`). Atiende quien toma el caso, y solo esa cuenta se conecta, da órdenes y lo resuelve.
# Cada acción vuelve a leer la autorización: si la persona la revocó o venció, la siguiente orden falla.
CAPACIDAD_SOPORTE = 'atender_soporte'


def _autorizacion(caso):
    if caso.autorizacion_revocada_en is not None:
        return 'revocada'
    return 'vencida' if timezone.now() >= caso.autorizacion_vence_en else 'vigente'


def _nombre_de_persona(usuario):
    return f'{usuario.first_name} {usuario.last_name}'.strip() or usuario.alias or None


def _caso_admin_dto(caso, admin):
    return {'id': str(caso.pk), 'folio': caso.folio, 'incident': caso.incidente, 'state': caso.estado, 'createdAt': _fecha(caso.creado_en),
            'person': _nombre_de_persona(caso.solicitante), 'email': caso.solicitante.email,
            'garden': caso.huerto.nombre, 'device': caso.dispositivo.identificador, 'note': caso.nota or None,
            'authorization': _autorizacion(caso), 'authorizedUntil': _fecha(caso.autorizacion_vence_en),
            'revokedAt': _fecha(caso.autorizacion_revocada_en), 'attendedBy': caso.atendido_por.email if caso.atendido_por_id else None,
            'mine': caso.atendido_por_id == admin.pk, 'result': caso.resultado, 'resolutionNote': caso.nota_resolucion or None,
            'closedAt': _fecha(caso.cerrado_en)}


def _casos_admin():
    return SoporteCaso.objects.select_related('solicitante', 'huerto', 'dispositivo', 'atendido_por')


def _caso_de_soporte(caso_id, *, bloquear=False):
    consulta = _casos_admin()
    # FOR UPDATE no admite el LEFT JOIN de `atendido_por`: se bloquea solo la fila del caso.
    caso = consulta.select_for_update(of=('self',)).filter(pk=caso_id).first() if bloquear else consulta.filter(pk=caso_id).first()
    if caso is None:
        raise Http404
    return caso


def _caso_propio_en_atencion(admin, caso):
    if caso.estado != 'en_atencion' or caso.atendido_por_id != admin.pk:
        raise ReglaDeNegocio('caso-no-tuyo', 'Solo quien atiende el caso puede conectarse, dar órdenes o resolverlo.')


def bandeja_soporte(actor, estado, pagina):
    admin = require_cap(actor, CAPACIDAD_SOPORTE)
    if estado not in ESTADOS_BANDEJA:
        raise ValidationError('Estado no válido')
    orden = '-cerrado_en' if estado == 'resuelto' else 'autorizacion_vence_en'
    conteo = {fila['estado']: fila['n'] for fila in SoporteCaso.objects.values('estado').annotate(n=Count('id'))}
    return {'status': 'ready', 'counts': {nombre: conteo.get(nombre, 0) for nombre in ESTADOS_BANDEJA},
            **paginar(_casos_admin().filter(estado=estado).order_by(orden, 'id'), pagina, lambda caso: _caso_admin_dto(caso, admin))}


def _sesion_abierta_del_caso(admin, caso):
    return SoporteSesion.objects.filter(caso_id=caso.pk, administrador_id=admin.pk, cerrada_en__isnull=True).first()


def _sesion_dto(sesion):
    return {'id': str(sesion.pk), 'startedAt': _fecha(sesion.iniciada_en)}


def detalle_soporte(actor, caso_id):
    admin = require_cap(actor, CAPACIDAD_SOPORTE)
    caso = _caso_de_soporte(caso_id)
    sesion = _sesion_abierta_del_caso(admin, caso)
    adjunto = Autodiagnostico.objects.filter(pk=caso.autodiagnostico_id).first() if caso.autodiagnostico_id else None
    return {'status': 'ready', 'case': _caso_admin_dto(caso, admin), 'diagnostic': autodiagnostico_dto(adjunto) if adjunto else None,
            'session': _sesion_dto(sesion) if sesion else None}


@transaction.atomic
def atender_caso(actor, caso_id):
    admin = require_cap(actor, CAPACIDAD_SOPORTE)
    caso = _caso_de_soporte(caso_id, bloquear=True)
    if caso.estado != 'abierto':
        raise ReglaDeNegocio('caso-ya-atendido', 'Este caso ya lo atiende otra persona o ya está cerrado.')
    caso.estado, caso.atendido_por = 'en_atencion', admin
    caso.save(update_fields=['estado', 'atendido_por'])
    auditar(admin, 'atender_caso', entidad='soporte_caso', entidad_id=caso.pk)
    return {'status': 'accepted', 'case': _caso_admin_dto(_caso_de_soporte(caso_id), admin)}


@transaction.atomic
def conectar_caso(actor, caso_id):
    admin = require_cap(actor, CAPACIDAD_SOPORTE)
    caso = _caso_de_soporte(caso_id, bloquear=True)
    _caso_propio_en_atencion(admin, caso)
    existente = _sesion_abierta_del_caso(admin, caso)
    if existente:
        return {'status': 'accepted', 'session': _sesion_dto(existente)}
    if _autorizacion(caso) != 'vigente':
        raise ReglaDeNegocio('autorizacion-no-vigente', 'La persona ya no autoriza el acceso o la autorización venció.')
    if SoporteSesion.objects.filter(administrador_id=admin.pk, cerrada_en__isnull=True).exists():
        raise ReglaDeNegocio('sesion-abierta', 'Ya tienes una sesión técnica abierta en otro caso. Ciérrala antes de conectarte.')
    sesion = SoporteSesion.objects.create(caso=caso, administrador=admin)
    sesion.refresh_from_db()
    auditar(admin, 'conectar_sesion', entidad='soporte_sesion', entidad_id=sesion.pk)
    return {'status': 'accepted', 'session': _sesion_dto(sesion)}


def _sesion_propia(admin, sesion_id, *, bloquear=False):
    consulta = SoporteSesion.objects.select_for_update() if bloquear else SoporteSesion.objects
    sesion = consulta.filter(pk=sesion_id, administrador_id=admin.pk).first()
    if sesion is None:
        raise Http404
    return sesion


def _lecturas_actuales(caso):
    medicion = Medicion.objects.filter(dispositivo_id=caso.dispositivo_id).order_by('-medida_en').first()
    if medicion is None:
        return None
    plantas = MedicionPlanta.objects.filter(medicion_id=medicion.pk).order_by('planta_numero')
    numero = lambda valor: None if valor is None else float(valor)
    return {'measuredAt': _fecha(medicion.medida_en), 'temperature': numero(medicion.temperatura_c),
            'airHumidity': numero(medicion.humedad_aire_pct), 'light': numero(medicion.luz_lux), 'tankHasWater': medicion.deposito_con_agua,
            'plants': [{'number': fila.planta_numero, 'moisture': numero(fila.humedad_sustrato_pct), 'adc': fila.adc_crudo} for fila in plantas]}


def _equipo_de_sesion(caso):
    equipo = Dispositivo.objects.get(pk=caso.dispositivo_id)
    ultima = Medicion.objects.filter(dispositivo_id=equipo.pk).order_by('-medida_en').values_list('medida_en', flat=True).first()
    return {'identifier': equipo.identificador, 'connection': equipo.conexion, 'firmware': equipo.firmware_version or None,
            'lastConnectionAt': _fecha(equipo.ultima_conexion_en), 'lastReadingAt': _fecha(ultima)}


def _motivo_de_cierre(sesion, caso):
    if sesion.cerrada_en is not None:
        return sesion.motivo_cierre
    return {'revocada': 'revocada', 'vencida': 'vencida'}.get(_autorizacion(caso))


def estado_sesion(actor, sesion_id):
    """Lo que ve el administrador conectado; la pantalla lo consulta cada 10 s para enterarse de una revocación."""
    admin = require_cap(actor, CAPACIDAD_SOPORTE)
    sesion = _sesion_propia(admin, sesion_id)
    caso = SoporteCaso.objects.get(pk=sesion.caso_id)
    motivo = _motivo_de_cierre(sesion, caso)
    resumen = {'id': str(sesion.pk), 'state': 'closed' if motivo else 'open', 'reason': motivo or None,
               'startedAt': _fecha(sesion.iniciada_en), 'closedAt': _fecha(sesion.cerrada_en)}
    if motivo:
        return {'status': 'ready', 'session': resumen}
    eventos = DispositivoEvento.objects.filter(dispositivo_id=caso.dispositivo_id, ocurrido_en__gte=timezone.now() - EVENTOS_DE_SESION)
    ordenes = Comando.objects.filter(sesion_id=sesion.pk).order_by('-creado_en')[:MAXIMO_LISTA_SESION]
    diagnostico = Autodiagnostico.objects.filter(comando__sesion_id=sesion.pk).order_by('-iniciado_en').first()
    return {'status': 'ready', 'session': resumen, 'device': _equipo_de_sesion(caso), 'readings': _lecturas_actuales(caso),
            'events': [{'type': evento.tipo, 'detail': evento.detalle or None, 'at': _fecha(evento.ocurrido_en)}
                       for evento in eventos.order_by('-ocurrido_en', '-id')[:MAXIMO_LISTA_SESION]],
            'orders': [_orden_de_soporte_dto(orden) for orden in ordenes],
            'diagnostic': autodiagnostico_dto(diagnostico) if diagnostico else None}


def _orden_de_soporte_valida(tipo, planta, duracion):
    if tipo not in ACCIONES_SOPORTE:
        raise ValidationError('Orden no válida')
    if tipo == 'probar_bomba':
        minimo, maximo = SEGUNDOS_PRUEBA_BOMBA
        if type(planta) is not int or not 1 <= planta <= 3 or type(duracion) is not int or not minimo <= duracion <= maximo:
            raise ValidationError('Planta o duración no válidas')
    elif planta is not None or duracion is not None:
        raise ValidationError('Datos que sobran')


@transaction.atomic
def dar_orden(actor, sesion_id, tipo, planta, duracion):
    admin = require_cap(actor, CAPACIDAD_SOPORTE)
    _orden_de_soporte_valida(tipo, planta, duracion)
    sesion = _sesion_propia(admin, sesion_id, bloquear=True)
    caso = SoporteCaso.objects.get(pk=sesion.caso_id)
    if sesion.cerrada_en is not None or _autorizacion(caso) != 'vigente':
        raise ReglaDeNegocio('sesion-cerrada', 'La sesión técnica ya se cerró o la persona retiró su autorización.')
    _caso_propio_en_atencion(admin, caso)
    orden = Comando.objects.create(huerto_id=caso.huerto_id, dispositivo_id=caso.dispositivo_id, tipo=tipo, planta_numero=planta,
                                   duracion_s=duracion, origen='soporte', solicitado_por=admin, sesion=sesion)
    orden.refresh_from_db()
    auditar(admin, 'crear_comando', entidad='comando', entidad_id=orden.pk, detalle={'tipo': tipo, 'origen': 'soporte'})
    return {'status': 'accepted', 'order': _orden_de_soporte_dto(orden)}


def _cerrar_sesion(sesion, actor, motivo):
    sesion.cerrada_en, sesion.motivo_cierre = timezone.now(), motivo
    sesion.save(update_fields=['cerrada_en', 'motivo_cierre'])
    auditar(actor, 'cerrar_sesion_tecnica', entidad='soporte_sesion', entidad_id=sesion.pk, detalle={'motivo': motivo})


@transaction.atomic
def cerrar_sesion_tecnica(actor, sesion_id):
    admin = require_cap(actor, CAPACIDAD_SOPORTE)
    sesion = _sesion_propia(admin, sesion_id, bloquear=True)
    # Cerrar una sesión que la base ya cerró (revocación) no es un error: la pantalla lo hace al salir.
    if sesion.cerrada_en is None:
        _cerrar_sesion(sesion, admin, 'manual')
    return {'status': 'accepted'}


def cerrar_sesion_tecnica_al_salir(sender, user=None, **kwargs):
    """Al cerrar la sesión de la cuenta (a mano o por vencimiento) termina su sesión técnica. Que falle no impide salir."""
    if user is None or not getattr(user, 'pk', None):
        return
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # El vencimiento por inactividad ocurre antes del middleware que fija el actor.
            cursor.execute("SELECT set_config('chilito.actor_id', %s, true)", [str(user.pk)])
            sesion = SoporteSesion.objects.select_for_update().filter(administrador_id=user.pk, cerrada_en__isnull=True).first()
            if sesion:
                _cerrar_sesion(sesion, user, 'cierre_sesion')
    except DatabaseError:
        logger.exception('sesion-tecnica-sin-cerrar')


@transaction.atomic
def resolver_caso(actor, caso_id, resultado, nota):
    admin = require_cap(actor, CAPACIDAD_SOPORTE)
    if resultado not in RESULTADOS_SOPORTE:
        raise ValidationError('Resultado no válido')
    nota = _nota_de_caso(nota)
    if resultado == 'otro' and not nota:
        raise ValidationError('La nota es obligatoria con «Otro»')
    caso = _caso_de_soporte(caso_id, bloquear=True)
    _caso_propio_en_atencion(admin, caso)
    caso.estado, caso.resultado, caso.nota_resolucion = 'resuelto', resultado, nota
    caso.save(update_fields=['estado', 'resultado', 'nota_resolucion'])
    auditar(admin, 'resolver_caso', entidad='soporte_caso', entidad_id=caso.pk, detalle={'resultado': resultado})
    return {'status': 'accepted', 'case': _caso_admin_dto(_caso_de_soporte(caso_id), admin)}


# Avisos: la misma tabla sirve a personas y administradores; cada quien ve solo los suyos.
def _aviso_dto(aviso):
    return {'id': str(aviso.pk), 'origin': aviso.origen, 'severity': aviso.severidad, 'title': aviso.titulo, 'text': aviso.texto,
            'garden': aviso.huerto.nombre if aviso.huerto_id else None, 'gardenId': str(aviso.huerto_id) if aviso.huerto_id else None,
            'link': aviso.enlace or None, 'createdAt': _fecha(aviso.creada_en), 'read': aviso.leida_en is not None,
            'resolvedAt': _fecha(aviso.resuelta_en),
            'resolvable': aviso.origen == 'dispositivo' and aviso.severidad == 'critico' and aviso.resuelta_en is None}


def _mis_avisos(actor):
    return Notificacion.objects.filter(destinatario_id=actor.pk)


def avisos(actor, filtro, pagina):
    if filtro not in FILTROS_AVISOS:
        raise ValidationError('Filtro no válido')
    consulta = _mis_avisos(actor).select_related('huerto').order_by('-creada_en', '-id')
    if filtro == 'no_leidos':
        consulta = consulta.filter(leida_en__isnull=True)
    elif FILTROS_AVISOS[filtro]:
        consulta = consulta.filter(origen__in=FILTROS_AVISOS[filtro])
    return {'status': 'ready', **paginar(consulta, pagina, _aviso_dto)}


def _aviso(actor, aviso_id):
    aviso = _mis_avisos(actor).select_related('huerto').filter(pk=aviso_id).first()
    if aviso is None:
        raise Http404
    return aviso


def aviso(actor, aviso_id):
    return {'status': 'ready', 'notice': _aviso_dto(_aviso(actor, aviso_id))}


@transaction.atomic
def marcar_leido(actor, aviso_id):
    _aviso(actor, aviso_id)
    # Now() es la hora de la base: la regla exige que no sea anterior a la creación del aviso.
    _mis_avisos(actor).filter(pk=aviso_id, leida_en__isnull=True).update(leida_en=Now())
    return {'status': 'accepted', 'notice': _aviso_dto(_aviso(actor, aviso_id))}


@transaction.atomic
def marcar_resuelto(actor, aviso_id):
    actual = _aviso(actor, aviso_id)
    if not _aviso_dto(actual)['resolvable']:
        raise ValidationError('Este aviso no se resuelve aquí')
    _mis_avisos(actor).filter(pk=aviso_id).update(resuelta_en=Now(), leida_en=Now() if actual.leida_en is None else actual.leida_en)
    return {'status': 'accepted', 'notice': _aviso_dto(_aviso(actor, aviso_id))}


@transaction.atomic
def leer_todos(actor):
    cuantos = _mis_avisos(actor).filter(leida_en__isnull=True).update(leida_en=Now())
    return {'status': 'accepted', 'updated': cuantos}


def contador_avisos(actor):
    return {'status': 'ready', 'unread': _mis_avisos(actor).filter(leida_en__isnull=True).count()}
