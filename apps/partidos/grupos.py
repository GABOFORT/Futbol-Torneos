"""Fase de grupos de una categoría de torneo.

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
from apps.estadisticas import tabla

from . import calendario, relampago
from .models import Partido

MINIMO_POR_GRUPO = 2


def motivo_para_no_generar(categoria):
    """Por que no se pueden generar los partidos de grupos, o '' si ya se puede."""
    if not categoria.juega_por_grupos:
        return 'Esta categoría no se juega por grupos.'
    if categoria.partidos.exists():
        return 'Los partidos de esta categoría ya están generados.'

    reparto = categoria.reparto
    flacos = [f'grupo {letra} ({cuantos})'
              for letra, cuantos in reparto.items() if cuantos < MINIMO_POR_GRUPO]
    if flacos:
        return (f'Cada grupo necesita al menos {MINIMO_POR_GRUPO} equipos. '
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
        equipos = list(categoria.equipos.filter(grupo=letra).order_by('id'))
        for numero, jornada in enumerate(calendario.armar_jornadas(equipos), start=1):
            por_jornada.setdefault(numero, []).extend(jornada)
            libre = _el_que_descansa(equipos, jornada)
            if libre is not None:
                descansan.setdefault(numero, []).append(libre)

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


def rondas_posibles(categoria):
    """Las rondas con las que se puede arrancar la liguilla de esta categoria.

    Se ofrece la que quepa con los equipos inscritos: no tiene sentido proponer
    octavos —que pide 16— en una categoria de seis equipos.
    """
    cuantos = categoria.equipos.count()
    return [(fase, llaves) for fase, llaves in RONDAS_INICIALES
            if llaves * 2 <= cuantos]


def ronda_ya_armada(categoria):
    """La primera fase de eliminacion que ya tiene partidos, o None."""
    for fase in Partido.ORDEN_FASES:
        if categoria.partidos.filter(fase=fase).exists():
            return fase
    return None


def motivo_para_no_sembrar(categoria):
    """Por que todavia no se puede armar la liguilla, o '' si ya se puede."""
    if not categoria.juega_por_grupos:
        return 'Esta categoría no se juega por grupos.'
    if not categoria.partidos.filter(fase=Partido.FASE_REGULAR).exists():
        return 'Primero genera los partidos de la fase de grupos.'
    if not rondas_posibles(categoria):
        return (f'Hacen falta al menos {LLAVES_POR_RONDA[Partido.FASE_FINAL] * 2} '
                f'equipos para armar una liguilla.')
    return ''


def sembrar(categoria, fase, cruces):
    """Arma a mano la primera ronda de la liguilla.

    `cruces` es una lista de pares de Equipo, en el orden del cuadro. De aqui en
    adelante el avance vuelve a ser automatico: los ganadores suben solos, que es
    lo unico que no necesita criterio.
    """
    con_siembra = [((local, numero * 2 + 1), (visitante, numero * 2 + 2))
                   for numero, (local, visitante) in enumerate(cruces)]

    Partido.objects.filter(
        categoria=categoria, fase__in=Partido.ORDEN_FASES).delete()
    return relampago.crear(categoria, fase, con_siembra)


def campeon(categoria):
    final = categoria.partidos.filter(
        fase=Partido.FASE_FINAL, estado=Partido.ESTADO_FINALIZADO).first()
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
        'ronda_armada': ronda_ya_armada(categoria),
        'campeon': campeon(categoria),
        'motivo_generar': motivo_para_no_generar(categoria),
        'motivo_sembrar': motivo_para_no_sembrar(categoria),
    }