from django.db import transaction
from django.core.exceptions import PermissionDenied
from allauth.account.models import EmailAddress
from huerto.models import Huerto, Zona, Membresia

@transaction.atomic
def provision_garden():
    garden, _ = Huerto.objects.get_or_create(
        clave="principal", defaults={"nombre": "Mi huerto de habanero"})
    # Serialize repeat provisioning; never overwrite existing display names.
    garden = Huerto.objects.select_for_update().get(pk=garden.pk)
    for number in (1, 2, 3):
        Zona.objects.get_or_create(
            huerto=garden, numero=number, defaults={"nombre": f"Planta {number}"})
    return garden

@transaction.atomic
def assign_membership(user, garden, *, active=True):
    membership, _ = Membresia.objects.update_or_create(
        usuario=user, huerto=garden, defaults={"activa": active})
    return membership

def visible_gardens(user):
    if not user.is_authenticated or not user.is_active:
        return Huerto.objects.none()
    if not EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists():
        return Huerto.objects.none()
    return Huerto.objects.filter(membresia__usuario=user, membresia__activa=True).distinct()

def require_garden(user, garden_id):
    try:
        return visible_gardens(user).get(pk=garden_id)
    except Huerto.DoesNotExist:
        raise PermissionDenied("No hay autorizacion para consultar el huerto.") from None

# Only the explicitly provisioned principal garden is selected by /actual.
class GardenAccessError(Exception):
    def __init__(self, code="garden-unassigned", status=403):
        self.code, self.status = code, status
        super().__init__(code)

def current_garden(user):
    try:
        return visible_gardens(user).get(clave="principal")
    except Huerto.DoesNotExist:
        raise GardenAccessError from None

def garden_projection(garden):
    zones = list(garden.zona_set.order_by("numero"))
    if [zone.numero for zone in zones] != [1, 2, 3]:
        raise GardenAccessError("garden-configuration-unavailable", 503)
    # No ingestion/reading schema is authorized yet. Missing is not zero/offline.
    def missing():
        return {"value": None, "quality": "missing", "at": None}
    return {
        "status": "waiting", "name": garden.nombre, "updatedAt": None,
        "plants": [{"id": zone.numero, "name": zone.nombre, "reading": missing()} for zone in zones],
        "temperature": missing(), "humidity": missing(), "tank": {"state": "unknown", "at": None},
    }

def notice_queryset(user, garden):
    from django.db.models import Exists, OuterRef
    from huerto.models import Aviso, AvisoLeido
    return Aviso.objects.filter(huerto=garden).select_related("zona").annotate(
        is_read=Exists(AvisoLeido.objects.filter(aviso_id=OuterRef("pk"), usuario=user))
    ).order_by("-creado_en", "-id")

def notice_projection(notice):
    return {
        "id": str(notice.pk), "title": notice.titulo, "description": notice.descripcion,
        "recommendation": notice.recomendacion, "zone": notice.zona.nombre if notice.zona_id else "Huerto",
        "createdAt": notice.creado_en.isoformat(),
        "resolvedAt": notice.resuelto_en.isoformat() if notice.resuelto_en else None,
        "importance": {"informacion": "info", "advertencia": "medium", "critico": "high"}[notice.severidad],
        "condition": "resolved" if notice.resuelto_en else "active", "read": notice.is_read,
    }

def notice_list(user, garden):
    return [notice_projection(notice) for notice in notice_queryset(user, garden)]

def notice_detail(user, garden, notice_id):
    from huerto.models import Aviso
    try:
        return notice_projection(notice_queryset(user, garden).get(pk=notice_id))
    except Aviso.DoesNotExist:
        raise GardenAccessError("notice-not-found", 404) from None

@transaction.atomic
def mark_notice_read(user, notice_id):
    from django.utils import timezone
    from huerto.models import Aviso, AvisoLeido
    # Serialize with membership changes and concurrent reads of the same notice.
    membership = Membresia.objects.select_for_update().filter(
        usuario=user, activa=True, huerto__clave="principal").select_related("huerto").first()
    if not membership or not visible_gardens(user).filter(pk=membership.huerto_id).exists():
        raise GardenAccessError()
    try:
        notice = Aviso.objects.select_for_update().get(pk=notice_id, huerto=membership.huerto)
    except Aviso.DoesNotExist:
        raise GardenAccessError("notice-not-found", 404) from None
    receipt, _ = AvisoLeido.objects.get_or_create(aviso=notice, usuario=user, defaults={"leido_en": timezone.now()})
    item = notice_detail(user, membership.huerto, notice.pk)
    return {"status": "accepted", "id": str(notice.pk), "read": True,
            "readAt": receipt.leido_en.isoformat(), "item": item}
