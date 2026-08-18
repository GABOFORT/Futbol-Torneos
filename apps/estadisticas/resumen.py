"""El panorama de una liga: sus numeros y el estado de cada categoria.

Es lo que se ve al entrar a Estadisticas antes de elegir una categoria. Hasta
ahora esa pantalla era una lista de nombres, y no decia nada: ni quien va
primero, ni cuanto falta para que termine el torneo.

Dos decisiones que ordenan todo el modulo:

**La regla de los puntos no se reescribe aca.** El lider de cada categoria sale
de `tabla.calcular()`, que es donde vive esa regla para todo el sistema. Rehacerla
con un `annotate` habria sido mas rapido en consultas y habria abierto la puerta a
que la tabla de posiciones y esta pantalla dijeran cosas distintas.

**Nada inventado.** Cada numero sale de marcadores y actuaciones cargadas. El
sistema no captura posesion, tiros, faltas ni tarjetas, asi que no se muestran.

**El vacio se explica.** De poco sirve un tablero en cero: cuando falta un dato,
en vez del numero se devuelve que hay que hacer para tenerlo ('Carga las
plantillas', 'Asigna fechas'). Es la misma idea de `motivo_para_no_iniciar()`.
"""
import math

from django.db.models import Count, Q, Sum

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.partidos.models import Actuacion, Partido
from apps.torneos.models import Categoria, Palmares

from . import porteros, tabla
from apps.usuarios.barras import a_paso


def panorama(ligas):
    """Una ficha por liga para la pantalla de seleccion, en 6 consultas fijas.

    No se llama `panel()` en un bucle a proposito: serian una docena de consultas
    por liga y con siete ligas la pantalla se iria a mas de cien. Aca todo se
    agrupa por liga en una sola pasada, asi que agregar ligas no agrega consultas.
    """
    ligas = list(ligas)
    if not ligas:
        return []
    ids = [liga.id for liga in ligas]

    partidos = _agrupado(
        Partido.objects.filter(categoria__liga_id__in=ids).values('categoria__liga'),
        clave='categoria__liga',
        totales=Count('id'),
        jugados=Count('id', filter=Q(estado=Partido.ESTADO_FINALIZADO)),
        goles_casa=Sum('goles_local'),
        goles_fuera=Sum('goles_visitante'),
        sin_fecha=Count('id', filter=Q(fecha__isnull=True)),
    )
    equipos = _agrupado(
        Equipo.objects.filter(liga_id__in=ids).values('liga'),
        clave='liga', cuantos=Count('id'),
    )
    jugadores = _agrupado(
        Jugador.objects.filter(equipo__liga_id__in=ids).values('equipo__liga'),
        clave='equipo__liga', cuantos=Count('id'),
    )
    categorias = _agrupado(
        Categoria.objects.filter(liga_id__in=ids, activa=True).values('liga'),
        clave='liga', cuantas=Count('id'), cupo=Sum('cupo_equipos'),
        cerradas=Count('id', filter=Q(cerrada=True)),
    )
    campeones = {}
    for fila in Palmares.objects.filter(categoria__liga_id__in=ids).values(
            'categoria__liga', 'categoria_nombre', 'campeon'):
        campeones.setdefault(fila['categoria__liga'], []).append(
            {'categoria': fila['categoria_nombre'], 'campeon': fila['campeon']})

    fichas = []
    for liga in ligas:
        p = partidos.get(liga.id, {})
        c = categorias.get(liga.id, {})
        totales, jugados = p.get('totales', 0), p.get('jugados', 0)
        goles = (p.get('goles_casa') or 0) + (p.get('goles_fuera') or 0)
        avance = _porcentaje(jugados, totales)

        fichas.append({
            'liga': liga,
            'categorias': c.get('cuantas', 0),
            'equipos': equipos.get(liga.id, {}).get('cuantos', 0),
            'cupo': c.get('cupo') or 0,
            'jugadores': jugadores.get(liga.id, {}).get('cuantos', 0),
            'partidos': totales,
            'jugados': jugados,
            'sin_fecha': p.get('sin_fecha', 0),
            'goles': goles,
            'goles_por_partido': round(goles / jugados, 1) if jugados else None,
            'avance': avance,
            'anillo': _anillo(avance),
            'estado': _estado_de_liga(liga, c, totales, jugados),
            'campeones': campeones.get(liga.id, []),
            'pendiente': _pendiente_de_liga(liga, c, equipos.get(liga.id, {}), totales),
        })
    return fichas


def _estado_de_liga(liga, categorias, totales, jugados):
    if liga.cerrada:
        return {'clave': 'concluida', 'texto': 'Concluida'}
    if not categorias.get('cuantas'):
        return {'clave': 'espera', 'texto': 'Sin categorías'}
    if not totales:
        return {'clave': 'espera', 'texto': 'Sin calendario'}
    if jugados >= totales:
        return {'clave': 'listo', 'texto': 'Calendario completo'}
    if jugados:
        return {'clave': 'juego', 'texto': 'En juego'}
    return {'clave': 'inscripcion', 'texto': 'Por comenzar'}


def _pendiente_de_liga(liga, categorias, equipos, totales):
    """El siguiente paso de la liga, o '' si ya esta andando."""
    if liga.cerrada:
        return ''
    if not categorias.get('cuantas'):
        return 'Todavía no tiene categorías.'
    if not equipos.get('cuantos'):
        return 'Todavía no tiene equipos inscritos.'
    if not totales:
        return 'Falta generar el calendario.'
    return ''


def _anillo(porcentaje, radio=26):
    """El recorte del trazo para dibujar el avance como un anillo."""
    vuelta = 2 * math.pi * radio
    return {
        'radio': radio,
        'vuelta': round(vuelta, 2),
        'corte': round(vuelta * (1 - porcentaje / 100), 2),
    }


def _agrupado(consulta, clave, **agregados):
    """Pasa un values().annotate() a {id: {campo: valor}}."""
    return {
        fila.pop(clave): fila
        for fila in consulta.annotate(**agregados)
    }


def panel(liga):
    """Los numeros de cabecera de la liga, en una consulta por bloque.

    Se resuelve con agregados y no recorriendo categorias: son cifras totales y
    no dependen de la tabla de posiciones.
    """
    partidos = Partido.objects.filter(categoria__liga=liga)
    conteo = partidos.aggregate(
        totales=Count('id'),
        jugados=Count('id', filter=Q(estado=Partido.ESTADO_FINALIZADO)),
        sin_fecha=Count('id', filter=Q(fecha__isnull=True)),
        goles=Sum('goles_local') or 0,
        goles_visita=Sum('goles_visitante') or 0,
    )
    goles = (conteo['goles'] or 0) + (conteo['goles_visita'] or 0)
    jugados = conteo['jugados']

    equipos = Equipo.objects.filter(liga=liga)
    cupo = sum(c.cupo_equipos for c in liga.categorias.all())

    jugadores = Jugador.objects.filter(equipo__liga=liga).count()
    sin_plantilla = equipos.annotate(cuantos=Count('jugadores')).filter(cuantos=0).count()

    de_penal = Actuacion.objects.filter(
        jugador__equipo__liga=liga
    ).aggregate(total=Sum('goles_de_penal'))['total'] or 0
    por_default = partidos.filter(no_se_presento__isnull=False).count()

    return {
        'equipos': equipos.count(),
        'cupo': cupo,
        'jugadores': jugadores,
        'equipos_sin_plantilla': sin_plantilla,
        'partidos': conteo['totales'],
        'jugados': jugados,
        'sin_fecha': conteo['sin_fecha'],
        'avance': _porcentaje(jugados, conteo['totales']),
        'goles': goles,
        'goles_por_partido': round(goles / jugados, 1) if jugados else None,
        'goles_de_penal': de_penal,
        'por_default': por_default,
    }


def tarjetas(liga):
    """Una tarjeta por categoria: quien va primero, cuanto falta y su goleador.

    Cuesta dos consultas por categoria (las de `tabla.calcular`) mas dos fijas
    para los goleadores y los conteos. Con la decena larga de categorias que
    maneja una liga es despreciable, y a cambio la regla de los puntos sigue
    escrita una sola vez.
    """
    categorias = list(liga.categorias.filter(activa=True).order_by('nombre'))
    if not categorias:
        return []

    goleadores = _goleador_por_categoria(categorias)
    conteos = _conteos_por_categoria(categorias)

    salida = []
    for categoria in categorias:
        datos = conteos.get(categoria.id, {})
        jugados, totales = datos.get('jugados', 0), datos.get('totales', 0)

        posiciones = tabla.calcular(categoria) if jugados else []
        lider = next((fila for fila in posiciones if fila['pj']), None)

        salida.append({
            'categoria': categoria,
            'estado': _estado(categoria, jugados, totales),
            'equipos': datos.get('equipos', 0),
            'cupo': categoria.cupo_equipos,
            'jugados': jugados,
            'totales': totales,
            'avance': _porcentaje(jugados, totales),
            'jornada': datos.get('jornada'),
            'jornadas': datos.get('jornadas'),
            'lider': lider,
            'goleador': goleadores.get(categoria.id),
            'pendiente': _pendiente(categoria, datos),
        })
    return salida


def rankings(categoria, tope=10):
    """Goleadores, asistidores y porterias de una categoria, ya recortados.

    Van al lado de la tabla de posiciones y no en una pantalla aparte: quien
    mira una categoria quiere ver quien va primero y quien mete los goles de una
    sola vez, sin navegar y volver.

    Como la liga y la categoria ya estan elegidas al llegar aca, las filas traen
    solo el jugador y su numero: repetir la liga y la categoria en cada renglon
    seria ruido.
    """
    goles = _top_jugadores(categoria, 'goles', tope)
    asistencias = _top_jugadores(categoria, 'asistencias', tope)

    bloques = porteros.calcular(Equipo.objects.filter(categoria=categoria))
    vallas = bloques[0]['filas'][:tope] if bloques else []

    return {
        'goleadores': goles,
        'asistidores': asistencias,
        'vallas': [fila for fila in vallas if fila['pj']],
    }


def _top_jugadores(categoria, campo, tope):
    """Los que mas suman en un campo de Actuacion, de mayor a menor."""
    filas = (
        Actuacion.objects
        .filter(jugador__equipo__categoria=categoria, **{f'{campo}__gt': 0})
        .values('jugador__nombre', 'jugador__apellido', 'jugador__equipo__nombre')
        .annotate(total=Sum(campo))
        .order_by('-total', 'jugador__apellido')[:tope]
    )
    return [
        {
            'nombre': f"{fila['jugador__nombre']} {fila['jugador__apellido']}".strip(),
            'equipo': fila['jugador__equipo__nombre'],
            'total': fila['total'],
        }
        for fila in filas
    ]


def _estado(categoria, jugados, totales):
    """En que momento de su vida esta la categoria.

    El orden de las preguntas importa: una categoria concluida tambien tiene la
    inscripcion cerrada, y preguntar por la inscripcion primero la mostraria como
    si estuviera por arrancar.
    """
    if categoria.cerrada:
        return {'clave': 'concluida', 'texto': 'Concluida'}
    if Partido.objects.filter(categoria=categoria).exclude(fase=Partido.FASE_REGULAR).exists():
        return {'clave': 'liguilla', 'texto': 'En liguilla'}
    if categoria.inscripcion_abierta:
        return {'clave': 'inscripcion', 'texto': 'Inscripción abierta'}
    if not totales:
        return {'clave': 'espera', 'texto': 'Sin calendario'}
    if jugados >= totales:
        return {'clave': 'listo', 'texto': 'Torneo regular terminado'}
    return {'clave': 'juego', 'texto': 'En juego'}


def _pendiente(categoria, datos):
    """Que le falta a esta categoria para mostrar algo, o '' si no le falta nada.

    Devuelve el siguiente paso concreto en vez de un cartel de 'sin datos': quien
    mira la pantalla casi siempre es quien puede resolverlo.
    """
    if categoria.cerrada:
        return ''
    if not datos.get('equipos'):
        return 'Todavía no tiene equipos inscritos.'
    if categoria.inscripcion_abierta:
        return 'Cierra la inscripción para poder generar el calendario.'
    if not datos.get('totales'):
        return 'Ya puedes generar los partidos.'
    if not datos.get('jugados'):
        return 'Aún no se juega ningún partido.'
    return ''


def _conteos_por_categoria(categorias):
    """Equipos, partidos y jornadas de cada categoria, en dos consultas."""
    ids = [c.id for c in categorias]

    partidos = (
        Partido.objects.filter(categoria_id__in=ids)
        .values('categoria_id')
        .annotate(
            totales=Count('id'),
            jugados=Count('id', filter=Q(estado=Partido.ESTADO_FINALIZADO)),
            jornadas=Count('jornada', distinct=True, filter=Q(fase=Partido.FASE_REGULAR)),
            jugadas=Count(
                'jornada', distinct=True,
                filter=Q(fase=Partido.FASE_REGULAR, estado=Partido.ESTADO_FINALIZADO),
            ),
        )
    )
    equipos = (
        Equipo.objects.filter(categoria_id__in=ids)
        .values('categoria_id').annotate(cuantos=Count('id'))
    )

    datos = {cid: {} for cid in ids}
    for fila in partidos:
        datos[fila['categoria_id']].update({
            'totales': fila['totales'], 'jugados': fila['jugados'],
            'jornadas': fila['jornadas'], 'jornada': fila['jugadas'],
        })
    for fila in equipos:
        datos[fila['categoria_id']]['equipos'] = fila['cuantos']
    return datos


def _goleador_por_categoria(categorias):
    """El maximo anotador de cada categoria, en una sola consulta.

    Los goles en contra no cuentan: suben el marcador del rival y nunca la tabla
    de goleo, igual que en `Partido._asignados`.
    """
    filas = (
        Actuacion.objects
        .filter(jugador__equipo__categoria__in=categorias, goles__gt=0)
        .values('jugador__equipo__categoria_id', 'jugador__nombre',
                'jugador__apellido', 'jugador__equipo__nombre')
        .annotate(total=Sum('goles'))
        .order_by('jugador__equipo__categoria_id', '-total')
    )

    mejores = {}
    for fila in filas:
        cid = fila['jugador__equipo__categoria_id']
        if cid in mejores:
            continue
        mejores[cid] = {
            'nombre': f"{fila['jugador__nombre']} {fila['jugador__apellido']}".strip(),
            'equipo': fila['jugador__equipo__nombre'],
            'goles': fila['total'],
        }
    return mejores


def _porcentaje(parte, total):
    """El avance en porcentaje, al paso de las clases `.ancho-N`.

    Va al paso de 5 y no al entero exacto porque este numero dibuja una barra, y
    en este proyecto las barras no llevan la medida en un `style` inline: la
    llevan en una clase. El detalle exacto se lee en el texto de al lado
    ('12 de 17 partidos'), que si es preciso.
    """
    return a_paso(parte * 100 / total) if total else 0
