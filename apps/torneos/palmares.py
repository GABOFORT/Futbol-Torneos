"""Cierre de una categoria y armado de su palmares.

Cuando se carga el resultado de la final, la categoria queda terminada: se
congela quien gano y la categoria pasa a solo lectura. Cuando todas las
categorias de una liga estan cerradas, la liga tambien se cierra.

El palmares se guarda **congelado** y no se calcula al vuelo. La tabla de
posiciones y las de goleo se recalculan con cada consulta: si el superadmin
corrige un resultado viejo, el campeon podria cambiar solo. Un palmares es un
hecho historico, no una consulta. Ademas tiene que sobrevivir al borrado de la
liga, que es lo unico que queda para mostrar de esa temporada.

Los premios individuales (bota de oro y trofeo de asistencias) son del mejor de
la categoria sin importar de que equipo sea: los gana quien mas anoto o mas
asistio, aunque su equipo no haya salido campeon. El guante de oro es el unico
premio de equipo.

Los empates se premian compartidos en los tres. Desempatar por un criterio
inventado seria decidir por el reglamento de la liga, que no le toca al sistema.
"""
from django.db.models import Sum
from django.utils import timezone

from apps.estadisticas import porteros, tabla
from apps.jugadores.models import Jugador
from apps.partidos.models import Actuacion, Partido

SEPARADOR = ' / '


def cerrar_si_termino(partido):
    """Cierra la categoria si este resultado termino de definir la final.

    Se llama al guardar cada resultado, igual que `liguilla.avanzar`. Devuelve
    el Palmares si cerro o actualizo algo, o None.

    La final se juega a ida y vuelta, asi que no alcanza con que este partido
    este jugado: la categoria recien termina cuando la serie tiene ganador.

    Solo la final del cuadro principal cierra la categoria: la mini-liguilla
    tambien tiene una fase 'final' y no corona al campeon del torneo.
    """
    from apps.partidos import liguilla

    if partido.fase != Partido.FASE_FINAL or not partido.jugado:
        return None
    if partido.cuadro != Partido.CUADRO_PRINCIPAL:
        return None
    if partido.es_de_torneo:
        return None

    final = next(
        (s for s in liguilla.series(partido.categoria, Partido.FASE_FINAL)), None
    )
    if final is None or final['ganador'] is None:
        return None
    return cerrar(partido.categoria)


def cerrar_torneo_si_termino(partido):
    """Graba el palmarés de un torneo relámpago cuando se juega su final.

    Es el equivalente de `cerrar_si_termino` para los relámpago, que no tienen
    temporada: el podio sale del cuadro y no hay tabla final que congelar.

    **En un relámpago solo se premia a los equipos.** No hay bota de oro, ni
    guante de oro, ni trofeo de asistencias: son distinciones de temporada, y
    aqui un jugador puede levantarlas con tres partidos en una tarde.
    """
    from apps.partidos import relampago
    from .models import Palmares

    if partido.fase != Partido.FASE_FINAL or not partido.jugado:
        return None

    torneo = getattr(partido.categoria.liga, 'torneo', None)
    if torneo is None:
        return None

    cuadro = relampago.cuadro(torneo)
    if cuadro is None or cuadro['campeon'] is None:
        return None

    categoria = torneo.categoria
    datos = {
        'liga_nombre': torneo.nombre,
        'categoria_nombre': f'Relámpago · {torneo.equipos} equipos',
        'es_torneo': True,
        'campeon': cuadro['campeon'].nombre,
        'subcampeon': cuadro['subcampeon'].nombre if cuadro['subcampeon'] else '',
        'tercero': cuadro['tercer_lugar'].nombre if cuadro['tercer_lugar'] else '',
        'goleadores': '',
        'goles_del_goleador': 0,
        'asistidores': '',
        'asistencias_del_asistidor': 0,
        'vallas': '',
        'goles_recibidos': 0,
        'tabla_final': [],
    }

    existente = Palmares.objects.filter(categoria=categoria).first()
    if existente:
        cambios = [c for c, valor in datos.items() if getattr(existente, c) != valor]
        if cambios:
            for campo, valor in datos.items():
                setattr(existente, campo, valor)
            existente.save(update_fields=list(datos))
        return existente
    return Palmares.objects.create(categoria=categoria, **datos)


def reabrir(categoria):
    """Deshace el cierre: la categoria vuelve a estar en juego.

    Hace falta cuando se corrige un resultado de semifinales y cambia quien
    llega a la final: la final vieja se borra, asi que el campeon que se habia
    declarado ya no existe. Dejar el palmares seria dejar una copa a un equipo
    que no jugo la final.

    Tambien reabre la liga, que pudo haberse cerrado con esta categoria.
    """
    from .models import Palmares

    borrados, _ = Palmares.objects.filter(categoria=categoria).delete()
    if not categoria.cerrada and not borrados:
        return False

    categoria.cerrada = False
    categoria.fecha_cierre = None
    categoria.save(update_fields=['cerrada', 'fecha_cierre'])

    liga = categoria.liga
    if liga.cerrada:
        liga.cerrada = False
        liga.fecha_cierre = None
        liga.save(update_fields=['cerrada', 'fecha_cierre'])
    return True


def cerrar(categoria):
    """Marca la categoria como cerrada y le graba el palmares.

    Si ya tenia palmares se recalcula: puede que el superadmin haya corregido el
    resultado de la final y el campeon sea otro. Se conserva la fila y su fecha
    de cierre original, porque la categoria termino cuando termino; lo que se
    corrige es quien gano.
    """
    from .models import Palmares

    datos = calcular(categoria)

    existente = Palmares.objects.filter(categoria=categoria).first()
    if existente:
        cambios = [c for c, valor in datos.items() if getattr(existente, c) != valor]
        if cambios:
            for campo, valor in datos.items():
                setattr(existente, campo, valor)
            existente.save(update_fields=list(datos))
        return existente

    palmares = Palmares.objects.create(categoria=categoria, **calcular(categoria))

    categoria.cerrada = True
    categoria.fecha_cierre = timezone.now()
    categoria.inscripcion_abierta = False
    categoria.save(update_fields=['cerrada', 'fecha_cierre', 'inscripcion_abierta'])

    cerrar_liga_si_termino(categoria.liga)
    return palmares


def cerrar_liga_si_termino(liga):
    """Cierra la liga cuando ya no le queda ninguna categoria en juego.

    Solo cuentan las categorias activas: una desactivada no deberia impedir que
    la liga termine.
    """
    if liga.cerrada:
        return False
    pendientes = liga.categorias.filter(activa=True, cerrada=False).exists()
    if pendientes:
        return False

    liga.cerrada = True
    liga.fecha_cierre = timezone.now()
    liga.save(update_fields=['cerrada', 'fecha_cierre'])
    return True


def calcular(categoria):
    """Los datos del palmares de una categoria, listos para guardar."""
    posiciones = tabla.calcular(categoria)
    goleadores, goles = _mejores_jugadores(categoria, 'goles')
    asistidores, asistencias = _mejores_jugadores(categoria, 'asistencias')
    vallas, recibidos = _mejores_vallas(categoria)

    return {
        'liga_nombre': categoria.liga.nombre,
        'categoria_nombre': categoria.nombre,
        'campeon': _nombre_del_puesto(categoria, 1),
        'subcampeon': _nombre_del_puesto(categoria, 2),
        'tercero': _nombre_del_puesto(categoria, 3),
        'goleadores': SEPARADOR.join(goleadores),
        'goles_del_goleador': goles,
        'asistidores': SEPARADOR.join(asistidores),
        'asistencias_del_asistidor': asistencias,
        'vallas': SEPARADOR.join(vallas),
        'goles_recibidos': recibidos,
        'tabla_final': [
            {
                'puesto': numero,
                'equipo': fila['equipo'].nombre,
                'pj': fila['pj'], 'pg': fila['pg'], 'pe': fila['pe'], 'pp': fila['pp'],
                'gf': fila['gf'], 'gc': fila['gc'], 'dg': fila['dg'], 'pts': fila['pts'],
            }
            for numero, fila in enumerate(posiciones, start=1)
        ],
    }


def _nombre_del_puesto(categoria, puesto):
    """El campeon, el subcampeon o el tercero, sacados del cuadro de liguilla.

    Salen del cuadro y no de la tabla de posiciones a proposito: el campeon es
    el que gano la final, no el que termino primero en la fase regular. Si la
    categoria no llego a jugar liguilla, no hay podio que declarar.
    """
    from apps.partidos import liguilla

    cuadro = liguilla.cuadro(categoria)
    if not cuadro:
        return ''
    equipo = {1: cuadro['campeon'], 2: cuadro['subcampeon'], 3: cuadro['tercer_lugar']}[puesto]
    return equipo.nombre if equipo else ''


def _mejores_jugadores(categoria, campo):
    """Los jugadores que mas suman en ese campo, y cuanto.

    Se cuenta todo el torneo, liguilla incluida: un gol en la final es un gol.
    Va al reves que la tabla de posiciones, que excluye la liguilla porque mide
    el todos contra todos.

    Devuelve ([nombres], total). Lista vacia si nadie sumo.
    """
    filas = (
        Jugador.objects.filter(equipo__categoria=categoria)
        .annotate(total=Sum(f'actuaciones__{campo}'))
        .filter(total__gt=0)
        .order_by('-total', 'apellido', 'nombre')
    )
    primera = filas.first()
    if primera is None:
        return [], 0

    tope = primera.total
    empatados = [j for j in filas if j.total == tope]
    return [f'{j.nombre} {j.apellido} ({j.equipo.nombre})' for j in empatados], tope


TROFEOS_EQUIPO = [
    ('campeon', 'Campeón', 'img/copa-transparente.png'),
    ('subcampeon', 'Subcampeón', 'img/copa-transparente-plata.png'),
    ('tercero', 'Tercer lugar', 'img/copa-transparente-bronce.png'),
    ('valla', 'Valla menos vencida', 'img/guante-oro-porteros.png'),
]

TROFEO_GOLEADOR = ('Bota de oro', 'img/bota-oro-goleadores.png')
TROFEO_ASISTIDOR = ('Trofeo de asistencias', 'img/trofeo-oro-asistidores.png')


def trofeos_por_categoria(categorias):
    """Los premios de varias categorias de una vez, para no consultar por fila.

    Devuelve {categoria_id: {'equipos': {nombre: [trofeo, ...]},
                             'jugadores': {nombre: [trofeo, ...]}}}

    Se resuelve con una sola consulta sin importar cuantas categorias entren:
    las tablas y los listados dibujan cientos de filas y no pueden preguntar por
    el palmares una por una.

    Se indexa por nombre y no por id porque el palmares guarda nombres: tiene
    que sobrevivir al borrado de la liga, cuando ya no queda ningun equipo al
    que apuntar.
    """
    from apps.usuarios.estaticos import url_estatico
    from .models import Palmares

    ids = [c.id if hasattr(c, 'id') else c for c in categorias]
    premios = {}

    for fila in Palmares.objects.filter(categoria_id__in=ids):
        equipos, jugadores = {}, {}

        for campo, etiqueta, imagen in TROFEOS_EQUIPO:
            nombres = fila.lista_vallas if campo == 'valla' else [getattr(fila, campo)]
            for nombre in nombres:
                if nombre:
                    equipos.setdefault(nombre, []).append(
                        {'etiqueta': etiqueta, 'imagen': url_estatico(imagen)}
                    )

        for nombres, (etiqueta, imagen) in (
            (fila.lista_goleadores, TROFEO_GOLEADOR),
            (fila.lista_asistidores, TROFEO_ASISTIDOR),
        ):
            for nombre in nombres:
                quien, club = _partir(nombre)
                jugadores.setdefault(quien, []).append(
                    {'etiqueta': etiqueta, 'imagen': url_estatico(imagen)}
                )
                if club:
                    equipos.setdefault(club, []).append(
                        {'etiqueta': f'{etiqueta} · {quien}', 'imagen': url_estatico(imagen)}
                    )

        premios[fila.categoria_id] = {'equipos': equipos, 'jugadores': jugadores}

    return premios


def _partir(nombre):
    """Separa "Nelda Gusman Chamu (Club Zorros)" en jugador y club.

    En el palmares el premiado se guarda con su equipo entre parentesis, porque
    la fila tiene que seguir contando de quien se trata cuando la liga ya no
    exista y no queden ni el jugador ni el club a los que apuntar.
    """
    if nombre.endswith(')') and ' (' in nombre:
        quien, _, club = nombre.rpartition(' (')
        return quien, club[:-1]
    return nombre, ''


def trofeos_de_equipo(equipo):
    """Los premios de un solo equipo. Para el perfil y la ficha, que abren de a uno."""
    premios = trofeos_por_categoria([equipo.categoria_id])
    return premios.get(equipo.categoria_id, {}).get('equipos', {}).get(equipo.nombre, [])


def premios_del_entrenador(usuario):
    """Lo que ganaron los equipos que dirige, para felicitarlo en su tablero.

    Devuelve una entrada por equipo premiado, con sus trofeos de club y los
    individuales que hayan ganado sus jugadores. Los equipos sin premios no
    entran: el tablero solo muestra el bloque cuando hay algo que festejar.
    """
    from apps.equipos.models import Equipo
    from apps.jugadores.models import Jugador

    equipos = list(
        Equipo.objects.filter(entrenador=usuario).select_related('categoria', 'categoria__liga')
    )
    if not equipos:
        return []

    premios = trofeos_por_categoria({e.categoria_id for e in equipos})
    nombres_de_sus_jugadores = set(
        f'{n} {a}' for n, a in
        Jugador.objects.filter(equipo__in=equipos).values_list('nombre', 'apellido')
    )

    festejos = []
    for equipo in equipos:
        de_la_categoria = premios.get(equipo.categoria_id, {})
        del_club = de_la_categoria.get('equipos', {}).get(equipo.nombre, [])
        de_sus_jugadores = [
            {'jugador': quien, 'trofeos': lista}
            for quien, lista in de_la_categoria.get('jugadores', {}).items()
            if quien in nombres_de_sus_jugadores
        ]
        if del_club or de_sus_jugadores:
            festejos.append({
                'equipo': equipo,
                'trofeos': del_club,
                'jugadores': de_sus_jugadores,
            })
    return festejos


def _mejores_vallas(categoria):
    """Los equipos que menos goles recibieron, y cuantos.

    Se apoya en porteros.calcular, que ya resuelve el conteo por equipo con una
    cantidad fija de consultas. Solo cuentan los que jugaron: un equipo sin
    partidos tiene cero recibidos y no es un merito.
    """
    from apps.equipos.models import Equipo

    bloques = porteros.calcular(Equipo.objects.filter(categoria=categoria))
    if not bloques:
        return [], 0

    jugaron = [f for f in bloques[0]['filas'] if f['pj']]
    if not jugaron:
        return [], 0

    minimo = min(f['recibidos'] for f in jugaron)
    empatados = sorted(
        (f for f in jugaron if f['recibidos'] == minimo),
        key=lambda f: f['equipo'].nombre,
    )
    return [f['equipo'].nombre for f in empatados], minimo
