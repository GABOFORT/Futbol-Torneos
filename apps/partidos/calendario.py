"""Armado del calendario por jornadas (round-robin, metodo del circulo).

Cada equipo juega una vez por jornada y todos se enfrentan una sola vez en
todo el torneo. Con una cantidad impar de equipos se agrega un lugar vacio:
el que le toca enfrentarlo descansa esa jornada.

    18 equipos (par)   -> 17 jornadas de 9 partidos, nadie descansa
    17 equipos (impar) -> 17 jornadas de 8 partidos, 1 descansa por jornada
"""

LUGAR_VACIO = None


def armar_jornadas(equipos):
    """Devuelve una lista de jornadas; cada jornada es [(local, visitante), ...]."""
    rueda = list(equipos)
    if len(rueda) < 2:
        return []
    if len(rueda) % 2:
        rueda.append(LUGAR_VACIO)

    total = len(rueda)
    jornadas = []
    for numero in range(total - 1):
        partidos = []
        for i in range(total // 2):
            uno, otro = rueda[i], rueda[total - 1 - i]
            if uno is LUGAR_VACIO or otro is LUGAR_VACIO:
                continue  # el que queda solo descansa esta jornada
            # Se alterna la localia jornada a jornada para que ningun equipo
            # juegue siempre de local.
            partidos.append((otro, uno) if numero % 2 else (uno, otro))
        jornadas.append(partidos)
        # Rotacion del circulo: el primero queda fijo y el resto gira.
        rueda = [rueda[0], rueda[-1]] + rueda[1:-1]
    return jornadas


def equipo_que_descansa(equipos, partidos_de_la_jornada):
    """El equipo de la categoria que no juega en esa jornada, si hay alguno.

    Se deduce en vez de guardarse: asi no puede quedar desincronizado con los
    partidos si alguno se cancela o se regenera el calendario.
    """
    juegan = set()
    for partido in partidos_de_la_jornada:
        juegan.add(partido.equipo_local_id)
        juegan.add(partido.equipo_visitante_id)
    libres = [equipo for equipo in equipos if equipo.id not in juegan]
    return libres[0] if len(libres) == 1 else None
