from django.contrib import admin
from django.urls import path, get_resolver
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.core.management import call_command
from django.db import connection
from plantapp.api import api

def debug_db(request):
    import io, traceback
    out = io.StringIO()
    err = None
    try:
        call_command('migrate', interactive=False, stdout=out, stderr=out)
        from plantapp.models import Category, Product
        cat_furn, _ = Category.objects.get_or_create(name='Furniture')
        cat_light, _ = Category.objects.get_or_create(name='Lighting')
        cat_text, _ = Category.objects.get_or_create(name='Carpets & Textiles')
        cat_pot, _ = Category.objects.get_or_create(name='Objects & Pots')

        Product.objects.get_or_create(
            name='Verona Sofa',
            defaults={
                'category': cat_furn,
                'price': 2850,
                'description': 'Gentle sweeping silhouette wrapped in tactile cream boucle with an internal kiln-dried ash wood framework.'
            }
        )
        Product.objects.get_or_create(
            name='Dune Table Lamp',
            defaults={
                'category': cat_light,
                'price': 480,
                'description': 'Wheel-thrown porous stoneware vessel paired with a coarse woven unbleached Belgian linen lampshade.'
            }
        )
        Product.objects.get_or_create(
            name='Sienna Wool Rug',
            defaults={
                'category': cat_text,
                'price': 890,
                'description': 'Hand-tufted organic New Zealand wool featuring tactile sculpted waves and subtle natural cream variation.'
            }
        )
        Product.objects.get_or_create(
            name='Earthen Vessel',
            defaults={
                'category': cat_pot,
                'price': 195,
                'description': 'Artisanal hand-sculpted ceramic plant pot with soft mineral patina, ideal for olive branches and indoor flora.'
            }
        )
    except Exception as e:
        err = traceback.format_exc()
    
    tables = []
    try:
        tables = connection.introspection.table_names()
    except Exception:
        pass

    return JsonResponse({
        "db_name": str(connection.settings_dict.get('NAME')),
        "tables": tables,
        "migrate_output": out.getvalue(),
        "migrate_error": err,
    })

def api_health(request):
    return JsonResponse({
        "status": "online",
        "service": "Plantpot Luxury Atelier API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "products": "/api/products",
        "debug_db": "/debug-db",
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
    path('debug-db', debug_db, name='debug_db'),
    path('api/index.py', vercel_dispatcher, name='vercel_dispatcher'),
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # Django Ninja REST API & Docs (/api/docs)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
