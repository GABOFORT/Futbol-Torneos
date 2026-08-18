"""Armado del calendario por jornadas (round-robin, metodo del circulo).

Cada equipo juega una vez por jornada. Con una cantidad impar de equipos se
agrega un lugar vacio: el que le toca enfrentarlo descansa esa jornada.

    18 equipos (par)   -> 17 jornadas de 9 partidos, nadie descansa
    17 equipos (impar) -> 17 jornadas de 8 partidos, 1 descansa por jornada

Con dos vueltas la rueda completa se repite con la localia invertida:

    8 equipos a 1 vuelta   ->  7 jornadas,  28 partidos
    8 equipos a 2 vueltas  -> 14 jornadas,  56 partidos
    15 equipos a 2 vueltas -> 30 jornadas, 210 partidos
"""

LUGAR_VACIO = None

VUELTAS_MINIMAS = 1
VUELTAS_MAXIMAS = 2


def armar_jornadas(equipos, vueltas=VUELTAS_MINIMAS):
    """Devuelve una lista de jornadas; cada jornada es [(local, visitante), ...]."""
    ida = _una_vuelta(equipos)
    if not ida or vueltas <= VUELTAS_MINIMAS:
        return ida

    repeticiones = min(vueltas, VUELTAS_MAXIMAS)
    jornadas = list(ida)
    for _ in range(repeticiones - 1):
        jornadas += [_invertir(jornada) for jornada in ida]
    return jornadas


def _una_vuelta(equipos):
    """La rueda completa: todos contra todos una sola vez."""
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
                continue
            partidos.append((otro, uno) if numero % 2 else (uno, otro))
        jornadas.append(partidos)
        rueda = [rueda[0], rueda[-1]] + rueda[1:-1]
    return jornadas


def _invertir(jornada):
    """La misma jornada con la localia cambiada: el que fue local ahora visita."""
    return [(visitante, local) for local, visitante in jornada]


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
