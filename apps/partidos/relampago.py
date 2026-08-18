"""Cuadro de un torneo relámpago: un día, eliminación directa, partido único.

Se diferencia de la liguilla de una liga en tres cosas, y por eso vive aparte:

  - Todas las rondas van a partido unico. No hay ida y vuelta.
  - El empate se define SIEMPRE en penales, en cualquier ronda. Aqui no hay
    tabla de posiciones de la que sacar un mejor sembrado.
  - El cuadro sale de un sorteo, no de una siembra ganada en el torneo regular.

Lo que si se reusa es el resto del sistema: los equipos, los jugadores, la ficha
de partido, las actuaciones y el dibujo del cuadro.
"""
import datetime
import random

from django.utils import timezone

from .models import Partido

RONDAS = {
    16: Partido.FASE_OCTAVOS,
    8: Partido.FASE_CUARTOS,
    4: Partido.FASE_SEMIFINAL,
    2: Partido.FASE_FINAL,
}

CRUCES = {
    16: [(0, 15), (7, 8), (3, 12), (4, 11), (1, 14), (6, 9), (2, 13), (5, 10)],
    8: [(0, 7), (3, 4), (1, 6), (2, 5)],
    4: [(0, 3), (1, 2)],
    2: [(0, 1)],
}

PRIMER_HORARIO = 9
MINUTOS_ENTRE_PARTIDOS = 45


def ronda_de(cuantos):
    return RONDAS.get(cuantos)


def ya_empezo(torneo):
    categoria = torneo.categoria
    return categoria is not None and categoria.partidos.exists()


def motivo_para_no_sortear(torneo):
    """Por que este torneo todavia no se puede sortear, o '' si ya se puede."""
    if ya_empezo(torneo):
        return 'El cuadro de este torneo ya está sorteado.'
    if torneo.categoria is None:
        return 'El torneo no tiene categoría. Vuelve a crearlo.'
    faltan = torneo.faltan
    if faltan:
        return (
            f'Faltan {faltan} equipo(s): el torneo se juega con '
            f'{torneo.equipos} y hay {torneo.inscritos}.'
        )
    return ''


def puede_sortear(torneo):
    return not motivo_para_no_sortear(torneo)


def sortear(torneo, semilla=None):
    """Arma la primera ronda con un sorteo al azar. Devuelve los partidos."""
    if not puede_sortear(torneo):
        return []

    categoria = torneo.categoria
    equipos = list(categoria.equipos.all())
    random.Random(semilla).shuffle(equipos)

    fase = ronda_de(len(equipos))
    partidos = [
        _armar(categoria, fase, orden, equipos[uno], equipos[otro], uno + 1, otro + 1)
        for orden, (uno, otro) in enumerate(CRUCES[len(equipos)])
    ]
    _programar(torneo, partidos)
    Partido.objects.bulk_create(partidos)
    return partidos


def _armar(categoria, fase, orden, local, visitante, siembra_local, siembra_visitante):
    return Partido(
        categoria=categoria,
        fase=fase,
        orden=orden,
        vuelta=False,
        jornada=0,
        equipo_local=local,
        equipo_visitante=visitante,
        siembra_local=siembra_local,
        siembra_visitante=siembra_visitante,
    )


def _programar(torneo, partidos):
    """Las horas corridas del día, que es lo que hace un relámpago."""
    inicio = datetime.datetime.combine(torneo.fecha, datetime.time(PRIMER_HORARIO, 0))
    for numero, partido in enumerate(partidos):
        momento = timezone.make_aware(
            inicio + datetime.timedelta(minutes=MINUTOS_ENTRE_PARTIDOS * numero))
        partido.fecha = momento
        partido.fecha_original = momento


def series(torneo, fase=None):
    """Las llaves del cuadro, con el ganador ya resuelto."""
    partidos = (Partido.objects
                .filter(categoria=torneo.categoria)
                .exclude(fase=Partido.FASE_REGULAR)
                .select_related('equipo_local', 'equipo_visitante', 'ganador_penales', 'sede'))
    if fase is not None:
        partidos = partidos.filter(fase=fase)

    llaves = []
    for partido in partidos.order_by('orden'):
        llaves.append({
            'fase': partido.fase,
            'orden': partido.orden,
            'etiqueta': partido.get_fase_display(),
            'partido': partido,
            'partidos': [partido],
            'a_partido_unico': True,
            'uno': partido.equipo_local,
            'otro': partido.equipo_visitante,
            'siembra_uno': partido.siembra_local,
            'siembra_otro': partido.siembra_visitante,
            'goles_uno': partido.goles_local,
            'goles_otro': partido.goles_visitante,
            'trofeos_uno': [],
            'trofeos_otro': [],
            'completa': partido.jugado,
            'ganador': _ganador(partido),
            'perdedor': _perdedor(partido),
            'motivo': 'Se definió desde el punto penal' if partido.empatado else '',
        })
    return sorted(llaves, key=lambda s: (Partido.ORDEN_FASES.index(s['fase']), s['orden']))


def _ganador(partido):
    """Quien paso. Con el marcador empatado manda la tanda, sin excepciones."""
    if not partido.jugado:
        return None
    if partido.goles_local > partido.goles_visitante:
        return partido.equipo_local
    if partido.goles_local < partido.goles_visitante:
        return partido.equipo_visitante
    return partido.ganador_penales


def _perdedor(partido):
    ganador = _ganador(partido)
    if ganador is None:
        return None
    return (partido.equipo_visitante if ganador.id == partido.equipo_local_id
            else partido.equipo_local)


DERIVADAS = {
    Partido.FASE_SEMIFINAL: [Partido.FASE_TERCERO, Partido.FASE_FINAL],
}


def avanzar(partido):
    """Arma la ronda siguiente cuando la actual termina. Rehace si cambio quien paso."""
    if not partido.es_liguilla:
        return {'creados': [], 'rehechas': []}

    torneo = getattr(partido.categoria.liga, 'torneo', None)
    if torneo is None:
        return {'creados': [], 'rehechas': []}

    ronda = series(torneo, partido.fase)
    if not ronda or any(llave['ganador'] is None for llave in ronda):
        return {'creados': [], 'rehechas': []}

    siguientes = _cruces_siguientes(partido.fase, ronda)
    if not siguientes:
        return {'creados': [], 'rehechas': []}

    creados, rehechas = [], []
    for fase, cruces in siguientes.items():
        existentes = {p.orden: p for p in Partido.objects.filter(
            categoria=torneo.categoria, fase=fase)}

        if not existentes:
            creados += _crear(torneo, fase, cruces)
            continue

        cambio = False
        for orden, (uno, otro) in enumerate(cruces):
            actual = existentes.get(orden)
            if actual is None:
                creados += _crear(torneo, fase, [(uno, otro)], desde=orden)
                continue
            if {actual.equipo_local_id, actual.equipo_visitante_id} == {uno[0].id, otro[0].id}:
                continue
            actual.delete()
            creados += _crear(torneo, fase, [(uno, otro)], desde=orden)
            cambio = True

        if cambio:
            rehechas.append(dict(Partido.FASE_CHOICES)[fase])
            derivadas = Partido.objects.filter(
                categoria=torneo.categoria, fase__in=DERIVADAS.get(fase, []))
            rehechas += sorted({p.get_fase_display() for p in derivadas})
            derivadas.delete()

    return {'creados': creados, 'rehechas': rehechas}


def _cruces_siguientes(fase, ronda):
    if fase == Partido.FASE_OCTAVOS:
        return {Partido.FASE_CUARTOS: _emparejar(ronda)}
    if fase == Partido.FASE_CUARTOS:
        return {Partido.FASE_SEMIFINAL: _emparejar(ronda)}
    if fase == Partido.FASE_SEMIFINAL:
        return {
            Partido.FASE_TERCERO: [(_cae(ronda[0]), _cae(ronda[1]))],
            Partido.FASE_FINAL: [(_pasa(ronda[0]), _pasa(ronda[1]))],
        }
    return {}


def _emparejar(ronda):
    """Los ganadores de a dos, en el orden del cuadro."""
    pasan = [_pasa(llave) for llave in ronda]
    return [(pasan[i], pasan[i + 1]) for i in range(0, len(pasan) - 1, 2)]


def _pasa(llave):
    return (llave['ganador'], llave['partido'].siembra_local
            if llave['ganador'] and llave['ganador'].id == llave['partido'].equipo_local_id
            else llave['partido'].siembra_visitante)


def _cae(llave):
    return (llave['perdedor'], llave['partido'].siembra_local
            if llave['perdedor'] and llave['perdedor'].id == llave['partido'].equipo_local_id
            else llave['partido'].siembra_visitante)


def _crear(torneo, fase, cruces, desde=0):
    partidos = []
    for numero, (uno, otro) in enumerate(cruces, start=desde):
        partidos.append(_armar(
            torneo.categoria, fase, numero, uno[0], otro[0], uno[1], otro[1]))
    _programar_siguiente(torneo, fase, partidos)
    Partido.objects.bulk_create(partidos)
    return partidos


def _programar_siguiente(torneo, fase, partidos):
    """Cada ronda arranca donde termino la anterior, el mismo día."""
    ultima = (Partido.objects.filter(categoria=torneo.categoria, fecha__isnull=False)
              .order_by('-fecha').first())
    arranque = (ultima.fecha + datetime.timedelta(minutes=MINUTOS_ENTRE_PARTIDOS)
                if ultima else timezone.make_aware(datetime.datetime.combine(
                    torneo.fecha, datetime.time(PRIMER_HORARIO, 0))))
    for numero, partido in enumerate(partidos):
        momento = arranque + datetime.timedelta(minutes=MINUTOS_ENTRE_PARTIDOS * numero)
        partido.fecha = momento
        partido.fecha_original = momento


def cuadro(torneo):
    """El cuadro completo, en dos mitades que convergen en la final."""
    llaves = series(torneo)
    if not llaves:
        return None

    izquierda, derecha = [], []
    for fase in (Partido.FASE_OCTAVOS, Partido.FASE_CUARTOS, Partido.FASE_SEMIFINAL):
        cruces = [s for s in llaves if s['fase'] == fase]
        if not cruces:
            continue
        mitad = len(cruces) // 2 or 1
        for lado, tramo in ((izquierda, cruces[:mitad]), (derecha, cruces[mitad:])):
            if tramo:
                lado.append({
                    'fase': fase,
                    'etiqueta': tramo[0]['etiqueta'],
                    'pares': [tramo[i:i + 2] for i in range(0, len(tramo), 2)],
                })

    final = next((s for s in llaves if s['fase'] == Partido.FASE_FINAL), None)
    tercero = next((s for s in llaves if s['fase'] == Partido.FASE_TERCERO), None)

    return {
        'izquierda': izquierda,
        'derecha': list(reversed(derecha)),
        'final': final,
        'tercero': tercero,
        'campeon': final['ganador'] if final else None,
        'subcampeon': final['perdedor'] if final else None,
        'tercer_lugar': tercero['ganador'] if tercero else None,
        'es_mini': False,
        'titulo': 'Cuadro del torneo',
        'subtitulo': 'Eliminación directa · el empate se define en penales',
    }
