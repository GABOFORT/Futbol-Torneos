from django.apps import AppConfig


class JugadoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.jugadores'
    verbose_name = 'Jugadores'

    def ready(self):
        from apps.usuarios.archivos import conectar
        from .models import Jugador

        conectar(Jugador)
