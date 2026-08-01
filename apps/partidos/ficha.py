"""Los numeros de la ficha de un partido.

Todo sale de lo que el sistema ya guarda: el marcador de cada partido y las
actuaciones de los jugadores. No hay posesion, disparos, atajadas ni goles
esperados porque esos datos nunca se capturan; la ficha muestra unicamente lo
que la base puede respaldar.
"""
from django.db.models import Q, Sum

from apps.estadisticas import tabla
from apps.jugadores.models import Jugador

from .models import Partido

# Las lineas van de la delantera al arco para dibujarlas sobre la cancha de
# arriba hacia abajo, igual que se ve un equipo desde la tribuna.
LINEAS = [
    ('delantero', 'Delanteros'),
    ('medio', 'Mediocampistas'),
    ('defensa', 'Defensas'),
    ('portero', 'Porteros'),
]

CUANTOS_ULTIMOS = 5


def armar(partido):
    """Todo el contenido de la ficha, listo para el template.

    Casi todas las secciones muestran lo mismo para los dos equipos, uno al lado
    del otro. Por eso se devuelve `lados`, con un bloque completo por equipo: el
    template recorre esa lista una vez por seccion en vez de repetir el mismo
    marcado cambiandole el sufijo local/visitante.
    """
    posiciones = tabla.calcular(partido.categoria)
    lo_ocurrido = sucesos(partido) if partido.jugado else {'local': None, 'visitante': None}

    lados = []
    for donde, equipo in (('local', partido.equipo_local), ('visitante', partido.equipo_visitante)):
        juegos = _juegos(equipo)
        lados.append({
            'donde': donde,
            'equipo': equipo,
            'rendimiento': rendimiento(juegos),
            'ultimos': ultimos(juegos),
            'puesto': tabla.puesto_de(posiciones, equipo.id),
            'figuras': figuras(equipo),
            'plantel': plantel(equipo),
            'sucesos': lo_ocurrido[donde],
        })

    return {
        'lados': lados,
        'comparativa': comparativa(lados[0]['rendimiento'], lados[1]['rendimiento']),
        'sin_rendimiento': lados[0]['rendimiento']['sin_datos'] and lados[1]['rendimiento']['sin_datos'],
        'hay_puestos': any(lado['puesto'] for lado in lados),
        'hay_figuras': any(lado['figuras'] for lado in lados),
        'hay_sucesos': partido.jugado and lo_ocurrido.get('hay_algo', False),
        'historial': historial(partido),
    }


def _juegos(equipo):
    """Los partidos ya jugados del equipo, vistos desde su lado.

    Se resuelve aca de que lado jugo cada uno para que el resto del modulo no
    tenga que preguntarse en cada cuenta si era local o visitante.
    """
    partidos = Partido.objects.filter(
        Q(equipo_local=equipo) | Q(equipo_visitante=equipo),
        estado=Partido.ESTADO_FINALIZADO,
    ).select_related('equipo_local', 'equipo_visitante').order_by('jornada', 'fecha', 'id')

    juegos = []
    for partido in partidos:
        de_local = partido.equipo_local_id == equipo.id
        propios = partido.goles_local if de_local else partido.goles_visitante
        ajenos = partido.goles_visitante if de_local else partido.goles_local
        juegos.append({
            # El id va porque cada renglon de los ultimos cinco se puede pulsar
            # para abrir la ficha de ese partido.
            'partido_id': partido.pk,
            'jornada': partido.jornada,
            'rival': partido.equipo_visitante if de_local else partido.equipo_local,
            'de_local': de_local,
            'propios': propios,
            'ajenos': ajenos,
            'signo': 'G' if propios > ajenos else ('E' if propios == ajenos else 'P'),
        })
    return juegos


def rendimiento(juegos):
    """Promedios del equipo en el torneo, a partir de sus marcadores."""
    jugados = len(juegos)
    if not jugados:
        # Un equipo recien inscrito no tiene con que promediar. Se devuelven
        # ceros para que la ficha se dibuje igual, marcada como sin datos.
        return {
            'jugados': 0, 'goles_favor': 0, 'goles_contra': 0,
            'favor_promedio': 0, 'contra_promedio': 0, 'diferencia_promedio': 0,
            'porterias_cero': 0, 'sin_datos': True,
        }

    favor = sum(juego['propios'] for juego in juegos)
    contra = sum(juego['ajenos'] for juego in juegos)
    return {
        'jugados': jugados,
        'goles_favor': favor,
        'goles_contra': contra,
        'favor_promedio': favor / jugados,
        'contra_promedio': contra / jugados,
        'diferencia_promedio': (favor - contra) / jugados,
        'porterias_cero': sum(1 for juego in juegos if juego['ajenos'] == 0),
        'sin_datos': False,
    }


# Cada metrica dice cuantos decimales mostrar y hacia donde esta lo bueno:
# en goles concedidos gana el numero mas chico, no el mas grande.
METRICAS = [
    ('Goles a favor por juego', 'favor_promedio', 2, 'alto'),
    ('Goles concedidos por juego', 'contra_promedio', 2, 'bajo'),
    ('Diferencia promedio de goles', 'diferencia_promedio', 2, 'alto'),
    ('Porterías a cero', 'porterias_cero', 0, 'alto'),
    ('Partidos jugados', 'jugados', 0, None),
]


def comparativa(uno, otro):
    """Las filas del comparativo, con el ancho de cada barra ya resuelto.

    El ancho se calcula aca y no en el template porque las plantillas de Django
    no hacen cuentas, y ademas asi la regla queda en un solo lugar.
    """
    filas = []
    for etiqueta, clave, decimales, mejor in METRICAS:
        izquierda, derecha = uno[clave], otro[clave]
        filas.append({
            'etiqueta': etiqueta,
            'valor_uno': _con_decimales(izquierda, decimales),
            'valor_otro': _con_decimales(derecha, decimales),
            'ancho_uno': _ancho(izquierda, derecha),
            'ancho_otro': _ancho(derecha, izquierda),
            'gana_uno': _gana(izquierda, derecha, mejor),
            'gana_otro': _gana(derecha, izquierda, mejor),
        })
    return filas


def _con_decimales(valor, decimales):
    return f'{valor:.{decimales}f}'


# El ancho de las barras sale redondeado a multiplos de 5 porque en el template
# se aplica con una clase (.ancho-45) y no con un style inline: son 21 clases en
# vez de 101, y la diferencia con el valor exacto no llega a los 3 puntos.
PASO_ANCHO = 5


def _ancho(valor, contrario):
    """Cuanto de la barra le toca a este valor, en porcentaje.

    Los dos valores se reparten el 100%. La diferencia de goles puede ser
    negativa, asi que primero se desplazan ambos hasta que el menor quede en
    cero: lo que se compara es la distancia entre uno y otro, no el signo.
    """
    piso = min(0, valor, contrario)
    propio = valor - piso
    total = propio + (contrario - piso)
    if total <= 0:
        return 50
    return round(propio * 100 / total / PASO_ANCHO) * PASO_ANCHO


def _gana(valor, contrario, mejor):
    """Si este lado es el mejor de los dos en esa metrica."""
    if mejor == 'alto':
        return valor > contrario
    if mejor == 'bajo':
        return valor < contrario
    return False


def ultimos(juegos):
    """Los ultimos partidos del equipo, del mas reciente al mas viejo."""
    return list(reversed(juegos[-CUANTOS_ULTIMOS:]))


def historial(partido):
    """Los enfrentamientos anteriores entre los dos clubes de este partido.

    Se buscan por nombre y no por id a proposito: un mismo club se inscribe en
    varias categorias de la liga, y en cada una es un registro de Equipo
    distinto. Para el cara a cara siguen siendo el mismo club.

    El partido que se esta mirando queda afuera: lo que interesa es con que
    antecedentes llegan, no repetir el marcador que ya esta en la cabecera.
    """
    local, visitante = partido.equipo_local, partido.equipo_visitante

    previos = Partido.objects.filter(
        Q(equipo_local__nombre=local.nombre, equipo_visitante__nombre=visitante.nombre)
        | Q(equipo_local__nombre=visitante.nombre, equipo_visitante__nombre=local.nombre),
        categoria__liga=local.liga,
        estado=Partido.ESTADO_FINALIZADO,
    ).exclude(pk=partido.pk).select_related('categoria', 'equipo_local').order_by('-jornada', '-fecha')

    cruces, gano_local, empates, gano_visitante = [], 0, 0, 0
    for previo in previos:
        # 'uno' es siempre el club que hoy juega de local, sin importar de que
        # lado estuvo aquella vez.
        uno_de_local = previo.equipo_local.nombre == local.nombre
        goles_uno = previo.goles_local if uno_de_local else previo.goles_visitante
        goles_otro = previo.goles_visitante if uno_de_local else previo.goles_local

        if goles_uno > goles_otro:
            gano_local += 1
        elif goles_uno < goles_otro:
            gano_visitante += 1
        else:
            empates += 1

        cruces.append({
            # Igual que en los ultimos cinco: el cruce se puede pulsar para
            # abrir la ficha de aquel partido.
            'partido_id': previo.pk,
            'categoria': previo.categoria,
            'jornada': previo.jornada,
            'fecha': previo.fecha,
            'goles_uno': goles_uno,
            'goles_otro': goles_otro,
            'uno_de_local': uno_de_local,
        })

    return {
        'cruces': cruces,
        'total': len(cruces),
        'gano_local': gano_local,
        'empates': empates,
        'gano_visitante': gano_visitante,
    }


def figuras(equipo):
    """El goleador y el asistente mas destacados del equipo en el torneo.

    Devuelve una lista y no un dict con claves fijas para que el template la
    recorra sin tener que preguntar por cada rol: si un equipo no tiene
    asistencias cargadas, ese renglon simplemente no viene.
    """
    destacados = []
    for rol, campo in (('Goleador', 'goles'), ('Asistencias', 'asistencias')):
        lider = _lider(equipo, campo)
        if lider:
            destacados.append({'rol': rol, **lider})
    return destacados


def _lider(equipo, campo):
    """Quien mas suma en ese campo. None si nadie sumo todavia."""
    fila = (
        Jugador.objects.filter(equipo=equipo)
        .annotate(total=Sum(f'actuaciones__{campo}'))
        .filter(total__gt=0)
        .order_by('-total')
        .first()
    )
    if fila is None:
        return None
    return {'jugador': fila, 'total': fila.total}


def plantel(equipo):
    """El plantel repartido por linea, de la delantera al arco.

    Es como esta armado el equipo, no quienes jugaron: el sistema no registra la
    alineacion de cada partido. Los dados de baja quedan afuera; los lesionados
    y sancionados se muestran, porque siguen siendo parte del plantel.
    """
    jugadores = (
        equipo.jugadores.exclude(estado=Jugador.ESTADO_BAJA)
        .order_by('numero', 'apellido', 'nombre')
    )

    lineas = []
    for clave, etiqueta in LINEAS:
        de_la_linea = [jugador for jugador in jugadores if jugador.posicion == clave]
        if de_la_linea:
            lineas.append({'clave': clave, 'etiqueta': etiqueta, 'jugadores': de_la_linea})
    return lineas


def sucesos(partido):
    """Quien anoto y quien asistio en este partido, separado por equipo.

    Los goles en contra se muestran del lado del jugador que los hizo y no del
    equipo que se beneficio: es donde el lector los busca.
    """
    marcador = {
        'local': {'goles': [], 'asistencias': []},
        'visitante': {'goles': [], 'asistencias': []},
    }

    for actuacion in partido.actuaciones.select_related('jugador').all():
        lado = 'local' if actuacion.jugador.equipo_id == partido.equipo_local_id else 'visitante'
        if actuacion.goles:
            marcador[lado]['goles'].append({
                'jugador': actuacion.jugador, 'cantidad': actuacion.goles, 'en_contra': False,
            })
        if actuacion.goles_en_contra:
            marcador[lado]['goles'].append({
                'jugador': actuacion.jugador, 'cantidad': actuacion.goles_en_contra, 'en_contra': True,
            })
        if actuacion.asistencias:
            marcador[lado]['asistencias'].append({
                'jugador': actuacion.jugador, 'cantidad': actuacion.asistencias,
            })

    marcador['hay_algo'] = any(
        marcador[lado][que] for lado in ('local', 'visitante') for que in ('goles', 'asistencias')
    )
    return marcador
