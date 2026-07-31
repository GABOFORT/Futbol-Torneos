from django.apps import AppConfig


class EquiposConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.equipos'
    verbose_name = 'Equipos'

    def ready(self):
        # Deja que Equipo borre su imagen del disco al eliminarse o al
        # reemplazarla. Va en ready() porque las senales tienen que quedar
        # conectadas al arrancar, una sola vez.
        from apps.usuarios.archivos import conectar
        from .models import Equipo

        conectar(Equipo)
