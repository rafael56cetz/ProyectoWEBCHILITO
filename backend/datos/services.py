"""Frontera de persistencia de confianza (no es una API HTTP): se llama con el `request.user` ya autenticado.

Los ID del navegador solo identifican recursos; el actor y el rol nunca se toman de lo que envía el cliente."""
from datetime import timedelta

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.utils import timezone

from huerto.models import Huerto

from . import avisos_correo
from .models import Auditoria, ConsultaProducto

CAPS = {'ver_flota', 'atender_soporte', 'gestionar_mantenimientos', 'atender_consultas', 'gestionar_dispositivos',
        'gestionar_ventas', 'gestionar_guias', 'gestionar_legales', 'ver_consentimientos', 'gestionar_administradores'}
ESTADOS_CONSULTA = {'nueva', 'atendida', 'archivada'}


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
