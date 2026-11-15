"""Vinculación de huertos: emitir, revocar y consumir códigos de un solo uso. Lógica y autorización.

Reglas (aprobadas por el propietario el 2026-11-08):
- Código de 26 caracteres Base32 de Crockford (130 bits), generado con `secrets`. Solo se guarda su resumen
  con el algoritmo de contraseñas de Django; el código en claro existe únicamente en memoria.
- Vigencia única de 10 minutos. Cinco intentos por código y diez rechazos por cuenta en una hora.
- Un código pendiente por cuenta y por huerto; emitir otro reemplaza el anterior.
- Una cuenta, un huerto activo. No se transfieren ni reactivan membresías.
- Operador: capacidad explícita `vincular_huertos` y TOTP o WebAuthn usados hace 5 minutos o menos.
- Por correo solo tras una emisión presencial del mismo huerto y cuenta, al correo principal verificado.

Los rechazos y límites no lanzan excepciones: devuelven un estado para que el intento y su auditoría
se confirmen con la transacción. Solo los errores inesperados deshacen la operación.
"""
import logging
import re
import secrets
import time
from datetime import timedelta
from smtplib import (SMTPAuthenticationError, SMTPConnectError, SMTPDataError, SMTPHeloError,
                     SMTPNotSupportedError, SMTPRecipientsRefused, SMTPSenderRefused)

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMessage
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from cuentas.email import MailUnavailable, delivery_problem
from huerto.models import Huerto, Membresia

from . import services as s
from .models import Auditoria, CodigoVinculacion, Dispositivo

logger = logging.getLogger(__name__)

ALFABETO = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'   # Base32 de Crockford: sin I, L, O ni U.
LONGITUD = 26                                   # 26 × 5 = 130 bits aleatorios.
GRUPOS = (5, 5, 5, 5, 6)
LIMITE_CUENTA = 10                              # rechazos por cuenta en una hora
VENTANA_CUENTA = 3600
REAUTENTICACION = 300                           # segundos
CODIGO_RE = re.compile(r'[0-9A-HJKMNP-TV-Z]{26}')


class ReautenticacionRequerida(PermissionDenied):
    """El operador debe confirmar TOTP o WebAuthn antes de emitir o revocar."""


# --- Código -------------------------------------------------------------------------------------
def generar_codigo():
    return ''.join(secrets.choice(ALFABETO) for _ in range(LONGITUD))


def agrupar(codigo):
    partes, inicio = [], 0
    for largo in GRUPOS:
        partes.append(codigo[inicio:inicio + largo])
        inicio += largo
    return '-'.join(partes)


def normalizar(texto):
    """Mayúsculas, sin espacios ni guiones; O cuenta como 0 e I o L como 1. None si no es un código."""
    if not isinstance(texto, str) or len(texto) > 64:
        return None
    limpio = re.sub(r'[\s\-‐-―]', '', texto).upper().translate(str.maketrans('OIL', '011'))
    return limpio if CODIGO_RE.fullmatch(limpio) else None


def folio(codigo):
    return 'VC-' + codigo.pk.hex[:8].upper()


# --- Autorización del operador ------------------------------------------------------------------
def autenticacion_reciente(user, registros, ahora=None):
    """Método y momento efectivos: un uso de TOTP o WebAuthn de esta misma cuenta en los últimos 5 minutos.
    Tener un factor registrado no basta; los códigos de recuperación tampoco cuentan."""
    ahora = time.time() if ahora is None else ahora
    for registro in registros or []:
        if not isinstance(registro, dict) or registro.get('method') != 'mfa':
            continue
        tipo, momento = registro.get('type'), registro.get('at')
        if tipo not in (Authenticator.Type.TOTP, Authenticator.Type.WEBAUTHN) or not isinstance(momento, (int, float)):
            continue
        if 0 <= ahora - momento <= REAUTENTICACION and Authenticator.objects.filter(
                pk=registro.get('id'), user=user, type=tipo).exists():
            return True
    return False


def operador(actor, registros):
    user = s.require_cap(actor, 'vincular_huertos')
    if not autenticacion_reciente(user, registros):
        raise ReautenticacionRequerida('Confirma tu segundo factor')
    return user


# --- Bloqueos -----------------------------------------------------------------------------------
def _bloquear(clave):
    """Bloqueo de transacción en PostgreSQL. Orden fijo en todo el módulo: cuenta y después huerto."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', [clave])


def _bloquear_cuenta(user_id):
    _bloquear(f'chilito-vinculacion-cuenta:{user_id}')


def _bloquear_huerto(garden_id):
    _bloquear(f'chilito-vinculacion-huerto:{garden_id}')


# --- Emisión, revocación y listado (operador) ----------------------------------------------------
def _cuenta_elegible(email):
    if not isinstance(email, str) or not email.strip() or len(email) > 254:
        return None
    user = get_user_model().objects.filter(email__iexact=email.strip()).first()
    if not user or not user.is_active:
        return None
    verificado = EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists()
    return user if verificado else None


def _cerrar(codigo, estado, ahora):
    codigo.estado, codigo.cerrado_en = estado, ahora
    codigo.save(update_fields=['estado', 'cerrado_en'])


@transaction.atomic
def emitir(actor, registros, garden_id, email, entrega):
    """Devuelve {'status':'issued', ...} o {'status':'refused','reason':...}. El código solo va en la
    respuesta de una entrega presencial; por correo lo envía el sistema después de confirmar."""
    admin = operador(actor, registros)
    if entrega not in ('presencial', 'correo'):
        return {'status': 'refused', 'reason': 'invalid-delivery'}
    garden = Huerto.objects.filter(pk=garden_id).first()
    if garden is None or not Dispositivo.objects.filter(huerto=garden).exists():
        return {'status': 'refused', 'reason': 'garden-unavailable'}
    target = _cuenta_elegible(email)
    if target is None:
        return {'status': 'refused', 'reason': 'account-not-eligible'}
    _bloquear_cuenta(target.pk)
    _bloquear_huerto(garden.pk)
    if Membresia.objects.filter(usuario=target, activa=True).exists():
        return {'status': 'refused', 'reason': 'account-has-garden'}
    if Membresia.objects.filter(huerto=garden, activa=True).exists():
        return {'status': 'refused', 'reason': 'garden-occupied'}
    if Membresia.objects.filter(usuario=target, huerto=garden).exists():
        return {'status': 'refused', 'reason': 'previous-membership'}
    if entrega == 'correo' and not CodigoVinculacion.objects.filter(
            huerto=garden, destinatario=target, entrega='presencial').exists():
        return {'status': 'refused', 'reason': 'mail-requires-in-person'}
    ahora = timezone.now()
    anteriores = CodigoVinculacion.objects.select_for_update().filter(estado='pendiente').filter(
        Q(huerto=garden) | Q(destinatario=target))
    for anterior in anteriores:
        _cerrar(anterior, 'reemplazado', ahora)
        s.audit(admin, 'binding-replaced', huerto_id=anterior.huerto_id, vinculacion=anterior)
    codigo = generar_codigo()
    fila = CodigoVinculacion.objects.create(
        huerto=garden, destinatario=target, emitido_por=admin, entrega=entrega,
        verificador=make_password(codigo), emitido_en=ahora, vence_en=ahora + CodigoVinculacion.VIGENCIA,
        envio='pendiente' if entrega == 'correo' else 'no_aplica')
    s.audit(admin, 'binding-issued', huerto=garden, vinculacion=fila)
    resultado = {'status': 'issued', 'binding': dto(fila)}
    if entrega == 'presencial':
        # Única aparición del código. `code` está en la lista que el recibo de idempotencia descarta.
        resultado['code'] = agrupar(codigo)
    else:
        # Se envía tras confirmar: ningún bloqueo de la base espera al servidor de correo.
        transaction.on_commit(lambda: _actualizar(resultado, enviar_codigo(fila.pk, codigo)))
    return resultado


def _actualizar(resultado, fila):
    if fila is not None:
        resultado['binding'] = dto(fila)


@transaction.atomic
def revocar(actor, registros, code_id):
    admin = operador(actor, registros)
    fila = CodigoVinculacion.objects.select_for_update().filter(pk=code_id).first()
    if fila is None:
        raise PermissionDenied('Código no encontrado')
    if fila.estado != 'pendiente':
        raise s.RegistroDesactualizado('El código ya está cerrado')
    _cerrar(fila, 'revocado', timezone.now())
    s.audit(admin, 'binding-revoked', huerto_id=fila.huerto_id, vinculacion=fila)
    return {'status': 'revoked', 'binding': dto(fila)}


def panel(actor):
    """Metadatos para el operador. Nunca el código ni su resumen."""
    s.require_cap(actor, 'vincular_huertos')
    ocupados = Membresia.objects.filter(activa=True).values('huerto_id')
    gardens = (Huerto.objects.filter(dispositivo__isnull=False).exclude(pk__in=ocupados)
               .select_related('dispositivo').order_by('nombre'))
    base = CodigoVinculacion.objects.select_related('huerto', 'destinatario', 'emitido_por')
    return {'status': 'ready',
            'gardens': [{'id': str(g.pk), 'name': g.nombre, 'key': g.clave, 'device': g.dispositivo.identificador}
                        for g in gardens],
            'pending': [dto(c) for c in base.filter(estado='pendiente').order_by('-emitido_en')[:50]],
            'recent': [dto(c) for c in base.exclude(estado='pendiente').order_by('-emitido_en')[:20]]}


def dto(fila):
    ahora = timezone.now()
    vencido = fila.estado == 'pendiente' and fila.vence_en <= ahora
    return {'id': str(fila.pk), 'folio': folio(fila), 'garden': fila.huerto.nombre, 'gardenKey': fila.huerto.clave,
            'account': fila.destinatario.email, 'issuedBy': fila.emitido_por.email, 'delivery': fila.entrega,
            'issuedAt': fila.emitido_en.isoformat(), 'expiresAt': fila.vence_en.isoformat(),
            'attempts': fila.intentos, 'state': 'expired' if vencido else fila.estado, 'mail': fila.envio,
            'closedAt': fila.cerrado_en.isoformat() if fila.cerrado_en else None}


# --- Envío por correo ---------------------------------------------------------------------------
RECHAZOS = (MailUnavailable, SMTPRecipientsRefused, SMTPSenderRefused, SMTPDataError, SMTPConnectError,
            SMTPAuthenticationError, SMTPHeloError, SMTPNotSupportedError)


def _mensaje(fila, codigo):
    vence = timezone.localtime(fila.vence_en)
    cuerpo = ('Este es el código para vincular tu huerto de El Chilito con tu cuenta:\n\n'
              f'    {agrupar(codigo)}\n\n'
              f'Vence a las {vence:%H:%M} ({vence:%Y-%m-%d}), diez minutos después de emitirse, y solo sirve una vez.\n\n'
              'Para usarlo: inicia sesión con esta cuenta, abre «Mi huerto» › «Vincular mi huerto», '
              'pega el código y confirma.\n'
              f'{settings.ORIGIN.rstrip("/")}/index.html#huerto\n\n'
              'Si no esperabas este correo, no hagas nada: el código vencerá solo. '
              'Nadie del equipo te pedirá que se lo reenvíes.\n')
    return EmailMessage('[El Chilito] Código para vincular tu huerto', cuerpo, to=[fila.destinatario.email])


def enviar_codigo(code_id, codigo):
    """Un solo intento, fuera de cualquier transacción. Clasifica el resultado:
    aceptado_smtp (el servidor lo aceptó; no prueba que llegue al buzón), rechazado (no se envió)
    o incierto (pudo haberse entregado). Si no fue aceptado, el código se invalida."""
    fila = CodigoVinculacion.objects.select_related('destinatario').get(pk=code_id)
    resultado = 'aceptado_smtp'
    if delivery_problem(fila.destinatario.email):
        resultado = 'rechazado'
    else:
        try:
            if _mensaje(fila, codigo).send() != 1:
                resultado = 'rechazado'
        except RECHAZOS:
            resultado = 'rechazado'
        except Exception:   # tiempo agotado, desconexión, error de red: no sabemos si llegó
            resultado = 'incierto'
    with transaction.atomic():
        # Solo se bloquea la fila del código: el rol de la aplicación no puede bloquear huertos ni cuentas.
        fila = CodigoVinculacion.objects.select_for_update(of=('self',)).select_related(
            'huerto', 'destinatario', 'emitido_por').get(pk=code_id)
        fila.envio = resultado
        campos = ['envio']
        if resultado != 'aceptado_smtp' and fila.estado == 'pendiente':
            fila.estado, fila.cerrado_en = 'revocado', timezone.now()
            campos += ['estado', 'cerrado_en']
            s.audit(fila.emitido_por, 'binding-revoked', huerto_id=fila.huerto_id, vinculacion=fila)
        fila.save(update_fields=campos)
    if resultado != 'aceptado_smtp':
        logger.warning('vinculacion-envio %s %s', fila.pk, resultado)   # sin destinatario ni código
    return fila


# --- Consumo (persona usuaria) ------------------------------------------------------------------
def _rechazos_recientes(user):
    desde = timezone.now() - timedelta(seconds=VENTANA_CUENTA)
    return Auditoria.objects.filter(actor=user, accion='binding-rejected', creada_en__gte=desde).count()


def _rechazar(user, fila=None):
    s.audit(user, 'binding-rejected', huerto_id=fila.huerto_id if fila else None, vinculacion=fila)
    return {'status': 'rejected'}


@transaction.atomic
def consumir(actor, texto):
    """Estados: linked, already-linked, rejected (sin distinguir el motivo) o limited."""
    user = s.identity(actor)
    _bloquear_cuenta(user.pk)
    activa = Membresia.objects.filter(usuario=user, activa=True).first()
    if activa:
        return {'status': 'already-linked', 'membership': activa.pk, 'garden': {'name': activa.huerto.nombre}}
    # Límite antes de la comprobación costosa, también si la cuenta no tiene código pendiente.
    if _rechazos_recientes(user) >= LIMITE_CUENTA:
        s.audit(user, 'binding-limited')
        return {'status': 'limited'}
    codigo = normalizar(texto)
    # Orden de bloqueos igual que al emitir (cuenta, huerto, fila del código) para no cruzarse.
    previo = CodigoVinculacion.objects.filter(destinatario=user, estado='pendiente').values('pk', 'huerto_id').first()
    fila = None
    if previo:
        _bloquear_huerto(previo['huerto_id'])
        fila = (CodigoVinculacion.objects.select_for_update(of=('self',)).select_related('huerto')
                .filter(pk=previo['pk'], estado='pendiente').first())
    ahora = timezone.now()
    if fila is None and CodigoVinculacion.objects.filter(
            destinatario=user, estado='bloqueado', cerrado_en__gt=ahora - CodigoVinculacion.VIGENCIA).exists():
        s.audit(user, 'binding-limited')   # su último código se bloqueó por intentos: hace falta uno nuevo
        return {'status': 'limited'}
    if fila is None or fila.vence_en <= ahora:
        return _rechazar(user, fila)
    if codigo is None or not check_password(codigo, fila.verificador):
        fila.intentos += 1
        campos = ['intentos']
        if fila.intentos >= CodigoVinculacion.MAX_INTENTOS:
            fila.estado, fila.cerrado_en = 'bloqueado', ahora
            campos += ['estado', 'cerrado_en']
        fila.save(update_fields=campos)
        respuesta = _rechazar(user, fila)
        if fila.estado == 'bloqueado':
            s.audit(user, 'binding-locked', huerto_id=fila.huerto_id, vinculacion=fila)
            return {'status': 'limited'}
        return respuesta
    if (Membresia.objects.filter(huerto_id=fila.huerto_id, activa=True).exists()
            or Membresia.objects.filter(usuario=user, huerto_id=fila.huerto_id).exists()):
        return _rechazar(user, fila)
    membresia = Membresia.objects.create(usuario=user, huerto_id=fila.huerto_id)
    fila.estado, fila.cerrado_en, fila.membresia = 'consumido', ahora, membresia
    fila.save(update_fields=['estado', 'cerrado_en', 'membresia'])
    s.audit(user, 'binding-consumed', huerto_id=fila.huerto_id, vinculacion=fila)
    return {'status': 'linked', 'membership': membresia.pk, 'garden': {'name': fila.huerto.nombre}}


def comprobar_recibo(actor, recibo):
    """Repetir un recibo de vinculación no recupera una membresía que ya no está activa."""
    if recibo.get('status') in ('linked', 'already-linked') and not Membresia.objects.filter(
            pk=recibo.get('membership'), usuario=s.identity(actor), activa=True).exists():
        raise PermissionDenied('La membresía ya no está activa')
