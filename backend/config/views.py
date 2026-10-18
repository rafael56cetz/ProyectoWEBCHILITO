from pathlib import Path
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe
from config.private import PROJECT_ROOT

DIST = PROJECT_ROOT / "dist"

@require_safe
def frontend(request):
    return FileResponse((DIST / "index.html").open("rb"), content_type="text/html; charset=utf-8")

@require_safe
def resource(request, path):
    target = (DIST / path).resolve()
    if not target.is_relative_to(DIST.resolve()) or not target.is_file():
        raise Http404
    return FileResponse(target.open("rb"))
