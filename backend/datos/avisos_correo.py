"""Avisos automáticos por correo: cola en PostgreSQL y envío después de confirmar la transacción.

Solo construye y envía; quién puede provocar un aviso lo decide datos.services.
Ningún aviso lleva el token de soporte: el token nunca llega a la base, así que no puede filtrarse aquí.
`aceptado_smtp` solo significa que el servidor de correo aceptó el mensaje, no que llegó a la bandeja.
"""
import logging
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from cuentas.email import MailUnavailable, delivery_problem

from .models import AvisoCorreo, CasoSoporte

logger = logging.getLogger(__name__)
MAX_INTENTOS = 5
INCIDENTES = dict(CasoSoporte.INCIDENTES)


def folio_caso(caso):
    return 'CS-' + caso.pk.hex[:8].upper()


def folio_consulta(consulta):
    return 'CP-' + consulta.pk.hex[:8].upper()


def _enlace(ruta):
    # Origen del entorno (CHILITO_ORIGIN); en producción se exige https.
    return settings.ORIGIN.rstrip('/') + '/index.html#' + ruta


def _mensaje(aviso):
    """Destinatario, asunto, cuerpo y respuesta. Los asuntos alimentan los filtros de Gmail del propietario."""
    soporte = settings.CHILITO_CONTACTO_SOPORTE
    if aviso.tipo == 'caso_nuevo':
        caso = aviso.caso
        folio = folio_caso(caso)
        cuerpo = (f'Se abrió el caso de soporte {folio}.\n'
                  f'Incidente: {INCIDENTES.get(caso.incidente, "Otro")}\n'
                  f'Fecha: {timezone.localtime(caso.creado_en):%Y-%m-%d %H:%M}\n\n'
                  f'Consúltalo en el panel: {_enlace("admin/soporte")}\n\n'
                  'Este aviso no incluye el token. La persona usuaria lo comparte por correo si decide hacerlo.\n')
        return soporte, f'[El Chilito] Nuevo caso de soporte {folio}', cuerpo, None
    if aviso.tipo == 'token_solicitado':
        caso = aviso.caso
        folio = folio_caso(caso)
        cuerpo = (f'El equipo de soporte solicita el token de tu caso {folio}.\n\n'
                  f'Si quieres que revise tu huerto, escribe a {soporte or "soporte"} con el asunto «Caso de soporte {folio}» '
                  'y pega el token en el mensaje.\n'
                  'El token solo se mostró al emitirlo. Si ya no lo tienes, revoca la autorización y genera una nueva '
                  f'desde tu panel: {_enlace("soporte")}\n\n'
                  'Nunca te pediremos tu contraseña ni tus códigos de acceso.\n')
        return caso.solicitante.email, f'[El Chilito] Soporte solicita el token del caso {folio}', cuerpo, soporte or None
    consulta = aviso.consulta
    cuerpo = (f'Consulta {folio_consulta(consulta)}\n'
              f'Nombre: {consulta.nombre or "Sin indicar"}\nCorreo: {consulta.correo}\n\n{consulta.mensaje}\n\n'
              f'Gestiónala en el panel: {_enlace("admin/solicitudes")}\n')
    return soporte, '[El Chilito] Pregunta sobre el producto', cuerpo, consulta.correo


def encolar(tipo, *, caso=None, consulta=None):
    """Registra el aviso dentro de la transacción en curso y lo envía solo si esta se confirma."""
    aviso = AvisoCorreo.objects.create(tipo=tipo, caso=caso, consulta=consulta)
    transaction.on_commit(lambda: enviar(aviso.pk))
    return aviso


def enviar(aviso_id):
    """Un intento de envío. Nunca lanza: un fallo de correo no deshace el caso ni la consulta."""
    try:
        with transaction.atomic():
            aviso = (AvisoCorreo.objects.select_for_update(skip_locked=True, of=('self',))
                     .select_related('caso__solicitante', 'consulta').filter(pk=aviso_id).first())
            if aviso is None or aviso.estado == 'aceptado_smtp' or aviso.intentos >= MAX_INTENTOS:
                return aviso
            destino, asunto, cuerpo, responder = _mensaje(aviso)
            ahora = timezone.now()
            aviso.intentos += 1
            aviso.ultimo_intento_en = ahora
            problema = None if destino else 'sin-destino'
            problema = problema or delivery_problem(destino)
            if problema is None:
                try:
                    EmailMessage(asunto, cuerpo, to=[destino], reply_to=[responder] if responder else None).send()
                except (MailUnavailable, OSError, SMTPException):
                    problema = 'smtp'
            if problema is None:
                aviso.estado, aviso.aceptado_en = 'aceptado_smtp', ahora
            else:
                aviso.estado = 'fallido'
                # Solo el código y el identificador: ni destinatario ni contenido.
                logger.warning('aviso-correo-fallido %s %s', aviso.pk, problema)
            aviso.save(update_fields=['estado', 'intentos', 'ultimo_intento_en', 'aceptado_en'])
            return aviso
    except Exception:
        logger.exception('aviso-correo-error %s', aviso_id)
        return None


def reintentar_pendientes(ahora=None):
    """Reintenta con espera creciente (2, 4, 8, 16 min). Devuelve cuántos se aceptaron."""
    ahora = ahora or timezone.now()
    aceptados = 0
    for aviso in AvisoCorreo.objects.filter(estado__in=['pendiente', 'fallido'], intentos__lt=MAX_INTENTOS).order_by('creado_en'):
        espera = timedelta(minutes=2 ** max(aviso.intentos, 1))
        if aviso.ultimo_intento_en and aviso.ultimo_intento_en > ahora - espera:
            continue
        resultado = enviar(aviso.pk)
        aceptados += bool(resultado and resultado.estado == 'aceptado_smtp')
    return aceptados
