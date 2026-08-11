"""Deja constancia de quien entra y quien sale del sistema.

Se engancha a las senales de Django y no a `login_view` a proposito: asi vale
por todos los caminos, incluido el login del panel de administracion, que no
pasa por nuestra vista. Si manana se agrega otra forma de entrar, esta ya queda
registrada sola.

Los intentos FALLIDOS no se registran aca: ya los emite django-axes, y LOGGING
los manda a este mismo archivo (ver futbol/settings.py). Repetirlos solo
ensuciaria la bitacora.
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .auditoria import ip_de, registro


@receiver(user_logged_in)
def registrar_entrada(sender, request, user, **kwargs):
    """Un login que SI funciono.

    Es la mitad que suele faltar en las bitacoras, y es la que importa el dia
    del incidente: los fallidos dicen que alguien lo intento, este dice que
    alguien lo consiguio. Un ataque de fuerza bruta exitoso se ve justo asi —
    decenas de lineas de axes y despues esta.

    Se anota el rol porque no es lo mismo que entre un entrenador a que entre
    un Administrador General a las tres de la manana.
    """
    registro.info(
        'ENTRADA usuario=%s (id=%s, rol=%s) desde ip=%s',
        user.username, user.pk, user.role, ip_de(request),
    )


@receiver(user_logged_out)
def registrar_salida(sender, request, user, **kwargs):
    """Un cierre de sesion.

    `user` puede venir en None: pasa cuando se cierra una sesion que ya estaba
    vencida del lado del servidor. Se registra igual, porque saber que la sesion
    se cerro sola es justamente el dato interesante.
    """
    registro.info(
        'SALIDA usuario=%s desde ip=%s',
        user.username if user else '(sesion ya vencida)', ip_de(request),
    )
