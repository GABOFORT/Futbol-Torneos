from django.apps import AppConfig


class TorneosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.torneos'
    verbose_name = 'Torneos'

    def ready(self):
        from apps.usuarios.archivos import conectar
        from .models import Liga

        conectar(Liga)
