"""Authenticated garden/notice projections. There is no device ingestion or actuation API."""
import json
import re
from functools import wraps
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from allauth.account.models import EmailAddress
from huerto.services import current_garden, garden_projection, notice_list, notice_detail, mark_notice_read, GardenAccessError

def failure(status, code):
    return JsonResponse({"status": status, "code": code}, status=status)

def authorized(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_active:
            return failure(401, "unauthenticated")
        try:
            if not EmailAddress.objects.filter(user=request.user, email__iexact=request.user.email, verified=True).exists():
                return failure(403, "verification-required")
            return view(request, *args, **kwargs)
        except GardenAccessError as error:
            return failure(error.status, error.code)
        except DatabaseError:
            # Unavailable data is never returned as a successful empty collection.
            return failure(503, "service-unavailable")
    return wrapped

def valid_notice_id(value):
    return isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,18}", value) and int(value) < 2**63

@never_cache
@require_GET
@authorized
def garden(request):
    return JsonResponse(garden_projection(current_garden(request.user)))

@never_cache
@require_GET
@authorized
def notices(request):
    garden = current_garden(request.user)
    return JsonResponse({"status": "ready", "items": notice_list(request.user, garden)})

@never_cache
@require_GET
@authorized
def notice(request, notice_id):
    garden = current_garden(request.user)
    if not valid_notice_id(notice_id):
        return failure(404, "notice-not-found")
    return JsonResponse({"status": "ready", "item": notice_detail(request.user, garden, int(notice_id))})

@never_cache
@require_http_methods(["PUT"])
@authorized
def read_notice(request, notice_id):
    # Permission is checked before looking up the notice; IDs never grant access.
    current_garden(request.user)
    if not valid_notice_id(notice_id):
        return failure(404, "notice-not-found")
    try:
        body = json.loads(request.body) if request.body else {}
        if body != {}:
            return failure(400, "invalid-input")
    except (ValueError, UnicodeError):
        return failure(400, "invalid-input")
    result = mark_notice_read(request.user, int(notice_id))
    return JsonResponse(result)
