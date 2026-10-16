from django import template

from apps.informacion.models import PatrocinadorOficial, RedesDeBuho

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


@register.simple_tag(takes_context=True)
def redes_de_buho(context):
    peticion = context.get('request')
    guardadas = getattr(peticion, '_redes_de_buho', None)
    if guardadas is None:
        registro = RedesDeBuho.objects.filter(pk=1).first()
        guardadas = registro.redes_sociales if registro else []
        if peticion is not None:
            peticion._redes_de_buho = guardadas
    return guardadas
