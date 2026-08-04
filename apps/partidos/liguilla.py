"""La liguilla: el cuadro de eliminacion que se juega al cerrar el torneo regular.

Arranca cuando la categoria termino todos sus partidos, y siembra a los mejores
de la tabla de posiciones.

**Las rondas de eliminacion se juegan a ida y vuelta.** Cada llave son dos
partidos y pasa el que suma mas goles entre los dos. La llave se identifica con
`fase` + `orden`, y el campo `vuelta` distingue cual de los dos encuentros es.

    Ida     -> de local el peor sembrado
    Vuelta  -> de local el mejor sembrado, que cierra en su cancha

Si el global termina empatado pasa el mejor ubicado en la tabla del torneo
regular: es la ventaja que se gano durante todo el ano.

**La final y el tercer lugar van a partido unico**: son las dos definiciones del
torneo y se juegan en un solo encuentro. En el tercer lugar, si terminan
empatados, el bronce es del mejor sembrado. En la final se patean penales,
porque no se puede coronar campeon con una tabla que ya termino.

El tamano del cuadro se adapta a la categoria, porque no todas tienen la misma
cantidad de equipos:

    8 o mas equipos  -> cuartos de final con los 8 mejores
    entre 4 y 7      -> semifinales con los 4 mejores
    2 o 3            -> final directa entre los dos primeros
    menos de 2       -> no hay liguilla

Cada ronda se genera cuando la anterior termina, no todas de una: hasta que no
se resuelve una llave no se sabe quien juega la siguiente.
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


def es_ida_y_vuelta(fase):
    """Si la fase se juega a doble partido. La lista vive en el modelo."""
    return fase not in Partido.FASES_PARTIDO_UNICO


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

    partidos = []
    for numero, (mejor, peor) in enumerate(CRUCES_INICIALES[config['clasifican']]):
        # La siembra se guarda con el partido porque es lo que desempata si el
        # global termina igualado. Va en base 1: el primero de la tabla es el 1o.
        partidos += _armar_llave(
            categoria, config['fase'], numero,
            (clasificados[mejor], mejor + 1),
            (clasificados[peor], peor + 1),
        )
    Partido.objects.bulk_create(partidos)
    return partidos


def _armar_llave(categoria, fase, orden, mejor, peor):
    """Los partidos de una llave: la ida y la vuelta, o uno solo si no lleva vuelta.

    `mejor` y `peor` llegan como (equipo, siembra), ya ordenados por siembra.

    La ida la recibe el peor sembrado y la vuelta el mejor: cerrar de local es
    la ventaja que se gano en la tabla durante todo el torneo regular.
    """
    def partido(local, visitante, vuelta):
        return Partido(
            categoria=categoria,
            fase=fase,
            orden=orden,
            vuelta=vuelta,
            jornada=0,   # la liguilla no es una jornada mas del calendario
            equipo_local=local[0], siembra_local=local[1],
            equipo_visitante=visitante[0], siembra_visitante=visitante[1],
        )

    if not es_ida_y_vuelta(fase):
        # Partido unico: lo recibe el mejor sembrado.
        return [partido(mejor, peor, False)]

    return [partido(peor, mejor, False), partido(mejor, peor, True)]


def series(categoria, fase=None):
    """Las llaves de la liguilla, con el global y quien paso ya resueltos.

    Una llave son los dos partidos de un mismo (fase, orden). Se devuelve una
    entrada por llave, ordenada como se dibuja el cuadro.

    El global se expresa desde el punto de vista de cada equipo y no de
    local/visitante, porque la localia se invierte entre la ida y la vuelta:
    sumar 'goles_local' de los dos partidos mezclaria a los dos equipos.
    """
    partidos = Partido.objects.filter(categoria=categoria).exclude(fase=Partido.FASE_REGULAR)
    if fase is not None:
        partidos = partidos.filter(fase=fase)
    partidos = partidos.select_related(
        'equipo_local', 'equipo_visitante', 'ganador_penales', 'sede'
    ).order_by('orden', 'vuelta')

    llaves = {}
    for partido in partidos:
        llave = llaves.setdefault((partido.fase, partido.orden), {
            'fase': partido.fase,
            'orden': partido.orden,
            'etiqueta': partido.get_fase_display(),
            'ida': None,
            'vuelta': None,
            'partidos': [],
        })
        llave['vuelta' if partido.vuelta else 'ida'] = partido
        llave['partidos'].append(partido)

    resueltas = [_resolver(llave) for llave in llaves.values()]
    return sorted(resueltas, key=lambda s: (Partido.ORDEN_FASES.index(s['fase']), s['orden']))


def _resolver(llave):
    """Completa una llave con el global, si esta terminada y quien paso."""
    ida, vuelta = llave['ida'], llave['vuelta']
    referencia = ida or vuelta
    # El "uno" de la llave es siempre el mejor sembrado, sin importar de que
    # lado jugo cada partido. Asi el global se lee igual en los dos encuentros.
    if referencia.siembra_local is not None and referencia.siembra_visitante is not None:
        de_local_es_mejor = referencia.siembra_local <= referencia.siembra_visitante
    else:
        de_local_es_mejor = True
    uno = referencia.equipo_local if de_local_es_mejor else referencia.equipo_visitante
    otro = referencia.equipo_visitante if de_local_es_mejor else referencia.equipo_local
    siembra_uno = referencia.siembra_local if de_local_es_mejor else referencia.siembra_visitante
    siembra_otro = referencia.siembra_visitante if de_local_es_mejor else referencia.siembra_local

    esperados = 2 if es_ida_y_vuelta(llave['fase']) else 1
    jugados = [p for p in llave['partidos'] if p.jugado]
    completa = len(jugados) == esperados and len(llave['partidos']) == esperados

    goles_uno = goles_otro = 0
    for partido in jugados:
        if partido.equipo_local_id == uno.id:
            goles_uno += partido.goles_local
            goles_otro += partido.goles_visitante
        else:
            goles_uno += partido.goles_visitante
            goles_otro += partido.goles_local

    ganador = None
    motivo = ''
    if completa:
        if goles_uno > goles_otro:
            ganador = uno
        elif goles_otro > goles_uno:
            ganador = otro
        elif llave['fase'] == Partido.FASE_FINAL:
            # La final no se puede coronar por una tabla que ya termino: se
            # patea al terminar la vuelta.
            ultimo = vuelta or ida
            ganador = ultimo.ganador_penales
            if ganador:
                motivo = 'Se definió desde el punto penal'
        else:
            # El resto de las rondas las decide la tabla del torneo regular: es
            # la ventaja que el equipo se gano durante todo el ano.
            ganador = uno   # `uno` es, por construccion, el mejor sembrado
            motivo = f'Global empatado: pasa el {siembra_uno}º de la tabla'

    llave.update({
        'uno': uno, 'otro': otro,
        'siembra_uno': siembra_uno, 'siembra_otro': siembra_otro,
        'goles_uno': goles_uno, 'goles_otro': goles_otro,
        'completa': completa,
        'ganador': ganador,
        'perdedor': (otro if ganador and ganador.id == uno.id else uno) if ganador else None,
        'motivo': motivo,
        'a_partido_unico': not es_ida_y_vuelta(llave['fase']),
    })
    return llave


# Que rondas dejan de valer cuando una se rehace. Si cambia un semifinalista,
# la final y el tercer lugar que salian de ahi tampoco sirven. El tercer lugar y
# la final no alimentan nada, asi que no arrastran a nadie.
DERIVADAS = {
    Partido.FASE_SEMIFINAL: [Partido.FASE_TERCERO, Partido.FASE_FINAL],
}


def avanzar(partido):
    """Arma la ronda siguiente, o la rehace si cambio quien paso.

    Se llama al guardar cada resultado de liguilla. Mientras falte un cruce por
    definirse no hace nada; cuando se juega el ultimo, deja creada la ronda que
    sigue para que solo haya que ponerle fecha y cancha.

    Si el resultado que se guardo era una **correccion** y cambio el ganador, la
    ronda siguiente ya existe pero con el equipo equivocado. En ese caso se
    borra y se vuelve a armar. Sin esto, un error de tipeo en cuartos dejaba a
    un equipo jugando una semifinal que no gano, y al final del camino un
    campeon que nunca lo fue.

    Rehacer una ronda **borra sus fechas, canchas y resultados**: son de cruces
    que no van a existir. Por eso se devuelve que se rehizo, para poder avisarlo.

    Devuelve {'creados': [...], 'rehechas': ['Semifinal', ...]}.
    """
    if not partido.es_liguilla:
        return {'creados': [], 'rehechas': []}

    # La ronda son sus llaves, no sus partidos: hasta que no se juegan la ida y
    # la vuelta no se sabe quien paso.
    ronda = series(partido.categoria, partido.fase)
    if any(llave['ganador'] is None for llave in ronda):
        return {'creados': [], 'rehechas': []}   # la ronda todavia no esta resuelta

    siguientes = _cruces_siguientes(partido.fase, ronda)
    if not siguientes:
        return {'creados': [], 'rehechas': []}   # el tercer lugar y la final no alimentan nada

    creados, rehechas = [], []
    for fase, cruces in siguientes.items():
        existentes = {}
        for p in Partido.objects.filter(categoria=partido.categoria, fase=fase):
            existentes.setdefault(p.orden, []).append(p)

        if not existentes:
            creados += _crear(partido.categoria, fase, cruces)
            continue

        # Se revisa llave por llave y no la ronda entera: si cambio una sola,
        # la otra semifinal sigue siendo valida y no tiene por que perder su
        # fecha, su cancha y su resultado.
        cambio_alguno = False
        for numero, (uno, otro) in enumerate(cruces):
            de_la_llave = existentes.get(numero, [])
            mejor, peor = sorted([uno, otro], key=lambda par: par[1] or 99)
            if not de_la_llave:
                creados += _crear_llave(partido.categoria, fase, numero, mejor, peor)
                continue
            actuales = {de_la_llave[0].equipo_local_id, de_la_llave[0].equipo_visitante_id}
            if actuales == {mejor[0].id, peor[0].id}:
                continue   # son los mismos dos: no hay nada que rehacer
            # Cambiaron los protagonistas: se borra la llave entera y se rearma,
            # porque la localia de la ida y la vuelta depende de las siembras.
            Partido.objects.filter(pk__in=[p.pk for p in de_la_llave]).delete()
            creados += _crear_llave(partido.categoria, fase, numero, mejor, peor)
            cambio_alguno = True

        if cambio_alguno:
            rehechas.append(dict(Partido.FASE_CHOICES)[fase])
            # Las rondas que salian de esta ya no valen: se armaron con un
            # resultado que acaba de borrarse.
            derivadas = Partido.objects.filter(
                categoria=partido.categoria, fase__in=DERIVADAS.get(fase, [])
            )
            rehechas += sorted({p.get_fase_display() for p in derivadas})
            derivadas.delete()

    return {'creados': creados, 'rehechas': rehechas}


def _crear_llave(categoria, fase, orden, mejor, peor):
    """Crea la ida y la vuelta de una llave que falta dentro de una ronda existente."""
    partidos = _armar_llave(categoria, fase, orden, mejor, peor)
    Partido.objects.bulk_create(partidos)
    return partidos


def _cruces_siguientes(fase, ronda):
    """Como quedarian las rondas que alimenta esta, con los resultados de hoy.

    Devuelve {fase: [cruce, ...]} en el orden en que se juegan. Vacio cuando la
    fase no alimenta ninguna.
    """
    if fase == Partido.FASE_CUARTOS:
        return {
            Partido.FASE_SEMIFINAL: [
                (_pasa(ronda[0]), _pasa(ronda[1])),
                (_pasa(ronda[2]), _pasa(ronda[3])),
            ],
        }
    if fase == Partido.FASE_SEMIFINAL:
        # La final y el tercer lugar salen juntos de la misma ronda: los que
        # ganan van a una y los que pierden a la otra.
        return {
            Partido.FASE_TERCERO: [(_cae(ronda[0]), _cae(ronda[1]))],
            Partido.FASE_FINAL: [(_pasa(ronda[0]), _pasa(ronda[1]))],
        }
    return {}


def _pasa(llave):
    """El que avanza, con su siembra a cuestas."""
    return _con_siembra(llave, llave['ganador'])


def _cae(llave):
    """El que queda eliminado, con su siembra a cuestas."""
    return _con_siembra(llave, llave['perdedor'])


def _con_siembra(llave, equipo):
    """Empareja al equipo con el lugar que saco en la tabla.

    La siembra tiene que viajar de ronda en ronda: es lo que desempata si la
    llave siguiente tambien termina igualada, y ademas decide quien cierra de
    local.
    """
    if equipo is None:
        return (None, None)
    if equipo.id == llave['uno'].id:
        return (equipo, llave['siembra_uno'])
    return (equipo, llave['siembra_otro'])


def _crear(categoria, fase, cruces):
    """Crea las llaves de una fase, salvo que ya existan.

    Cada cruce llega como ((equipo, siembra), (equipo, siembra)).

    La guarda de existencia importa porque corregir un resultado vuelve a
    disparar el avance, y sin ella se duplicaria la ronda siguiente.
    """
    if Partido.objects.filter(categoria=categoria, fase=fase).exists():
        return []

    partidos = []
    for numero, (uno, otro) in enumerate(cruces):
        mejor, peor = sorted([uno, otro], key=lambda par: par[1] or 99)
        partidos += _armar_llave(categoria, fase, numero, mejor, peor)
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
    from apps.torneos import palmares

    llaves = series(categoria)
    if not llaves:
        return None

    # Los premios de la temporada, si ya termino: van al lado del nombre de cada
    # equipo dentro de la llave. Una sola consulta para todo el cuadro.
    de_equipos = palmares.trofeos_por_categoria([categoria.id if hasattr(categoria, 'id') else categoria])
    de_equipos = next(iter(de_equipos.values()), {}).get('equipos', {})
    for llave in llaves:
        llave['trofeos_uno'] = de_equipos.get(llave['uno'].nombre, [])
        llave['trofeos_otro'] = de_equipos.get(llave['otro'].nombre, [])

    etiquetas = dict(Partido.FASE_CHOICES)
    izquierda, derecha = [], []

    # La final y el tercer lugar no se reparten: van al centro y abajo.
    for fase in (Partido.FASE_CUARTOS, Partido.FASE_SEMIFINAL):
        cruces = [s for s in llaves if s['fase'] == fase]
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

    final = next((s for s in llaves if s['fase'] == Partido.FASE_FINAL), None)
    tercero = next((s for s in llaves if s['fase'] == Partido.FASE_TERCERO), None)

    return {
        'izquierda': izquierda,
        # Se invierte para dibujarla de adentro hacia afuera: pegada al centro
        # queda la semifinal y en el borde los cuartos, como en el espejo.
        'derecha': list(reversed(derecha)),
        'final': final,
        'tercero': tercero,
        'campeon': final['ganador'] if final else None,
        'subcampeon': final['perdedor'] if final else None,
        'tercer_lugar': tercero['ganador'] if tercero else None,
    }
