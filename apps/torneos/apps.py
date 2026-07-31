from django.apps import AppConfig


class TorneosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.torneos'
    verbose_name = 'Torneos'

    def ready(self):
        # Deja que Liga borre su imagen del disco al eliminarse o al
        # reemplazarla. Va en ready() porque las senales tienen que quedar
        # conectadas al arrancar, una sola vez.
        from apps.usuarios.archivos import conectar
        from .models import Liga

        conectar(Liga)
