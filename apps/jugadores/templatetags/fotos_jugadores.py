from django import template

from apps.usuarios.permissions import puede_ver_foto_de_jugador

register = template.Library()


@register.filter
def foto_visible_para(jugador, user):
    return puede_ver_foto_de_jugador(user, jugador)
