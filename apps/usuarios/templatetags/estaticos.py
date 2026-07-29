from django import template

from apps.usuarios.estaticos import url_estatico

register = template.Library()


@register.simple_tag
def static_v(ruta):
    """Igual que {% static %} pero con la version del archivo pegada al final."""
    return url_estatico(ruta)
