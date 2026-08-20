"""Cuadro de eliminación de un torneo: partido único, empate a penales.

Se diferencia de la liguilla de una liga en tres cosas, y por eso vive aparte:

  - Todas las rondas van a partido unico. No hay ida y vuelta.
  - En las rondas de eliminacion el empate se define SIEMPRE en penales.
  - El cuadro no sale de una siembra ganada en el torneo regular: en el formato
    de eliminacion directa sale de un sorteo, y en el de grupos lo arma a mano
    el administrador (ver `apps/partidos/grupos.py`).

El motor trabaja por CATEGORIA, no por torneo. Importa porque un torneo por
grupos lleva varias categorias —una por edad o division— y cada una corre su
propio cuadro sin cruzarse con las demas.

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

DERIVADAS = {
    Partido.FASE_SEMIFINAL: [Partido.FASE_TERCERO, Partido.FASE_FINAL],
}

PRIMER_HORARIO = 9
MINUTOS_ENTRE_PARTIDOS = 45


def ronda_de(cuantos):
    return RONDAS.get(cuantos)


def torneo_de(categoria):
    if categoria is None:
        return None
    return getattr(categoria.liga, 'torneo', None)


def ya_empezo(torneo):
    return torneo is not None and torneo.sorteado


def motivo_para_no_sortear(torneo):
    """Por que este torneo todavia no se puede sortear, o '' si ya se puede."""
    if torneo.es_por_grupos:
        return 'Este torneo se arma por categorías, no con un sorteo general.'
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
        armar(categoria, fase, orden, equipos[uno], equipos[otro], uno + 1, otro + 1)
        for orden, (uno, otro) in enumerate(CRUCES[len(equipos)])
    ]
    _programar_seguido(torneo.fecha, partidos)
    Partido.objects.bulk_create(partidos)
    return partidos


def armar(categoria, fase, orden, local, visitante,
          siembra_local=None, siembra_visitante=None, jornada=0):
    return Partido(
        categoria=categoria,
        fase=fase,
        orden=orden,
        vuelta=False,
        jornada=jornada,
        equipo_local=local,
        equipo_visitante=visitante,
        siembra_local=siembra_local,
        siembra_visitante=siembra_visitante,
    )


def _programar_seguido(dia, partidos, desde=None):
    """Las horas corridas del día, que es lo que hace un relámpago."""
    arranque = desde or timezone.make_aware(
        datetime.datetime.combine(dia, datetime.time(PRIMER_HORARIO, 0)))
    for numero, partido in enumerate(partidos):
        momento = arranque + datetime.timedelta(minutes=MINUTOS_ENTRE_PARTIDOS * numero)
        partido.fecha = momento
        partido.fecha_original = momento


def series(categoria, fase=None):
    """Las llaves del cuadro de una categoria, con el ganador ya resuelto."""
    partidos = (Partido.objects
                .filter(categoria=categoria)
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


def sin_cambios():
    return {'creados': [], 'rehechas': []}


def avanzar(partido):
    """Arma la ronda siguiente cuando la actual termina. Rehace si cambio quien paso."""
    categoria = partido.categoria
    if torneo_de(categoria) is None:
        return sin_cambios()
    if not partido.es_liguilla:
        return sin_cambios()

    ronda = series(categoria, partido.fase)
    if not ronda or any(llave['ganador'] is None for llave in ronda):
        return sin_cambios()

    siguientes = _cruces_siguientes(partido.fase, ronda)
    if not siguientes:
        return sin_cambios()

    creados, rehechas = [], []
    for fase, cruces in siguientes.items():
        parcial = sincronizar(categoria, fase, cruces)
        creados += parcial['creados']
        rehechas += parcial['rehechas']

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


def sincronizar(categoria, fase, cruces):
    """Crea la ronda, o la rehace si cambio quien la juega."""
    existentes = {p.orden: p for p in Partido.objects.filter(
        categoria=categoria, fase=fase)}

    if not existentes:
        return {'creados': crear(categoria, fase, cruces), 'rehechas': []}

    creados, cambio = [], False
    for orden, (uno, otro) in enumerate(cruces):
        actual = existentes.get(orden)
        if actual is None:
            creados += crear(categoria, fase, [(uno, otro)], desde=orden)
            continue
        if {actual.equipo_local_id, actual.equipo_visitante_id} == {uno[0].id, otro[0].id}:
            continue
        actual.delete()
        creados += crear(categoria, fase, [(uno, otro)], desde=orden)
        cambio = True

    rehechas = []
    if cambio:
        rehechas.append(dict(Partido.FASE_CHOICES)[fase])
        derivadas = Partido.objects.filter(
            categoria=categoria, fase__in=DERIVADAS.get(fase, []))
        rehechas += sorted({p.get_fase_display() for p in derivadas})
        derivadas.delete()

    return {'creados': creados, 'rehechas': rehechas}


def crear(categoria, fase, cruces, desde=0):
    partidos = []
    for numero, (uno, otro) in enumerate(cruces, start=desde):
        partidos.append(armar(categoria, fase, numero, uno[0], otro[0], uno[1], otro[1]))
    _programar_siguiente(categoria, partidos)
    Partido.objects.bulk_create(partidos)
    return partidos


def _programar_siguiente(categoria, partidos):
    """Cada ronda arranca donde termino la anterior.

    En el formato por grupos no se programa nada: ahi el administrador le pone
    a cada partido su fecha, su hora y su cancha, que es lo que necesita un
    torneo que dura varios dias y se juega en varias sedes.
    """
    if categoria.juega_por_grupos:
        return

    torneo = torneo_de(categoria)
    if torneo is None:
        return

    ultima = (Partido.objects.filter(categoria=categoria, fecha__isnull=False)
              .order_by('-fecha').first())
    desde = (ultima.fecha + datetime.timedelta(minutes=MINUTOS_ENTRE_PARTIDOS)
             if ultima else None)
    _programar_seguido(torneo.fecha, partidos, desde=desde)


def cuadro(categoria):
    """El cuadro completo de una categoria, en dos mitades que convergen."""
    llaves = series(categoria)
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
        'subtitulo': ('Clasificados de los grupos · el empate se define en penales'
                      if categoria.juega_por_grupos
                      else 'Eliminación directa · el empate se define en penales'),
    }