"""De qué liga es la pantalla que se está mostrando.

Hace falta para pintar la portada de la liga de fondo, y el problema es que no
existe una "liga actual" en el sistema: cada vista manda al template lo que
necesita y nada mas. Estadisticas manda `liga`, la tabla de posiciones manda
`categoria`, el perfil de equipo manda `equipo` y la ficha manda `partido`. En
ninguna de las tres ultimas hay una variable llamada `liga`.

Se resuelve con un template tag y no con un context processor porque el
context processor solo recibe el `request`: no ve lo que la vista puso en el
contexto, que es justamente de donde sale la liga. Con `takes_context=True` el
tag si lo ve.

La alternativa era recorrer las ~20 vistas agregando `liga` al contexto de cada
una. Se descarto: es mas codigo, hay que acordarse en cada vista nueva, y una
que se olvide se queda sin fondo sin que nada lo avise.
"""
from django import template

register = template.Library()

CAMINOS = (
    ('liga', ()),
    ('categoria', ('liga',)),
    ('equipo', ('liga',)),
    ('partido', ('categoria', 'liga')),
    ('jugador', ('equipo', 'liga')),
)


def _seguir(objeto, camino):
    """Recorre `camino` a partir de `objeto`. None si algo por el medio falta."""
    for paso in camino:
        objeto = getattr(objeto, paso, None)
        if objeto is None:
            return None
    return objeto


def _es_liga(objeto):
    """Si esto se parece a una Liga.

    Se pregunta por el atributo en vez de importar el modelo porque hay vistas
    que ponen un `liga` que es solo el nombre en texto —los rankings arman filas
    con `{'liga': 'Liga MX'}`—, y un string no tiene portada que mostrar.
    """
    return hasattr(objeto, 'portada_url')


@register.simple_tag(takes_context=True)
def portada_de_liga(context):
    """La URL de la portada de la liga de esta pantalla, o '' si no aplica.

    **La regla es la misma para todos**: visitante sin cuenta, Administrador de
    Liga y Administrador General ven exactamente lo mismo. Lo unico que decide
    es de que liga es la pantalla, nunca quien la esta mirando.

    Hubo una regla de ultimo recurso —"si el que entro tiene una sola liga, usa
    su portada"— y se quito el 07/08/2026: le pegaba la portada del admin a
    TODAS las pantallas, incluidas la portada del sitio, el buscador y las
    canchas, que no son de ninguna liga en particular.

    Devuelve '' —y por lo tanto se queda el gris neutro del sistema— en tres
    casos, todos a proposito:

      - Pantallas que no son de ninguna liga: la portada del sitio, el buscador,
        el reglamento, el mapa de canchas, el listado general de ligas y el
        tablero de cada usuario.
      - Pantallas que mezclan varias ligas: los resultados de busqueda o el
        calendario sin filtrar. Ahi no hay una liga sola, y mostrar la de la
        primera fila seria arbitrario.
      - Ligas que todavia no cargaron ninguna portada.
    """
    for variable, camino in CAMINOS:
        objeto = context.get(variable)
        if objeto is None:
            continue
        liga = _seguir(objeto, camino)
        if _es_liga(liga) and liga.portada_url:
            return liga.portada_url

    return ''
