from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from plantapp.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # Django Ninja REST API & Docs (/api/docs)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
