from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def segundos_aviso_sesion():
    """Cuantos segundos antes del vencimiento se muestra el aviso.

    Un tag y no un context processor a proposito: el aviso solo se dibuja en las
    pantallas con sesion iniciada, y un context processor correria en cada
    peticion del sitio publico —la portada, las tablas, el calendario— para un
    dato que ahi no se usa nunca.
    """
    return settings.SESION_AVISO_SEGUNDOS


@register.simple_tag
def minutos_sesion():
    """Cuantos minutos de inactividad se toleran, para decirlo en pantalla.

    Sale de SESSION_COOKIE_AGE y no escrito a mano en la plantilla: si manana se
    sube SESION_MINUTOS en el .env, la pantalla que explica el cierre seguiria
    diciendo "20 minutos" y estaria mintiendo, que en un mensaje de seguridad es
    peor que no decir nada.
    """
    return settings.SESSION_COOKIE_AGE // 60
