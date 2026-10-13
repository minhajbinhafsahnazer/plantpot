import os
import sys
import urllib.parse
from pathlib import Path

# Add project root directory to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plantpot_project.settings')

import django
django.setup()

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command
from django.db import connection

# Run automatic migration and seed on Vercel cold start
try:
    tables = connection.introspection.table_names()
    if 'plantapp_product' not in tables:
        call_command('migrate', interactive=False)
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
                'description': 'Gentle sweeping silhouette wrapped in tactile cream bouclé with an internal kiln-dried ash wood framework.'
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
    print('Vercel startup notice:', e)

django_wsgi_app = get_wsgi_application()

class VercelPathMiddleware:
    """Restores actual requested URL from Vercel rewrites and forward headers."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query = environ.get('QUERY_STRING', '')
        params = urllib.parse.parse_qs(query)

        # 1. First priority: explicit __path__ parameter from vercel.json rewrite
        if '__path__' in params:
            raw_path = params.pop('__path__')[0]
            environ['QUERY_STRING'] = urllib.parse.urlencode(params, doseq=True)
            if not raw_path.startswith('/'):
                raw_path = '/' + raw_path
            environ['PATH_INFO'] = raw_path
            return self.wsgi_app(environ, start_response)

        # 2. Check header fallbacks from Vercel
        for key in ('HTTP_X_FORWARDED_URI', 'RAW_URI', 'REQUEST_URI', 'HTTP_X_MATCHED_PATH'):
            val = environ.get(key)
            if val and 'index.py' not in val:
                environ['PATH_INFO'] = '/' + val.split('?')[0].lstrip('/')
                return self.wsgi_app(environ, start_response)

        # 3. If PATH_INFO is still pointing directly to index.py, route to root
        if environ.get('PATH_INFO', '').endswith('index.py'):
            environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)

app = VercelPathMiddleware(django_wsgi_app)
