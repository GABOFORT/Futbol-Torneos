import segno
from django.utils.safestring import mark_safe

from apps.torneos.templatetags.liga_actual import absoluta

CREDENCIALES_POR_HOJA = 4


def qr_del_equipo(equipo):
    enlace = absoluta(equipo.get_absolute_url())
    return mark_safe(segno.make(enlace, error='m').svg_inline(border=0, omitsize=True, dark='#111111'))


def en_hojas(jugadores):
    return [jugadores[inicio:inicio + CREDENCIALES_POR_HOJA]
            for inicio in range(0, len(jugadores), CREDENCIALES_POR_HOJA)]
