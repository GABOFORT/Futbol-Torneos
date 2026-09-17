"""Armado del calendario por jornadas (round-robin, metodo del circulo).

Cada equipo juega una vez por jornada. Son dos ruedas distintas segun la
cantidad de equipos, porque el papel del descanso cambia:

    18 equipos (par)   -> 17 jornadas de 9 partidos, nadie descansa
    9 equipos (impar)  ->  9 jornadas de 4 partidos, 1 descansa por jornada

CON CANTIDAD PAR el primero queda fijo y los demas rotan a su alrededor:

    J1:  1-2   12-3   11-4   10-5   9-6   8-7

CON CANTIDAD IMPAR no hay a quien fijar, asi que la jornada la define QUIEN
DESCANSA: en la primera descansa el primero, en la segunda el segundo, y los
demas se emparejan hacia afuera a partir de el.

    J1 (descansa 1):  9-2   8-3   7-4   6-5
    J2 (descansa 2):  1-3   9-4   8-5   7-6
    J3 (descansa 3):  2-4   1-5   9-6   8-7

Antes el impar se resolvia agregando un equipo fantasma para volverlo par, y el
que le tocaba enfrentarlo descansaba. Salia un torneo valido, pero el descanso
caia salteado —el tercero, el quinto, el septimo— en vez de correr en orden, y
no es asi como se arma un rol a mano.

La rueda par se recorre de atras para adelante. El metodo del circulo arranca
emparejando al primero con el ultimo (1-12) y termina emparejandolo con el
segundo (1-2), y el orden natural de una liga es el contrario: la jornada de
apertura es 1-2, 12-3, 11-4... Son las mismas jornadas y los mismos partidos,
solo cambia en que fecha cae cada uno.

Con dos vueltas la rueda completa se repite con la localia invertida:

    8 equipos a 1 vuelta   ->  7 jornadas,  28 partidos
    8 equipos a 2 vueltas  -> 14 jornadas,  56 partidos
    15 equipos a 2 vueltas -> 30 jornadas, 210 partidos
"""

MINIMO_EQUIPOS = 2

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
    if len(rueda) < MINIMO_EQUIPOS:
        return []
    return _rueda_impar(rueda) if len(rueda) % 2 else _rueda_par(rueda)


def _rueda_par(rueda):
    """El primero queda fijo y los demas giran a su alrededor.

    La localia se alterna jornada a jornada para que nadie reciba siempre en su
    cancha ni visite siempre la ajena.
    """
    total = len(rueda)
    jornadas = []
    for numero in range(total - 1):
        jornadas.append([
            (rueda[total - 1 - puesto], rueda[puesto]) if numero % 2
            else (rueda[puesto], rueda[total - 1 - puesto])
            for puesto in range(total // 2)
        ])
        rueda = [rueda[0], rueda[-1]] + rueda[1:-1]
    jornadas.reverse()
    return jornadas


def _rueda_impar(rueda):
    """Cada jornada la define quien descansa; los demas se emparejan a su lado.

    En la jornada del que descansa se van tomando pares a distancias crecientes
    de el —su vecino anterior con su vecino siguiente, y asi hacia afuera—,
    dando la vuelta al circulo. Sale un torneo parejo sin tener que inventar un
    equipo fantasma: cada uno descansa exactamente una vez y queda de local
    tantas veces como de visitante.
    """
    total = len(rueda)
    return [
        [(rueda[(descansa - distancia) % total], rueda[(descansa + distancia) % total])
         for distancia in range(1, total // 2 + 1)]
        for descansa in range(total)
    ]


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
