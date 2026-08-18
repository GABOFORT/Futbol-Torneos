from django.apps import AppConfig


class EquiposConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.equipos'
    verbose_name = 'Equipos'

    def ready(self):
        from apps.usuarios.archivos import conectar
        from .models import Equipo

        conectar(Equipo)
