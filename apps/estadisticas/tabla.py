"""Calculo de la tabla de posiciones de una categoria.

Vive aparte de la vista porque la ficha de partido tambien necesita saber en
que puesto va cada equipo, y la regla de los puntos (con el punto extra por
penales incluido) tiene que estar escrita una sola vez.
"""
from apps.equipos.models import Equipo
from apps.partidos.models import Partido


def fila_vacia(equipo):
    return {
        'equipo': equipo,
        'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0,
        'gf': 0, 'gc': 0, 'dg': 0, 'pen': 0, 'pts': 0,
    }


def calcular(categoria):
    """Las filas de la tabla, ordenadas del primero al ultimo.

    Entran todos los equipos de la categoria, tambien los que no jugaron
    todavia: en la tabla figuran desde el arranque con la fila en cero.
    """
    tabla = {equipo.id: fila_vacia(equipo) for equipo in Equipo.objects.filter(categoria=categoria)}

    partidos = Partido.objects.filter(
        categoria=categoria,
        estado=Partido.ESTADO_FINALIZADO,
        fase=Partido.FASE_REGULAR,
    ).select_related('equipo_local', 'equipo_visitante')

    for partido in partidos:
        local = tabla.setdefault(partido.equipo_local_id, fila_vacia(partido.equipo_local))
        visitante = tabla.setdefault(partido.equipo_visitante_id, fila_vacia(partido.equipo_visitante))

        local['pj'] += 1
        visitante['pj'] += 1
        local['gf'] += partido.goles_local
        local['gc'] += partido.goles_visitante
        visitante['gf'] += partido.goles_visitante
        visitante['gc'] += partido.goles_local

        if partido.goles_local > partido.goles_visitante:
            local['pg'] += 1
            local['pts'] += 3
            visitante['pp'] += 1
        elif partido.goles_local < partido.goles_visitante:
            visitante['pg'] += 1
            visitante['pts'] += 3
            local['pp'] += 1
        else:
            local['pe'] += 1
            visitante['pe'] += 1
            local['pts'] += 1
            visitante['pts'] += 1
            if categoria.empate_define_penales and partido.ganador_penales_id in tabla:
                tabla[partido.ganador_penales_id]['pts'] += 1
                tabla[partido.ganador_penales_id]['pen'] += 1

    for fila in tabla.values():
        fila['dg'] = fila['gf'] - fila['gc']

    return sorted(tabla.values(), key=lambda fila: (-fila['pts'], -fila['dg'], -fila['gf']))


def puesto_de(posiciones, equipo_id):
    """En que lugar de la tabla va un equipo, junto con su fila.

    Devuelve None si el equipo no esta en esa tabla, que no deberia pasar pero
    evita que la ficha reviente si algun dia se mueve un equipo de categoria.
    """
    for numero, fila in enumerate(posiciones, start=1):
        if fila['equipo'].id == equipo_id:
            return {'puesto': numero, 'de': len(posiciones), **fila}
    return None
