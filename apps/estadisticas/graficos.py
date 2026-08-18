"""Los numeros de la pantalla de graficos: goles por jornada, ataque y defensa.

Todo sale de una sola pasada sobre los partidos terminados. Se agrega en Python
y no con `annotate` sobre relaciones porque los goles de un equipo estan
repartidos en dos columnas —`goles_local` cuando recibe y `goles_visitante`
cuando visita— y unir las dos relaciones en una consulta multiplica las filas.
Ya paso una vez con las vallas de la portada.

**Solo el torneo regular**, igual que la tabla de posiciones y las porterias:
los partidos de liguilla son de otra competencia y moverian los promedios
despues de que el torneo termino.

Los graficos se dibujan con barras de CSS y no con una libreria: el proyecto no
tiene ninguna, meter una por cuatro graficos de barras seria pagar 200 KB y una
dependencia externa por algo que es un `width` en porcentaje.
"""
from apps.equipos.models import Equipo
from apps.partidos.models import Partido
from apps.usuarios.barras import a_paso, reparto

TOPE = 10

MINIMO = 4


def _vacio():
    return {
        'hay_datos': False,
        'partidos': 0, 'goles': 0, 'promedio': 0,
        'por_jornada': [], 'ofensivos': [], 'defensivos': [],
        'resultados': {'local': 0, 'empate': 0, 'visitante': 0},
        'mas_goleado': None,
    }


def calcular(ligas, categoria=None):
    """Los datos de todos los graficos, en dos consultas.

    `categoria` acota a una sola competencia. Sin ella se mezclan todas las
    visibles: sirve para mirar el panorama, aunque las jornadas de categorias
    distintas no sean el mismo dia.
    """
    consulta = Partido.objects.filter(
        categoria__liga__in=ligas,
        estado=Partido.ESTADO_FINALIZADO,
        fase=Partido.FASE_REGULAR,
    )
    if categoria is not None:
        consulta = consulta.filter(categoria=categoria)

    filas = list(consulta.values_list(
        'jornada', 'equipo_local_id', 'equipo_visitante_id',
        'goles_local', 'goles_visitante',
    ))
    if not filas:
        return _vacio()

    jornadas = {}
    equipos = {}
    resultados = {'local': 0, 'empate': 0, 'visitante': 0}
    goles_totales = 0

    for jornada, local, visitante, gl, gv in filas:
        goles_totales += gl + gv

        fecha = jornadas.setdefault(jornada, {'goles': 0, 'partidos': 0})
        fecha['goles'] += gl + gv
        fecha['partidos'] += 1

        for equipo_id, favor, contra in ((local, gl, gv), (visitante, gv, gl)):
            fila = equipos.setdefault(equipo_id, {'pj': 0, 'gf': 0, 'gc': 0})
            fila['pj'] += 1
            fila['gf'] += favor
            fila['gc'] += contra

        if gl > gv:
            resultados['local'] += 1
        elif gl < gv:
            resultados['visitante'] += 1
        else:
            resultados['empate'] += 1

    nombres = {
        e.id: e for e in Equipo.objects.filter(pk__in=equipos)
        .select_related('categoria', 'liga')
    }

    comparables = [
        {
            'equipo': nombres[eid],
            'pj': datos['pj'],
            'gf': datos['gf'],
            'gc': datos['gc'],
            'promedio_gf': round(datos['gf'] / datos['pj'], 2),
            'promedio_gc': round(datos['gc'] / datos['pj'], 2),
        }
        for eid, datos in equipos.items()
        if eid in nombres and datos['pj'] >= MINIMO
    ]

    ofensivos = sorted(comparables, key=lambda f: (-f['promedio_gf'], -f['pj']))[:TOPE]
    defensivos = sorted(comparables, key=lambda f: (f['promedio_gc'], -f['pj']))[:TOPE]

    por_jornada = [
        {
            'jornada': numero,
            'goles': datos['goles'],
            'partidos': datos['partidos'],
            'promedio': round(datos['goles'] / datos['partidos'], 2),
        }
        for numero, datos in sorted(jornadas.items())
    ]

    return {
        'hay_datos': True,
        'partidos': len(filas),
        'goles': goles_totales,
        'promedio': round(goles_totales / len(filas), 2),
        'por_jornada': _con_altura(por_jornada, 'goles'),
        'ofensivos': _con_altura(ofensivos, 'promedio_gf'),
        'defensivos': _con_altura(defensivos, 'promedio_gc', invertir=True),
        'resultados': _porcentajes(resultados, len(filas)),
        'mas_goleado': max(comparables, key=lambda f: f['promedio_gc'], default=None),
    }


def _con_altura(filas, campo, invertir=False):
    """Agrega a cada fila el porcentaje que le toca en la barra.

    Con `invertir`, el mejor es el mas chico —los goles recibidos— y la barra
    mas larga tiene que ser la del que menos recibio, no la del que mas.

    El valor sale redondeado al paso de las clases `.ancho-N` / `.alto-N`: en
    este proyecto las barras no llevan la medida en un `style` inline. El numero
    exacto se muestra escrito al lado de cada barra.
    """
    if not filas:
        return filas
    valores = [f[campo] for f in filas]
    tope = max(valores) or 1
    piso = min(valores)
    for fila in filas:
        if invertir:
            rango = tope - piso or 1
            fila['altura'] = a_paso(100 - (fila[campo] - piso) * 75 / rango)
        else:
            fila['altura'] = a_paso(fila[campo] * 100 / tope)
    return filas


def _porcentajes(resultados, total):
    """Los tres tramos de la barra: cantidad, porcentaje escrito y ancho de clase.

    El **porcentaje** es el valor exacto redondeado, que es el que se lee; el
    **ancho** va al paso de 5 de las clases `.ancho-N` y se reparte con
    `barras.reparto`, que le da el sobrante al tramo mas grande para que los
    tres sumen 100 y la barra no se desborde.
    """
    anchos = reparto(list(resultados.items()), total)
    return {
        clave: {
            'cantidad': cantidad,
            'porcentaje': round(cantidad * 100 / total) if total else 0,
            'ancho': anchos[clave],
        }
        for clave, cantidad in resultados.items()
    }
