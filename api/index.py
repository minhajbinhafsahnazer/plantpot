import os
import sys
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

class VercelPathMiddleware:
    """Restores actual requested URL from Vercel rewrite headers."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = environ.get('HTTP_X_MATCHED_PATH')
        if matched:
            environ['PATH_INFO'] = matched
        return self.wsgi_app(environ, start_response)

app = VercelPathMiddleware(get_wsgi_application())
