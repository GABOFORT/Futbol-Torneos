import os

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

_versiones = {}


def url_estatico(ruta):
    """URL del estatico con la fecha de modificacion pegada al final.

    Sirve para que el navegador vuelva a bajar el archivo apenas cambia, sin
    perder el cacheo cuando no cambio: mismo contenido, misma URL.

    Vive en un modulo comun y no en el templatetag porque tambien se usa desde
    los modelos, por ejemplo para la imagen por defecto del escudo.
    """
    url = static(ruta)
    version = _version_de(ruta)
    if not version:
        return url
    separador = '&' if '?' in url else '?'
    return f'{url}{separador}v={version}'


def _version_de(ruta):
    if not settings.DEBUG and ruta in _versiones:
        return _versiones[ruta]

    version = ''
    absoluta = finders.find(ruta)
    if not absoluta and settings.STATIC_ROOT:
        candidata = os.path.join(settings.STATIC_ROOT, ruta)
        absoluta = candidata if os.path.exists(candidata) else None
    if absoluta:
        try:
            version = str(int(os.path.getmtime(absoluta)))
        except OSError:
            version = ''

    if not settings.DEBUG:
        _versiones[ruta] = version
    return version
