from django.apps import AppConfig


class JugadoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.jugadores'
    verbose_name = 'Jugadores'

    def ready(self):
        # Deja que Jugador borre su imagen del disco al eliminarse o al
        # reemplazarla. Va en ready() porque las senales tienen que quedar
        # conectadas al arrancar, una sola vez.
        from apps.usuarios.archivos import conectar
        from .models import Jugador

        conectar(Jugador)
