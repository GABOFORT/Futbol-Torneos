from django import template

from apps.informacion.models import PatrocinadorOficial

register = template.Library()


@register.simple_tag(takes_context=True)
def patrocinadores_oficiales(context):
    peticion = context.get('request')
    guardados = getattr(peticion, '_patrocinadores_oficiales', None)
    if guardados is None:
        guardados = list(PatrocinadorOficial.objects.visibles())
        if peticion is not None:
            peticion._patrocinadores_oficiales = guardados
    return guardados
