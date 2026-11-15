"""Frontera de persistencia de confianza (no es una API HTTP): se llama con el `request.user` ya autenticado.

Los ID del navegador solo identifican recursos; el actor y el rol nunca se toman de lo que envía el cliente."""
from datetime import timedelta

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.db.models.functions import Now
from django.http import Http404
from django.utils import timezone

from huerto.models import Huerto

from . import avisos_correo
from .models import (Auditoria, Autodiagnostico, AutodiagnosticoRevision, Comando, ConsultaProducto, Dispositivo, Notificacion, SoporteCaso)
from .paginacion import paginar

CAPS = {'ver_flota', 'atender_soporte', 'gestionar_mantenimientos', 'atender_consultas', 'gestionar_dispositivos',
        'gestionar_ventas', 'gestionar_guias', 'gestionar_legales', 'ver_consentimientos', 'gestionar_administradores'}
ESTADOS_CONSULTA = {'nueva', 'atendida', 'archivada'}
INCIDENTES = ('bomba', 'humedad', 'lampara', 'conexion', 'otro')
CASOS_ACTIVOS = ('abierto', 'en_atencion')
HISTORIAL_CASOS = 20
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
