from django.apps import AppConfig

class PlantappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plantapp'

    def ready(self):
        import plantapp.signals  # 👈 Add this line