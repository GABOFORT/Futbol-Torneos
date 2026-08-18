"""Escudos y logos generados cuando no hay imagen cargada.

Ningun equipo del sistema tiene escudo subido, y son 211. Con un unico
placeholder gris todos se ven iguales: la lista de partidos se vuelve una
columna de manchas identicas y no se distingue un club de otro.

La solucion es un **monograma**: las iniciales del club sobre un color propio.
Se genera como SVG en una `data:` URI, no como archivo, por tres motivos:

  - Entra donde ya habia un `<img src>`. Las trece pantallas que muestran un
    escudo no se tocan: siguen pidiendo `equipo.escudo_url` y ahora reciben algo
    que se ve bien.
  - Escala sin pixelarse. El mismo monograma sirve para los 28 px de la llave de
    liguilla y para los 80 px del detalle del equipo.
  - No hay archivos que guardar, servir ni borrar cuando se elimina el equipo.

El color sale del nombre, no de un contador ni de un random: el mismo club tiene
siempre el mismo color, en todas las pantallas y entre corridas. Se usa `md5` y
no `hash()` porque `hash()` de un texto cambia en cada arranque de Python.
"""
import hashlib
from urllib.parse import quote

COLORES = [
    '#1d4ed8',
    '#b91c1c',
    '#047857',
    '#7c3aed',
    '#b45309',
    '#0f766e',
    '#be123c',
    '#4338ca',
    '#15803d',
    '#a16207',
    '#0369a1',
    '#9d174d',
    '#c2410c',
    '#065f46',
    '#1e40af',
    '#831843',
    '#3f6212',
    '#7e22ce',
    '#0e7490',
    '#92400e',
]

IGNORADAS = {'de', 'del', 'la', 'las', 'el', 'los', 'y', 'fc', 'cf', 'sc', 'ac', 'club'}


def iniciales_de(nombre, cuantas=2):
    """Las iniciales de un nombre. 'Bayern Munchen' -> 'BM'.

    Con una sola palabra usable se toman sus dos primeras letras ('Barcelona' ->
    'BA'), que se lee mejor que una inicial suelta perdida en el circulo.
    """
    palabras = [p for p in (nombre or '').split() if any(c.isalpha() for c in p)]
    utiles = [p for p in palabras if p.lower().strip('.') not in IGNORADAS] or palabras
    if len(utiles) >= 2:
        return ''.join(p[0] for p in utiles[:cuantas]).upper()
    if utiles:
        return utiles[0][:cuantas].upper()
    return '?'


def color_de(nombre):
    """Un color estable para ese nombre. El mismo club, siempre el mismo color."""
    digest = hashlib.md5((nombre or '').encode('utf-8')).digest()
    return COLORES[digest[0] % len(COLORES)]


def monograma(nombre):
    """Un escudo generado: las iniciales sobre su color, como `data:` URI.

    Va en `viewBox` de 64 y no en pixeles fijos para que el navegador lo dibuje
    nitido en cualquier tamaño. El circulo ocupa todo el lienzo, asi queda igual
    con `object-fit: cover` que con `contain`.
    """
    letras = iniciales_de(nombre)
    tamano = 26 if len(letras) <= 2 else 20
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<rect width="64" height="64" rx="32" fill="{color_de(nombre)}"/>'
        '<text x="32" y="32" dy=".36em" text-anchor="middle" '
        'font-family="Segoe UI,system-ui,-apple-system,sans-serif" '
        f'font-size="{tamano}" font-weight="700" fill="#ffffff">{letras}</text>'
        '</svg>'
    )
    return 'data:image/svg+xml;charset=utf-8,' + quote(svg)
