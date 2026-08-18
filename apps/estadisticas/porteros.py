"""Porterias menos vencidas: que equipos reciben menos goles.

Va por equipo y no por portero a proposito. El sistema no registra quien ataja
cada partido, y casi todos los equipos tienen dos o tres porteros en el plantel:
repartirles los goles recibidos seria inventar un dato. Lo que si se sabe con
certeza es cuantos goles recibio cada equipo, y eso es lo que se ordena.

Los porteros del plantel se muestran igual, como el rostro de esa porteria,
pero sin numeros propios.
"""
from django.db.models import Q

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.partidos.models import Partido


def calcular(equipos):
    """Un bloque por categoria, cada uno con su tabla del que menos recibio al que mas.

    Se agrupa por categoria y no se devuelve una tabla unica porque una
    porteria solo se compara dentro de la misma competencia: un equipo de una categoria
    de 10 jornadas contra otro de 18 no miden lo mismo, y ni siquiera juegan
    entre ellos. Los filtros acotan que categorias se ven; el orden siempre es
    interno a cada una.

    `equipos` es un queryset ya acotado a lo que el usuario puede ver y a los
    filtros que eligio. Se resuelve con tres consultas fijas, sin importar
    cuantos equipos entren.
    """
    equipos = list(equipos.select_related('liga', 'categoria'))
    if not equipos:
        return []

    filas = {equipo.id: _fila_vacia(equipo) for equipo in equipos}

    partidos = Partido.objects.filter(
        Q(equipo_local__in=equipos) | Q(equipo_visitante__in=equipos),
        estado=Partido.ESTADO_FINALIZADO,
        fase=Partido.FASE_REGULAR,
    ).only('equipo_local_id', 'equipo_visitante_id', 'goles_local', 'goles_visitante')

    for partido in partidos:
        _sumar(filas.get(partido.equipo_local_id), partido.goles_visitante)
        _sumar(filas.get(partido.equipo_visitante_id), partido.goles_local)

    for portero in Jugador.objects.filter(
        equipo__in=equipos, posicion='portero'
    ).exclude(estado=Jugador.ESTADO_BAJA).order_by('numero', 'apellido'):
        fila = filas.get(portero.equipo_id)
        if fila is not None:
            fila['porteros'].append(portero)

    for fila in filas.values():
        if fila['pj']:
            fila['promedio'] = round(fila['recibidos'] / fila['pj'], 2)

    bloques = {}
    for fila in filas.values():
        categoria = fila['equipo'].categoria
        bloque = bloques.setdefault(categoria.id, {'categoria': categoria, 'filas': []})
        bloque['filas'].append(fila)

    for bloque in bloques.values():
        bloque['filas'].sort(
            key=lambda fila: (not fila['pj'], fila['promedio'], -fila['porterias_cero'], fila['recibidos'])
        )

    return sorted(
        bloques.values(),
        key=lambda bloque: (bloque['categoria'].liga.nombre, bloque['categoria'].nombre),
    )


def _fila_vacia(equipo):
    return {
        'equipo': equipo,
        'porteros': [],
        'pj': 0,
        'recibidos': 0,
        'porterias_cero': 0,
        'promedio': 0,
    }


def _sumar(fila, recibidos):
    if fila is None:
        return
    fila['pj'] += 1
    fila['recibidos'] += recibidos
    if recibidos == 0:
        fila['porterias_cero'] += 1
