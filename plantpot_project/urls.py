from django.contrib import admin
from django.urls import path
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

urlpatterns = [
    path('', api_health, name='api_health'),
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # Django Ninja REST API & Docs (/api/docs)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
