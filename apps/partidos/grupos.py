"""Fase de grupos: cada grupo juega su propio todos contra todos.

Lo usan las dos competencias. Un torneo relampago corre una sola vuelta y en un
dia, asi que empareja entre grupos a los que descansan para que nadie viaje en
balde; una liga suele ir a ida y vuelta y deja descansar de verdad, porque ese
partido cruzado suma puntos y dejaria a unos equipos con mas jornadas jugadas
que otros. Las dos cosas salen de la categoria (`vueltas` y
`cruces_entre_grupos`), no de saber cual competencia es.

Los equipos de la categoria se reparten en los grupos que el administrador
declare —de la A a la Z— y cada grupo juega su propio todos contra todos. Los
grupos no se cruzan: un equipo del A nunca enfrenta a uno del B.

Cada grupo lleva su tabla y la categoria lleva ademas una general con todos.
La tabla ordena y muestra, pero NO decide: quien pasa a la liguilla lo elige el
administrador, y tambien contra quien juega. Es a proposito —cada torneo tiene
su regla ("los tres primeros y el mejor segundo", "el ganador del A contra el
del C") y ninguna se deja escribir en el codigo sin quedarse corta.

Los partidos salen sin fecha: un torneo por grupos dura varios dias y se juega
en varias canchas, asi que la agenda la pone el administrador partido por
partido.
"""
from apps.equipos.models import Equipo
from apps.estadisticas import tabla

from . import calendario, liguilla, relampago
from .models import Partido


def repartir(categoria):
    """Acomoda a los equipos en sus grupos y devuelve como quedo el reparto.

    Por bloques y en orden de inscripcion: los primeros que se dieron de alta
    forman el grupo A, los siguientes el B. Cuando la division no es exacta, los
    primeros grupos se llevan el equipo de mas —trece equipos en dos grupos son
    siete y seis; en tres, cinco, cuatro y cuatro—.

    Lo hace el sistema y no el administrador porque en una liga el reparto sale
    de la cuenta y no de un criterio: no hay nada que decidir que la division no
    resuelva sola. Un torneo relampago si lo elige a mano —ahi los grupos se
    sortean o se acomodan— y por eso pide el grupo al inscribir cada equipo.

    Con un solo grupo no escribe nada: ahi la pertenencia es implicita
    (ver `Categoria.equipos_del_grupo`).
    """
    if not categoria.varios_grupos:
        return categoria.reparto

    letras = categoria.letras_de_grupo
    equipos = list(categoria.equipos.order_by('id'))
    por_grupo, sobrantes = divmod(len(equipos), len(letras))

    cambiados, desde = [], 0
    for numero, letra in enumerate(letras):
        cuantos = por_grupo + (1 if numero < sobrantes else 0)
        for equipo in equipos[desde:desde + cuantos]:
            if equipo.grupo != letra:
                equipo.grupo = letra
                cambiados.append(equipo)
        desde += cuantos

    if cambiados:
        Equipo.objects.bulk_update(cambiados, ['grupo'])
    return categoria.reparto


def motivo_para_no_generar(categoria):
    """Por que no se pueden generar los partidos de grupos, o '' si ya se puede."""
    if not categoria.juega_por_grupos:
        return 'Esta categoría no se juega por grupos.'
    if categoria.partidos.exists():
        return 'Los partidos de esta categoría ya están generados.'

    minimo = categoria.MINIMO_POR_GRUPO
    flacos = [f'grupo {letra} ({cuantos})'
              for letra, cuantos in categoria.reparto.items() if cuantos < minimo]
    if flacos:
        return (f'Cada grupo necesita al menos {minimo} equipos. '
                f'Falta llenar: {", ".join(flacos)}.')

    sueltos = categoria.equipos_sin_grupo
    if sueltos:
        return (f'Hay {sueltos} equipo(s) sin grupo asignado. Edítalos y ponles '
                f'uno antes de generar los partidos.')
    return ''


def puede_generar(categoria):
    return not motivo_para_no_generar(categoria)


def generar(categoria):
    """Arma el todos contra todos de cada grupo. Devuelve los partidos creados."""
    if not puede_generar(categoria):
        return []

    por_jornada, descansan = {}, {}
    for letra in categoria.letras_de_grupo:
        equipos = list(categoria.equipos_del_grupo(letra).order_by('id'))
        rueda = calendario.armar_jornadas(equipos, vueltas=categoria.vueltas)
        for numero, jornada in enumerate(rueda, start=1):
            por_jornada.setdefault(numero, []).extend(jornada)
            libre = _el_que_descansa(equipos, jornada)
            if libre is not None:
                descansan.setdefault(numero, []).append(libre)

    if categoria.cruces_entre_grupos:
        for numero, libres in descansan.items():
            por_jornada.setdefault(numero, []).extend(_cruces(libres))

    partidos = []
    for numero in sorted(por_jornada):
        for orden, (local, visitante) in enumerate(por_jornada[numero]):
            partidos.append(relampago.armar(
                categoria, Partido.FASE_REGULAR, orden, local, visitante,
                jornada=numero))

    Partido.objects.bulk_create(partidos)
    return partidos


def _el_que_descansa(equipos, jornada):
    """El equipo del grupo que esa jornada se queda sin rival, si lo hay.

    Solo pasa con grupos impares, y siempre es uno solo: el metodo del circulo
    reparte a los demas de a pares.
    """
    juegan = {equipo.id for par in jornada for equipo in par}
    libres = [equipo for equipo in equipos if equipo.id not in juegan]
    return libres[0] if len(libres) == 1 else None


def _cruces(libres):
    """Empareja de a dos a los que descansan, siempre de grupos distintos.

    Con tres grupos impares se arma un cruce y el tercero descansa de verdad:
    no hay con quien emparejarlo sin repetirle rival dentro de la misma jornada.
    """
    pendientes = sorted(libres, key=lambda equipo: equipo.grupo)
    cruces = []
    while len(pendientes) >= 2:
        uno = pendientes.pop(0)
        otro = next((e for e in pendientes if e.grupo != uno.grupo), None)
        if otro is None:
            break
        pendientes.remove(otro)
        cruces.append((uno, otro))
    return cruces


def posiciones(categoria):
    """Una tabla por grupo declarado, en orden alfabetico."""
    return [
        {
            'grupo': letra,
            'etiqueta': f'Grupo {letra}',
            'posiciones': tabla.calcular(categoria, grupo=letra),
        }
        for letra in categoria.letras_de_grupo
    ]


def jornadas(categoria):
    """Los partidos de grupos agrupados por jornada."""
    partidos = (categoria.partidos
                .filter(fase=Partido.FASE_REGULAR)
                .select_related('equipo_local', 'equipo_visitante', 'sede',
                                'ganador_penales')
                .order_by('jornada', 'orden'))

    por_numero = {}
    for partido in partidos:
        por_numero.setdefault(partido.jornada, []).append(partido)
    return [{'numero': numero, 'partidos': por_numero[numero]}
            for numero in sorted(por_numero)]


def cerrados(categoria):
    """Si ya se jugaron todos los partidos de grupos."""
    partidos = categoria.partidos.filter(fase=Partido.FASE_REGULAR)
    total = partidos.count()
    return total > 0 and partidos.filter(
        estado=Partido.ESTADO_FINALIZADO).count() == total


def pendientes(categoria):
    return (categoria.partidos
            .filter(fase=Partido.FASE_REGULAR)
            .exclude(estado=Partido.ESTADO_FINALIZADO)
            .count())


RONDAS_INICIALES = [
    (Partido.FASE_OCTAVOS, 8),
    (Partido.FASE_CUARTOS, 4),
    (Partido.FASE_SEMIFINAL, 2),
    (Partido.FASE_FINAL, 1),
]

LLAVES_POR_RONDA = dict(RONDAS_INICIALES)

RONDAS_INICIALES_MINI = [
    (Partido.FASE_CUARTOS, 4),
    (Partido.FASE_SEMIFINAL, 2),
]


def equipos_en(categoria, cuadro):
    """Los ids de los equipos que ya juegan ese cuadro de eliminacion."""
    ids = set()
    for local, visitante in (categoria.partidos
                             .filter(cuadro=cuadro, fase__in=Partido.ORDEN_FASES)
                             .values_list('equipo_local_id', 'equipo_visitante_id')):
        ids.update((local, visitante))
    return ids


def equipos_para_sembrar(categoria, cuadro=Partido.CUADRO_PRINCIPAL):
    """Los equipos elegibles para un cuadro: nadie juega los dos a la vez."""
    otro = (Partido.CUADRO_PRINCIPAL if cuadro == Partido.CUADRO_CONSOLACION
            else Partido.CUADRO_CONSOLACION)
    return categoria.equipos.exclude(pk__in=equipos_en(categoria, otro))


def rondas_posibles(categoria, cuadro=Partido.CUADRO_PRINCIPAL):
    """Las rondas con las que se puede arrancar ese cuadro de esta categoria.

    Se ofrece la que quepa con los equipos elegibles: no tiene sentido proponer
    octavos —que pide 16— en una categoria de seis equipos. En una liga con
    mini-liguilla la principal no pasa de los puestos que le dejan a la mini.
    """
    cuantos = equipos_para_sembrar(categoria, cuadro).count()
    if cuadro == Partido.CUADRO_CONSOLACION:
        rondas = rondas_de_la_mini(categoria)
    else:
        rondas = RONDAS_INICIALES
        if relampago.torneo_de(categoria) is None and categoria.mini_liguilla:
            cuantos = min(cuantos, categoria.PUESTOS_ANTES_DE_LA_MINI_LIGUILLA)
    return [(fase, llaves) for fase, llaves in rondas if llaves * 2 <= cuantos]


def rondas_de_la_mini(categoria):
    """En un torneo la mini es libre; en una liga, hasta el tamano que eligio la categoria."""
    if relampago.torneo_de(categoria) is not None:
        return RONDAS_INICIALES_MINI
    return [(fase, llaves) for fase, llaves in RONDAS_INICIALES
            if llaves * 2 <= categoria.mini_liguilla]


def ronda_ya_armada(categoria, cuadro=Partido.CUADRO_PRINCIPAL):
    """La primera fase de eliminacion que ya tiene partidos, o None."""
    for fase in Partido.ORDEN_FASES:
        if categoria.partidos.filter(fase=fase, cuadro=cuadro).exists():
            return fase
    return None


def motivo_para_no_sembrar(categoria, cuadro=Partido.CUADRO_PRINCIPAL):
    """Por que todavia no se puede armar ese cuadro, o '' si ya se puede."""
    if not categoria.juega_por_grupos:
        return 'Esta categoría no se juega por grupos.'
    if not categoria.partidos.filter(fase=Partido.FASE_REGULAR).exists():
        return 'Primero genera los partidos de la fase de grupos.'
    if cuadro == Partido.CUADRO_CONSOLACION:
        rondas = rondas_de_la_mini(categoria)
        if not rondas:
            return 'Esta categoría no juega mini-liguilla. Se elige al editar la categoría.'
        if relampago.torneo_de(categoria) is None and not categoria.admite_mini_liguilla:
            return categoria.motivo_sin_mini_liguilla
        if ronda_ya_armada(categoria) is None:
            return 'Primero arma la liguilla: la mini-liguilla se arma con los que no pasaron.'
        if not rondas_posibles(categoria, cuadro):
            necesarios = min(llaves for _, llaves in rondas) * 2
            return (f'La mini-liguilla necesita {necesarios} equipos que no jueguen '
                    f'la liguilla.')
        return ''
    if not rondas_posibles(categoria):
        return (f'Hacen falta al menos {LLAVES_POR_RONDA[Partido.FASE_FINAL] * 2} '
                f'equipos para armar una liguilla.')
    return ''


def sembrar(categoria, fase, cruces, cuadro=Partido.CUADRO_PRINCIPAL):
    """Arma a mano la primera ronda de un cuadro de eliminacion.

    `cruces` es una lista de pares de Equipo, en el orden del cuadro. De aqui en
    adelante el avance vuelve a ser automatico: los ganadores suben solos, que es
    lo unico que no necesita criterio. Rehacer un cuadro no toca el otro.

    Cada competencia arma con su propio motor: el torneo a partido unico y la
    liga a ida y vuelta, que es con lo que despues la hace avanzar.
    """
    con_siembra = [((local, numero * 2 + 1), (visitante, numero * 2 + 2))
                   for numero, (local, visitante) in enumerate(cruces)]

    Partido.objects.filter(
        categoria=categoria, cuadro=cuadro, fase__in=Partido.ORDEN_FASES).delete()
    motor = relampago if relampago.torneo_de(categoria) is not None else liguilla
    return motor.crear(categoria, fase, con_siembra, cuadro=cuadro)


def campeon(categoria):
    final = categoria.partidos.filter(
        fase=Partido.FASE_FINAL, cuadro=Partido.CUADRO_PRINCIPAL,
        estado=Partido.ESTADO_FINALIZADO).first()
    return final.ganador if final else None


def resumen(categoria):
    """Todo lo que una pantalla necesita saber del estado de la categoria."""
    return {
        'categoria': categoria,
        'grupos': posiciones(categoria),
        'general': tabla.calcular(categoria),
        'jornadas': jornadas(categoria),
        'cerrados': cerrados(categoria),
        'pendientes': pendientes(categoria),
        'cuadro': relampago.cuadro(categoria),
        'mini': relampago.mini(categoria),
        'ronda_armada': ronda_ya_armada(categoria),
        'mini_armada': ronda_ya_armada(categoria, Partido.CUADRO_CONSOLACION),
        'campeon': campeon(categoria),
        'motivo_generar': motivo_para_no_generar(categoria),
        'motivo_sembrar': motivo_para_no_sembrar(categoria),
        'motivo_sembrar_mini': motivo_para_no_sembrar(categoria, Partido.CUADRO_CONSOLACION),
    }