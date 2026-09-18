from django.apps import AppConfig


class InformacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.informacion'
    verbose_name = 'Información'

    def ready(self):
        from apps.usuarios.archivos import conectar
        from .models import PatrocinadorOficial

        conectar(PatrocinadorOficial)
