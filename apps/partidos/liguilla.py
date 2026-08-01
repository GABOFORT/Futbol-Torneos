"""La liguilla: el cuadro de eliminacion que se juega al cerrar el torneo regular.

Arranca cuando la categoria termino todos sus partidos, y siembra a los mejores
de la tabla de posiciones. Se juega a partido unico: si terminan empatados,
pasa el que gana los penales, con el campo `ganador_penales` que el sistema ya
tenia.

El tamano del cuadro se adapta a la categoria, porque no todas tienen la misma
cantidad de equipos:

    8 o mas equipos  -> cuartos de final con los 8 mejores
    entre 4 y 7      -> semifinales con los 4 mejores
    2 o 3            -> final directa entre los dos primeros
    menos de 2       -> no hay liguilla

Cada ronda se genera cuando la anterior termina, no todas de una: hasta que no
se juega un cruce no se sabe quien lo disputa.
"""
from apps.estadisticas import tabla

from .models import Partido

# Como se enfrentan los clasificados en la primera ronda, por posicion en la
# tabla (0 es el primero). El 1o contra el ultimo que entro, el 2o contra el
# anteultimo, y asi: los dos mejores solo se pueden cruzar en la final.
CRUCES_INICIALES = {
    8: [(0, 7), (3, 4), (1, 6), (2, 5)],
    4: [(0, 3), (1, 2)],
    2: [(0, 1)],
}


def formato(categoria):
    """Con cuantos equipos se juega la liguilla y en que ronda arranca.

    Devuelve None cuando la categoria no da ni para una final.
    """
    equipos = categoria.equipos.count()
    if equipos >= 8:
        return {'clasifican': 8, 'fase': Partido.FASE_CUARTOS}
    if equipos >= 4:
        return {'clasifican': 4, 'fase': Partido.FASE_SEMIFINAL}
    if equipos >= 2:
        return {'clasifican': 2, 'fase': Partido.FASE_FINAL}
    return None


def ya_empezo(categoria):
    return Partido.objects.filter(categoria=categoria).exclude(fase=Partido.FASE_REGULAR).exists()


def motivo_para_no_iniciar(categoria):
    """Por que esta categoria no puede arrancar la liguilla, o '' si puede.

    Se devuelve el texto y no un booleano para que la pantalla explique el
    motivo en vez de limitarse a esconder el boton.
    """
    if ya_empezo(categoria):
        return 'La liguilla de esta categoría ya está en marcha.'

    regulares = Partido.objects.filter(categoria=categoria, fase=Partido.FASE_REGULAR)
    if not regulares.exists():
        return 'Todavía no se generaron los partidos del torneo regular.'

    # Un partido cancelado no se va a jugar nunca: no puede frenar la liguilla.
    pendientes = regulares.exclude(
        estado__in=[Partido.ESTADO_FINALIZADO, Partido.ESTADO_CANCELADO]
    ).count()
    if pendientes:
        return f'Faltan {pendientes} partido(s) por jugarse en el torneo regular.'

    if formato(categoria) is None:
        return 'Se necesitan al menos 2 equipos para jugar una liguilla.'
    return ''


def puede_iniciar(categoria):
    return not motivo_para_no_iniciar(categoria)


def iniciar(categoria):
    """Crea la primera ronda con los mejores de la tabla. Devuelve los partidos.

    Los clasificados salen de la tabla del torneo regular, que ya sabe resolver
    puntos, diferencia de gol y el punto extra por penales.
    """
    config = formato(categoria)
    if config is None or ya_empezo(categoria):
        return []

    posiciones = tabla.calcular(categoria)[:config['clasifican']]
    clasificados = [fila['equipo'] for fila in posiciones]

    partidos = [
        # El mejor sembrado juega de local: es la ventaja que se gana en la
        # tabla. La siembra se guarda con el partido porque tambien es lo que
        # desempata si terminan iguales. Va en base 1: el primero es el 1o.
        Partido(
            categoria=categoria,
            fase=config['fase'],
            orden=numero,
            equipo_local=clasificados[mejor],
            equipo_visitante=clasificados[peor],
            siembra_local=mejor + 1,
            siembra_visitante=peor + 1,
            jornada=0,   # la liguilla no es una jornada mas del calendario
        )
        for numero, (mejor, peor) in enumerate(CRUCES_INICIALES[config['clasifican']])
    ]
    Partido.objects.bulk_create(partidos)
    return partidos


def avanzar(partido):
    """Arma la ronda siguiente si este resultado cerro la actual.

    Se llama al guardar cada resultado de liguilla. Mientras falte un cruce por
    definirse no hace nada; cuando se juega el ultimo, deja creada la ronda que
    sigue para que solo haya que ponerle fecha y cancha.

    Devuelve los partidos que creo, o una lista vacia.
    """
    if not partido.es_liguilla:
        return []

    ronda = list(
        Partido.objects.filter(categoria=partido.categoria, fase=partido.fase)
        .select_related('equipo_local', 'equipo_visitante', 'ganador_penales')
        .order_by('orden')
    )
    if any(cruce.ganador is None for cruce in ronda):
        return []   # la ronda todavia no esta resuelta

    if partido.fase == Partido.FASE_CUARTOS:
        return _crear(partido.categoria, Partido.FASE_SEMIFINAL, [
            (_pasa(ronda[0]), _pasa(ronda[1])),
            (_pasa(ronda[2]), _pasa(ronda[3])),
        ])

    if partido.fase == Partido.FASE_SEMIFINAL:
        # La final y el tercer lugar salen juntos de la misma ronda: los que
        # ganan van a una y los que pierden a la otra.
        creados = _crear(partido.categoria, Partido.FASE_TERCERO, [
            (_cae(ronda[0]), _cae(ronda[1])),
        ])
        creados += _crear(partido.categoria, Partido.FASE_FINAL, [
            (_pasa(ronda[0]), _pasa(ronda[1])),
        ])
        return creados

    return []   # el tercer lugar y la final no alimentan nada


def _pasa(cruce):
    """El que avanza, con su siembra a cuestas."""
    return _con_siembra(cruce, cruce.ganador)


def _cae(cruce):
    """El que queda eliminado, con su siembra a cuestas."""
    return _con_siembra(cruce, cruce.perdedor)


def _con_siembra(cruce, equipo):
    """Empareja al equipo con el lugar que saco en la tabla.

    La siembra tiene que viajar de ronda en ronda: es lo que desempata si el
    cruce siguiente tambien termina igualado.
    """
    if equipo is None:
        return (None, None)
    if equipo.id == cruce.equipo_local_id:
        return (equipo, cruce.siembra_local)
    return (equipo, cruce.siembra_visitante)


def _crear(categoria, fase, cruces):
    """Crea los partidos de una fase, salvo que ya existan.

    Cada cruce llega como ((equipo, siembra), (equipo, siembra)). El mejor
    sembrado de los dos queda de local, igual que en la primera ronda.

    La guarda de existencia importa porque corregir un resultado vuelve a
    disparar el avance, y sin ella se duplicaria la ronda siguiente.
    """
    if Partido.objects.filter(categoria=categoria, fase=fase).exists():
        return []

    partidos = []
    for numero, (uno, otro) in enumerate(cruces):
        # Se ordena por siembra para que el mejor reciba de local, que es la
        # ventaja que arrastra desde la tabla.
        local, visitante = sorted([uno, otro], key=lambda par: par[1])
        partidos.append(Partido(
            categoria=categoria, fase=fase, orden=numero, jornada=0,
            equipo_local=local[0], siembra_local=local[1],
            equipo_visitante=visitante[0], siembra_visitante=visitante[1],
        ))
    Partido.objects.bulk_create(partidos)
    return partidos


def cuadro(categoria):
    """El cuadro completo, partido en dos mitades que convergen en la final.

    Se devuelve asi para poder dibujarlo como el cuadro de una liguilla de
    verdad: la mitad de las llaves a la izquierda, la otra mitad a la derecha, y
    la copa al medio. La primera mitad de cada ronda va a la izquierda y la
    segunda a la derecha, que es justo como se alimentan entre si: los cruces 0
    y 1 de cuartos dan la semifinal 0, y los 2 y 3 dan la semifinal 1.

    Dentro de cada ronda los cruces se agrupan de a dos, porque cada par
    desemboca en un mismo cruce de la ronda siguiente y hay que unirlos con una
    linea.
    """
    partidos = list(
        Partido.objects.filter(categoria=categoria)
        .exclude(fase=Partido.FASE_REGULAR)
        .select_related('equipo_local', 'equipo_visitante', 'ganador_penales', 'sede')
        .order_by('orden')
    )
    if not partidos:
        return None

    etiquetas = dict(Partido.FASE_CHOICES)
    izquierda, derecha = [], []

    # La final y el tercer lugar no se reparten: van al centro y abajo.
    for fase in (Partido.FASE_CUARTOS, Partido.FASE_SEMIFINAL):
        cruces = [p for p in partidos if p.fase == fase]
        if not cruces:
            continue
        mitad = len(cruces) // 2 or 1
        for lado, tramo in ((izquierda, cruces[:mitad]), (derecha, cruces[mitad:])):
            if tramo:
                lado.append({
                    'fase': fase,
                    'etiqueta': etiquetas[fase],
                    'pares': [tramo[i:i + 2] for i in range(0, len(tramo), 2)],
                })

    final = next((p for p in partidos if p.fase == Partido.FASE_FINAL), None)
    tercero = next((p for p in partidos if p.fase == Partido.FASE_TERCERO), None)

    return {
        'izquierda': izquierda,
        # Se invierte para dibujarla de adentro hacia afuera: pegada al centro
        # queda la semifinal y en el borde los cuartos, como en el espejo.
        'derecha': list(reversed(derecha)),
        'final': final,
        'tercero': tercero,
        'campeon': final.ganador if final else None,
        'subcampeon': final.perdedor if final else None,
        'tercer_lugar': tercero.ganador if tercero else None,
    }
