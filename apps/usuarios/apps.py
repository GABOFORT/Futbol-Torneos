from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.usuarios'
    verbose_name = 'Usuarios'

    def ready(self):
        """Conecta las senales de entrada y salida a la bitacora.

        El import va adentro de ready() y no arriba del archivo porque en ese
        momento las apps todavia no terminaron de cargar y tocar los modelos
        revienta el arranque. Es el lugar que Django reserva justo para esto.

        `noqa`: el import parece no usarse, pero es el que registra los
        receptores. Sin el, las senales no llegan a ningun lado.
        """
        from . import senales  # noqa: F401
