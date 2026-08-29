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
import os

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()

CAMINOS = (
    ('liga', ()),
    ('torneo', ('liga',)),
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


def _ligas_del_contexto(context):
    """Las ligas a las que apunta esta pantalla, en orden de cercania.

    Es el recorrido que comparten la portada de fondo y la imagen de compartir:
    las dos preguntan lo mismo —de que liga es esto— y solo cambian en que se
    quedan.
    """
    for variable, camino in CAMINOS:
        objeto = context.get(variable)
        if objeto is None:
            continue
        liga = _seguir(objeto, camino)
        if _es_liga(liga):
            yield liga


_MEDIDAS = {}


def _medidas(campo):
    """Ancho y alto del archivo, recordados por ruta y fecha de modificacion.

    Las redes piden las medidas en el encabezado para reservar el hueco antes de
    bajar la imagen. Sacarlas abre el archivo, y son siempre los mismos cuatro o
    cinco: se guardan en memoria para no releerlos en cada visita.
    """
    try:
        ruta = campo.path
        marca = os.path.getmtime(ruta)
    except (ValueError, OSError, NotImplementedError):
        return None

    guardado = _MEDIDAS.get(ruta)
    if guardado and guardado[0] == marca:
        return guardado[1]

    try:
        medida = (campo.width, campo.height)
    except (OSError, ValueError):
        return None

    _MEDIDAS[ruta] = (marca, medida)
    return medida


def _ficha(url, alto_texto, medida):
    return {
        'url': absoluta(url),
        'alt': alto_texto,
        'ancho': medida[0] if medida else '',
        'alto': medida[1] if medida else '',
    }


@register.simple_tag
def absoluta(ruta):
    """Pega el dominio del sitio a una ruta interna.

    Sale de `SITIO_URL` en el .env y nunca de la cabecera Host: quien pide la
    pagina la manda, y un robot que lea la etiqueta terminaria apuntando al
    dominio que el atacante quiera.
    """
    if not ruta or '://' in ruta:
        return ruta
    return f'{settings.SITIO_URL}{ruta}' if settings.SITIO_URL else ruta


@register.simple_tag(takes_context=True)
def imagen_de_compartir(context):
    """La imagen que sale en la tarjeta al pegar el link, con sus medidas.

    Baja por la escalera y se queda con la primera que exista: el escudo del
    equipo, la portada de la liga o torneo de esta pantalla, su logo, y al final
    el logo del sitio. Asi un link nunca se comparte sin imagen.
    """
    equipo = context.get('equipo')
    escudo = getattr(equipo, 'escudo', None)
    if escudo:
        return _ficha(escudo.url, f'Escudo de {equipo.nombre}', _medidas(escudo))

    for liga in _ligas_del_contexto(context):
        for campo, plantilla in ((liga.portada, 'Portada de {}'),
                                 (liga.logo, 'Logo de {}')):
            if campo:
                return _ficha(campo.url, plantilla.format(liga.nombre),
                              _medidas(campo))

    return _ficha(static('img/buho-sport.jpeg'), 'BUHO Sports League', None)


@register.simple_tag(takes_context=True)
def url_de_compartir(context):
    """La direccion completa de la pantalla que se esta viendo."""
    peticion = context.get('request')
    return absoluta(peticion.path if peticion is not None else '/')


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
    for liga in _ligas_del_contexto(context):
        if liga.portada_url:
            return liga.portada_url

    return ''


@register.simple_tag(takes_context=True)
def patrocinadores_de_la_pantalla(context):
    """Los patrocinadores de la liga o el torneo al que pertenece esta pantalla.

    Baja por la misma escalera que la portada de fondo, porque la pregunta es
    exactamente la misma: de que liga es esto. Gracias a eso el patrocinio
    aparece solo en las categorias, los equipos, los jugadores, los partidos y
    las tablas sin tocar una sola vista, y las pantallas que se agreguen manana
    lo heredan sin que nadie tenga que acordarse.

    Devuelve None —y entonces no se dibuja nada— cuando la pantalla no es de
    ninguna liga en particular (la portada del sitio, el buscador, el
    reglamento) o cuando esa liga todavia no cargo ninguno.
    """
    for liga in _ligas_del_contexto(context):
        patrocinadores = list(liga.patrocinadores.filter(activo=True))
        if patrocinadores:
            return {'liga': liga, 'lista': patrocinadores}
    return None
