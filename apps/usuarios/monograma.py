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

# Colores oscuros y saturados, que es lo que deja leer un texto blanco encima.
# Estan elegidos para distinguirse entre si de un vistazo, no solo por nombre.
#
# Son veinte y no doce por el problema del palomar: una categoria puede tener
# hasta 20 equipos, y con doce colores caian dos clubes del mismo color en la
# misma tabla. Con veinte, cada equipo de la categoria mas grande puede tener
# el suyo.
COLORES = [
    '#1d4ed8',  # azul
    '#b91c1c',  # rojo
    '#047857',  # verde
    '#7c3aed',  # violeta
    '#b45309',  # ambar
    '#0f766e',  # petroleo
    '#be123c',  # carmin
    '#4338ca',  # indigo
    '#15803d',  # verde ingles
    '#a16207',  # mostaza
    '#0369a1',  # celeste oscuro
    '#9d174d',  # frambuesa
    '#c2410c',  # naranja quemado
    '#065f46',  # esmeralda oscuro
    '#1e40af',  # azul rey
    '#831843',  # vino
    '#3f6212',  # oliva
    '#7e22ce',  # purpura
    '#0e7490',  # cian oscuro
    '#92400e',  # marron
]

# Palabras que no aportan a las iniciales: 'Real Madrid' tiene que dar RM, pero
# '1. FC Koln' tiene que dar FK y no '1F'.
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
    # Con tres o mas letras hay que achicar la tipografia o se sale del circulo.
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
