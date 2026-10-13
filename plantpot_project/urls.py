from django.contrib import admin
from django.urls import path, get_resolver
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from plantapp.api import api

def api_health(request):
    return JsonResponse({
        "status": "online",
        "service": "Plantpot Luxury Atelier API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "products": "/api/products",
        "currency": "AED"
    })

def vercel_dispatcher(request):
    """Seamlessly dispatches Vercel rewrites to target URL patterns."""
    raw_path = request.GET.get('__path__', '/')
    if not raw_path.startswith('/'):
        raw_path = '/' + raw_path
    if raw_path in ('/api/index.py', 'api/index.py'):
        raw_path = '/'
    request.path_info = raw_path
    request.path = raw_path
    resolver = get_resolver()
    match = resolver.resolve(raw_path)
    return match.func(request, *match.args, **match.kwargs)

urlpatterns = [
    path('', api_health, name='api_health'),
    path('api/index.py', vercel_dispatcher, name='vercel_dispatcher'),
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # Django Ninja REST API & Docs (/api/docs)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
