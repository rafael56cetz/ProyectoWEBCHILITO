from pathlib import Path
from django.conf import settings
from django.http import FileResponse,Http404,JsonResponse
from django.views.decorators.http import require_GET
ROOT=Path(settings.PROJECT_ROOT)/'frontend'
@require_GET
def frontend(request):return FileResponse((ROOT/'index.html').open('rb'),content_type='text/html; charset=utf-8')
@require_GET
def resource(request,path):
    candidate=(ROOT/path).resolve()
    if ROOT.resolve() not in candidate.parents or not candidate.is_file():raise Http404
    if candidate.suffix.lower() not in {'.js','.css','.svg','.webp','.jpg','.png','.ttf','.woff2'}:raise Http404
    return FileResponse(candidate.open('rb'))
def not_found(request,exception=None):return JsonResponse({'status':404,'code':'not-found'},status=404)
def server_error(request):return JsonResponse({'status':500,'code':'service-unavailable'},status=500)
