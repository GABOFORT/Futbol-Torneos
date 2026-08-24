"""Los nombres que van en la barra de direcciones.

Una liga, una categoria o un equipo se identifican en la URL por su nombre
convertido a texto de direccion —'Leones FC' pasa a 'leones-fc'— en vez de por
su numero interno. El numero sigue existiendo y sigue funcionando: las rutas
viejas redirigen a la nueva, para que un link ya compartido no se muera.

El apodo se recalcula cuando cambia el nombre. Es a proposito: la direccion debe
decir lo que el objeto es hoy, y quien tenga la vieja llega igual por el numero.
"""
from django.utils.text import slugify

TOPE = 120


def apodo(nombre):
    """'Leones F.C.' -> 'leones-f-c'. Nunca vacio."""
    return slugify(nombre)[:TOPE].strip('-') or 'sin-nombre'


def apodo_libre(nombre, ocupados):
    """El apodo de `nombre`, con sufijo si ya lo usa un hermano.

    `ocupados` son los apodos de los objetos con los que comparte espacio de
    nombres: las otras categorias de su liga, los otros equipos de su categoria.
    """
    base = apodo(nombre)
    if base not in ocupados:
        return base

    numero = 2
    while f'{base}-{numero}' in ocupados:
        numero += 1
    return f'{base}-{numero}'


def asignar(instancia, hermanos):
    """Le pone apodo a `instancia` si le falta o si le cambiaron el nombre."""
    esperado = apodo(instancia.nombre)
    actual = instancia.slug or ''
    if actual and (actual == esperado or actual.startswith(f'{esperado}-')):
        return

    ocupados = set(hermanos.exclude(pk=instancia.pk).values_list('slug', flat=True))
    instancia.slug = apodo_libre(instancia.nombre, ocupados)


def canonica(obtener):
    """Vista que manda una direccion vieja con numero a la que vale hoy.

    Las rutas por id no se retiran nunca: un link compartido hace meses —o un
    buscador que ya lo indexo— tiene que seguir llegando. Responde 301 para que
    el navegador y el robot se queden con la nueva.

    Arrastra lo que venga despues del `?`: sin eso un enlace a `?modal=1` caia
    en la pagina completa en vez de en el recuadro.
    """
    from django.shortcuts import redirect

    def vista(request, **claves):
        destino = obtener(**claves).get_absolute_url()
        cola = request.META.get('QUERY_STRING', '')
        return redirect(f'{destino}?{cola}' if cola else destino, permanent=True)

    return vista
