"""Los numeros del perfil de un equipo: lo que se ve al pulsarlo en cualquier pantalla.

Todo sale de lo que el sistema ya guarda: el marcador de cada partido y las
actuaciones de los jugadores. **No hay posesion, tiros, tarjetas, faltas,
corners, minutos jugados ni alineaciones**, porque esos datos no se capturan en
ningun lado. Cualquier metrica de este modulo se puede rastrear hasta una fila
de la base.

Esa es tambien la razon de como esta armado el radar. Un pentagono al estilo de
los videojuegos ("Ataque / Defensa / Fisico / Regate / Velocidad") seria inventado:
tres de esos cinco ejes no tienen dato detras. Los cinco que se usan aca salen
todos de los marcadores y las actuaciones, y en vez de compararse contra un
numero elegido a dedo se comparan **contra el resto de la categoria**: un 80 en
Ataque significa "llega al 80% del mejor ataque de su categoria", que es una
afirmacion que la base puede respaldar.

Este modulo no consulta equipo por equipo para normalizar: se apoya en
`tabla.calcular` y `porteros.calcular`, que resuelven toda la categoria con una
cantidad fija de consultas sin importar cuantos equipos tenga.
"""
import math

from django.db.models import Q, Sum

from apps.estadisticas import porteros, tabla
from apps.partidos import ficha
from apps.partidos.models import Actuacion, Partido
from apps.usuarios.barras import a_paso

CUANTAS_FIGURAS = 3
CUANTOS_DE_RACHA = 5

# Partidos que tiene que haber jugado el equipo para que se dibuje el radar.
# Con uno o dos, los promedios son ruido: un 4-0 de arranque lo deja con el
# mejor ataque de la categoria, y el pentagono lo mostraria como una verdad.
# Tres tampoco es mucho, pero ya alcanza para que un resultado suelto no defina
# la forma entera.
MINIMO_PARA_RADAR = 3

# Los cinco ejes del radar. Cada uno declara como se calcula y hacia donde esta
# lo bueno, para que la normalizacion no tenga que saberlo caso por caso.
#
# La etiqueta corta es la que va sobre el pentagono: "Juego colectivo" al lado
# del vertice derecho se sale del lienzo. La larga se usa en la lista de abajo,
# donde hay ancho de sobra.
#   clave, etiqueta, corta, ayuda (lo que se lee al pasar el mouse), mejor
EJES = [
    ('ataque', 'Ataque', 'Ataque', 'Goles a favor por partido', 'alto'),
    ('defensa', 'Defensa', 'Defensa', 'Goles recibidos por partido', 'bajo'),
    ('efectividad', 'Efectividad', 'Efectividad', 'Puntos sobre los puntos que se podían sacar', 'alto'),
    ('solidez', 'Solidez', 'Solidez', 'Partidos sin recibir goles', 'alto'),
    ('sociedad', 'Juego colectivo', 'Colectivo', 'Asistencias por cada gol del equipo', 'alto'),
]


def armar(equipo):
    """Todo el contenido del perfil, listo para el template."""
    jugados = ficha.juegos(equipo)
    posiciones = tabla.calcular(equipo.categoria)

    from apps.torneos import palmares

    return {
        'equipo': equipo,
        # Los premios de la temporada, si la categoria ya termino.
        'trofeos': palmares.trofeos_de_equipo(equipo),
        'puesto': tabla.puesto_de(posiciones, equipo.id),
        'rendimiento': ficha.rendimiento(jugados),
        'racha': _racha(jugados),
        'distribucion': _distribucion(posiciones, equipo.id),
        'calendario': calendario(equipo),
        'goleadores': ficha.lideres(equipo, 'goles', CUANTAS_FIGURAS),
        'asistidores': ficha.lideres(equipo, 'asistencias', CUANTAS_FIGURAS),
        'radar': radar(equipo, posiciones),
        # Para que la pantalla pueda explicar por que todavia no hay radar en vez
        # de dejar un hueco donde deberia estar.
        'minimo_radar': MINIMO_PARA_RADAR,
        'plantel_total': equipo.jugadores.count(),
        # Un equipo recien inscrito no tiene con que llenar ninguna seccion. Se
        # avisa una vez arriba en vez de repetir "sin datos" cinco veces.
        'sin_jugar': not jugados,
    }


# --------------------------------------------------------------------------
# Calendario del equipo
# --------------------------------------------------------------------------

def calendario(equipo):
    """Todos sus partidos, del mas viejo al mas nuevo: jugados y por jugarse.

    Se devuelven juntos y en orden porque es como se lee un calendario de
    verdad: el historial arriba y lo que viene abajo. Cada fila lleva el id del
    partido para poder abrir su ficha.
    """
    partidos = (
        Partido.objects.filter(Q(equipo_local=equipo) | Q(equipo_visitante=equipo))
        .exclude(estado=Partido.ESTADO_CANCELADO)
        .select_related('equipo_local', 'equipo_visitante', 'categoria', 'categoria__liga', 'sede')
        .order_by('jornada', 'fecha', 'id')
    )

    filas = []
    for partido in partidos:
        de_local = partido.equipo_local_id == equipo.id
        propios = partido.goles_local if de_local else partido.goles_visitante
        ajenos = partido.goles_visitante if de_local else partido.goles_local
        filas.append({
            'partido_id': partido.pk,
            'rival': partido.equipo_visitante if de_local else partido.equipo_local,
            'de_local': de_local,
            'jugado': partido.jugado,
            'propios': propios,
            'ajenos': ajenos,
            'signo': ('G' if propios > ajenos else 'E' if propios == ajenos else 'P') if partido.jugado else '',
            'fecha': partido.fecha,
            # En liguilla vale mas la fase que el numero de jornada: "Semifinal
            # · Ida" dice algo, "Jornada 0" no.
            'etiqueta': partido.etiqueta,
            'competencia': partido.categoria.nombre,
        })
    return filas


def _racha(jugados):
    """Los ultimos resultados, del mas reciente al mas viejo."""
    return [juego['signo'] for juego in reversed(jugados[-CUANTOS_DE_RACHA:])]


def _distribucion(posiciones, equipo_id):
    """Ganados, empatados y perdidos como porcentajes que suman 100.

    Los anchos se calculan aca porque las plantillas de Django no hacen cuentas.

    Van redondeados a multiplos de 5 para poder aplicarlos con las clases
    .ancho-N que ya existen en base.html, en vez de un style inline: es la misma
    convencion que usa la ficha de partido, y de paso evita meter una variable
    de plantilla dentro de un atributo style, que el editor no sabe interpretar
    y marca como error de CSS.

    El sobrante del redondeo se carga sobre el tramo mas grande: si no, tres
    porcentajes redondeados por separado suman 95 o 105 y la barra queda con una
    ranura o se desborda.
    """
    fila = next((f for f in posiciones if f['equipo'].id == equipo_id), None)
    if not fila or not fila['pj']:
        return None

    total = fila['pj']
    tramos = [
        {'clave': 'pg', 'etiqueta': 'Ganados', 'cantidad': fila['pg']},
        {'clave': 'pe', 'etiqueta': 'Empatados', 'cantidad': fila['pe']},
        {'clave': 'pp', 'etiqueta': 'Perdidos', 'cantidad': fila['pp']},
    ]
    for tramo in tramos:
        tramo['ancho'] = a_paso(tramo['cantidad'] * 100 / total)

    sobrante = 100 - sum(t['ancho'] for t in tramos)
    if sobrante:
        mayor = max(tramos, key=lambda t: t['cantidad'])
        mayor['ancho'] += sobrante

    return {'tramos': [t for t in tramos if t['cantidad']], 'total': total}


# --------------------------------------------------------------------------
# Radar
# --------------------------------------------------------------------------

def radar(equipo, posiciones):
    """Los cinco ejes del equipo, normalizados contra su categoria.

    Devuelve None cuando no hay con que compararlo: un equipo solo en su
    categoria, o una categoria donde todavia nadie jugo. Dibujar un pentagono
    lleno en ese caso seria mentir.
    """
    crudos = _metricas_de_la_categoria(equipo.categoria, posiciones)
    # Solo entran los que ya jugaron: el cero de quien no jugo no es un merito
    # ni un demerito, y arruinaria la escala de todos los demas.
    con_datos = {eid: m for eid, m in crudos.items() if m['pj']}
    if equipo.id not in con_datos or len(con_datos) < 2:
        return None
    if con_datos[equipo.id]['pj'] < MINIMO_PARA_RADAR:
        return None

    propias = con_datos[equipo.id]
    ejes = []
    for clave, etiqueta, corta, ayuda, mejor in EJES:
        valores = [m[clave] for m in con_datos.values()]
        puntaje = _normalizar(propias[clave], valores, mejor)
        ejes.append({
            'clave': clave,
            'etiqueta': etiqueta,
            'corta': corta,
            'ayuda': ayuda,
            'valor': propias[clave],
            'puntaje': puntaje,
            # El puntaje exacto es el que se muestra como numero; este otro es el
            # que dibuja la barra, redondeado al paso de las clases .ancho-N. La
            # diferencia no llega a 3 puntos y no se percibe.
            'ancho': a_paso(puntaje),
        })

    return {
        'ejes': ejes,
        'geometria': _geometria(ejes),
        'comparados': len(con_datos),
    }


def _metricas_de_la_categoria(categoria, posiciones):
    """Las cinco metricas crudas de cada equipo de la categoria.

    Se arma con una cantidad fija de consultas: la tabla de posiciones ya trae
    partidos, goles y puntos; `porteros.calcular` trae las porterias a cero; y
    las asistencias salen de una sola agregacion.
    """
    from .models import Equipo

    equipos = Equipo.objects.filter(categoria=categoria)

    # Porterias a cero por equipo. porteros.calcular agrupa por categoria y
    # aca hay una sola, asi que se aplana el unico bloque que devuelve.
    a_cero = {}
    for bloque in porteros.calcular(equipos):
        for fila in bloque['filas']:
            a_cero[fila['equipo'].id] = fila['porterias_cero']

    asistencias = dict(
        Actuacion.objects.filter(
            jugador__equipo__categoria=categoria,
            partido__fase=Partido.FASE_REGULAR,
        )
        .values('jugador__equipo_id')
        .annotate(total=Sum('asistencias'))
        .values_list('jugador__equipo_id', 'total')
    )

    metricas = {}
    for fila in posiciones:
        pj = fila['pj']
        eid = fila['equipo'].id
        metricas[eid] = {
            'pj': pj,
            'ataque': fila['gf'] / pj if pj else 0,
            'defensa': fila['gc'] / pj if pj else 0,
            # El maximo por partido son 3 puntos; el punto extra por penales
            # convierte un empate en 2, nunca en mas de 3.
            'efectividad': fila['pts'] / (pj * 3) if pj else 0,
            'solidez': a_cero.get(eid, 0) / pj if pj else 0,
            # No puede pasar de 1: el sistema no deja cargar mas asistencias que
            # goles (lo valida actuaciones.errores).
            'sociedad': (asistencias.get(eid) or 0) / fila['gf'] if fila['gf'] else 0,
        }
    return metricas


def _normalizar(valor, valores, mejor):
    """Lleva el valor a una escala de 0 a 100 contra el resto de la categoria.

    Se compara contra el mejor de la categoria y no contra el rango completo:
    con el rango, el peor equipo siempre marcaria 0 en todos los ejes aunque
    ande bien, porque alguien tiene que quedar ultimo.

    En los ejes donde lo bueno es el numero mas chico (goles recibidos), se
    invierte la razon: el que menos recibe llega a 100, y el que recibe el doble
    que el mejor se queda en 50.
    """
    if mejor == 'bajo':
        tope = min(valores)
        if valor <= 0:
            return 100
        return round(min(100, tope * 100 / valor))

    tope = max(valores)
    if tope <= 0:
        return 0
    return round(min(100, valor * 100 / tope))


# El lienzo del radar es apaisado y no cuadrado: el pentagono si es simetrico,
# pero las etiquetas de los vertices de los costados se escriben hacia afuera y
# necesitan lugar. Con un lienzo cuadrado, "Efectividad" se salia por la
# derecha y quedaba cortada.
ANCHO = 280
ALTO = 200
CENTRO_X = ANCHO / 2
CENTRO_Y = ALTO / 2
RADIO = 68
# Cuanto se separa la etiqueta del vertice, para no pisar la linea del borde.
AIRE_ETIQUETA = 14
ANILLOS = (25, 50, 75, 100)


def _geometria(ejes):
    """Las coordenadas del SVG, calculadas en Python.

    El template no puede hacer trigonometria, y ademas asi la forma queda
    resuelta de una sola manera en un solo lugar.
    """
    total = len(ejes)
    puntos, vertices, etiquetas = [], [], []

    for indice, eje in enumerate(ejes):
        # Se arranca arriba (-90 grados) y se gira en el sentido del reloj, que
        # es como se lee un pentagono.
        coseno, seno = _direccion(indice, total)

        puntos.append(_punto(coseno, seno, RADIO * eje['puntaje'] / 100))
        vertices.append(_punto(coseno, seno, RADIO))
        x, y = _punto(coseno, seno, RADIO + AIRE_ETIQUETA)
        etiquetas.append({
            'x': x,
            'y': y,
            'texto': eje['corta'],
            'puntaje': eje['puntaje'],
            # Un texto centrado sobre el vertice de un costado se monta encima
            # del pentagono: los de cada lado se escriben hacia afuera.
            'anclaje': 'middle' if abs(coseno) < 0.2 else ('start' if coseno > 0 else 'end'),
        })

    return {
        'area': _cadena(puntos),
        'borde': _cadena(vertices),
        'anillos': [_cadena([_punto(*_direccion(i, total), RADIO * p / 100) for i in range(total)])
                    for p in ANILLOS],
        'radios': vertices,
        'etiquetas': etiquetas,
        'centro_x': CENTRO_X,
        'centro_y': CENTRO_Y,
        'ancho': ANCHO,
        'alto': ALTO,
    }


def _direccion(indice, total):
    angulo = math.radians(-90 + indice * 360 / total)
    return math.cos(angulo), math.sin(angulo)


def _punto(coseno, seno, radio):
    return (round(CENTRO_X + coseno * radio, 1), round(CENTRO_Y + seno * radio, 1))


def _cadena(puntos):
    """Los puntos como los espera el atributo `points` de un <polygon>."""
    return ' '.join(f'{x},{y}' for x, y in puntos)
