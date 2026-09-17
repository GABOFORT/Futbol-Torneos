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


def calcular(categoria, grupo=None):
    """Las filas de la tabla, ordenadas del primero al ultimo.

    Entran todos los equipos de la categoria, tambien los que no jugaron
    todavia: en la tabla figuran desde el arranque con la fila en cero.

    Con `grupo` se acota a los equipos de ese grupo. Los partidos que CRUZAN dos
    grupos —los que se arman cuando un grupo impar deja a alguien descansando—
    entran igual, pero solo suman para el equipo que pertenece a este grupo: el
    rival ya los sumo en la tabla del suyo.
    """
    equipos = (categoria.equipos_del_grupo(grupo) if grupo
               else Equipo.objects.filter(categoria=categoria)).order_by('id')
    tabla = {equipo.id: fila_vacia(equipo) for equipo in equipos}

    partidos = Partido.objects.filter(
        categoria=categoria,
        estado=Partido.ESTADO_FINALIZADO,
        fase=Partido.FASE_REGULAR,
    ).select_related('equipo_local', 'equipo_visitante')

    for partido in partidos:
        if grupo:
            if not (partido.equipo_local_id in tabla
                    or partido.equipo_visitante_id in tabla):
                continue
        else:
            tabla.setdefault(partido.equipo_local_id, fila_vacia(partido.equipo_local))
            tabla.setdefault(partido.equipo_visitante_id, fila_vacia(partido.equipo_visitante))

        local = tabla.get(partido.equipo_local_id)
        visitante = tabla.get(partido.equipo_visitante_id)

        if local is not None:
            local['pj'] += 1
            local['gf'] += partido.goles_local
            local['gc'] += partido.goles_visitante
        if visitante is not None:
            visitante['pj'] += 1
            visitante['gf'] += partido.goles_visitante
            visitante['gc'] += partido.goles_local

        if partido.goles_local > partido.goles_visitante:
            if local is not None:
                local['pg'] += 1
                local['pts'] += 3
            if visitante is not None:
                visitante['pp'] += 1
        elif partido.goles_local < partido.goles_visitante:
            if visitante is not None:
                visitante['pg'] += 1
                visitante['pts'] += 3
            if local is not None:
                local['pp'] += 1
        else:
            for fila in (local, visitante):
                if fila is not None:
                    fila['pe'] += 1
                    fila['pts'] += 1
            if categoria.empate_define_penales and partido.ganador_penales_id in tabla:
                tabla[partido.ganador_penales_id]['pts'] += 1
                tabla[partido.ganador_penales_id]['pen'] += 1

    for fila in tabla.values():
        fila['dg'] = fila['gf'] - fila['gc']

    return sorted(tabla.values(), key=_orden)


def _orden(fila):
    """Puntos, diferencia, goles a favor y, al final, quien se inscribio antes.

    Los tres primeros son la regla deportiva. El cuarto existe porque sin el la
    tabla quedaba a merced de Postgres: con todo empatado —y al arrancar la
    temporada TODOS empatan en cero— el orden era el que devolviera la consulta,
    que no esta garantizado y cambia al editar cualquier equipo. Un padre podia
    ver a su hijo tercero y al recargar verlo noveno sin que se jugara nada.

    Se desempata por antiguedad y no por nombre para que la tabla en blanco
    cuente algo cierto: el orden en que se fueron inscribiendo. El `id` es el
    orden de alta real; `fecha_creacion` solo guarda el dia y no distingue entre
    los que entraron el mismo.
    """
    return -fila['pts'], -fila['dg'], -fila['gf'], fila['equipo'].id


def puesto_de(posiciones, equipo_id):
    """En que lugar de la tabla va un equipo, junto con su fila.

    Devuelve None si el equipo no esta en esa tabla, que no deberia pasar pero
    evita que la ficha reviente si algun dia se mueve un equipo de categoria.
    """
    for numero, fila in enumerate(posiciones, start=1):
        if fila['equipo'].id == equipo_id:
            return {'puesto': numero, 'de': len(posiciones), **fila}
    return None
