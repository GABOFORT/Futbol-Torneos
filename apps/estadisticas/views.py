from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render

from apps.equipos.models import Equipo
from apps.partidos import liguilla
from apps.partidos.models import Actuacion, Partido
from apps.torneos import palmares
from apps.torneos.models import Categoria, Liga
from apps.usuarios.estaticos import url_estatico
from apps.usuarios.filtros import buscar, campo_texto, campo_opciones
from apps.usuarios.permissions import (
    admin_liga_required, cascada_equipos, ligas_administradas, ligas_visibles,
)

from . import graficos, porteros, resumen, tabla


def estadisticas_ligas(request):
    """El listado publico de ligas, cada una con sus numeros y su avance.

    Acotado por `ligas_visibles`: **a proposito muestra todas las ligas
    activas**, tambien al admin de liga. Esta es la vitrina, y en la vitrina el
    que mira decide que quiere ver; que un admin viera aca menos que un
    visitante sin cuenta era justamente el 404 que se corrigio el 12/08/2026.

    Si buscas la pantalla acotada a lo propio, es `estadisticas_mis_ligas`: se
    entra desde el tablero y filtra por `ligas_administradas`. Son dos preguntas
    distintas y por eso son dos vistas, no un `if` adentro de esta.

    `panorama` resuelve todas las ligas juntas, en una cantidad fija de
    consultas.
    """
    ligas = ligas_visibles(request.user).order_by('nombre')
    return render(request, 'estadisticas/estadisticas_ligas.html', {
        'fichas': resumen.panorama(ligas),
        'titulo_pagina': 'Estadísticas',
        'seccion': 'Estadísticas',
        'encabezado': 'Elige una liga',
        'descripcion': 'Cómo va cada liga: equipos, calendario y goles.',
        'vacio': 'Todavía no hay ligas registradas.',
    })


@admin_liga_required
def estadisticas_mis_ligas(request):
    """El mismo listado, pero acotado a las ligas que uno administra.

    Es la entrada desde el tablero. El tablero es la zona de gestion, y ahi la
    pregunta no es "que puedo mirar" sino "que administro": por eso filtra por
    `ligas_administradas` y no por `ligas_visibles`.

    De aca en adelante el recorrido es el mismo que el publico —liga ->
    categorias -> tabla de posiciones— reusando `estadisticas_ligas.html` y las
    vistas que ya existen. No hay pantalla nueva ni consulta duplicada: lo unico
    que cambia es de que conjunto de ligas se parte.

    Se muestra el listado siempre, incluso administrando una sola liga: entrar
    directo cuando hay una y pedir que elija cuando hay dos vuelve el tablero
    impredecible. Elegir liga es el primer paso, y despues se elige categoria.
    """
    ligas = ligas_administradas(request.user).order_by('nombre')
    return render(request, 'estadisticas/estadisticas_ligas.html', {
        'fichas': resumen.panorama(ligas),
        'titulo_pagina': 'Mis ligas',
        'seccion': 'Tablero · Estadísticas',
        'encabezado': 'Mis ligas',
        'descripcion': 'Elige una de tus ligas para ver sus categorías.',
        'vacio': 'Todavía no administras ninguna liga.',
        # La vitrina completa sigue a un clic: el admin tambien es visitante del
        # resto del sistema y no tiene por que salir del tablero a buscarla.
        'enlace_publico': True,
    })


def estadisticas_liga_categorias(request, liga_id):
    """El panorama de la liga: sus numeros y como va cada categoria.

    Acotada por `ligas_visibles`: el admin de liga entra a las suyas y el
    publico a las activas. Antes usaba `get_object_or_404(Liga, ...)` a secas y
    se llegaba a cualquier liga escribiendo su id en la URL.
    """
    liga = get_object_or_404(ligas_visibles(request.user), pk=liga_id)
    return render(request, 'estadisticas/estadisticas_liga_categorias.html', {
        'liga': liga,
        'panel': resumen.panel(liga),
        'tarjetas': resumen.tarjetas(liga),
    })


def tabla_posiciones(request, categoria_id):
    categoria = get_object_or_404(Categoria.objects.select_related('liga'), pk=categoria_id)
    # El calculo vive en tabla.py: la ficha de partido lo usa para mostrar en
    # que puesto va cada equipo, y no puede quedar dentro de esta vista.
    posiciones = tabla.calcular(categoria)

    # Los trofeos se cuelgan de cada fila en la vista y no se buscan desde el
    # template: las plantillas de Django no saben indexar un diccionario con una
    # clave variable, y hacerlo con un filtro propio seria una consulta por fila.
    premios = palmares.trofeos_por_categoria([categoria.id])
    de_equipos = premios.get(categoria.id, {}).get('equipos', {})
    for fila in posiciones:
        fila['trofeos'] = de_equipos.get(fila['equipo'].nombre, [])

    return render(request, 'estadisticas/tabla_posiciones.html', {
        'categoria': categoria,
        'posiciones': posiciones,
        # Al lado de la tabla, para no tener que salir de la pantalla para saber
        # quien mete los goles de esta categoria. Solo los cinco primeros: es un
        # resumen que acompana a la tabla, no la tabla de goleo completa.
        'rankings': resumen.rankings(categoria, tope=5),
        # Los iconos se resuelven aca porque su ruta vive en palmares.py, que es
        # el unico lugar donde se declara el arte de cada premio.
        'icono_goleador': url_estatico(palmares.TROFEO_GOLEADOR[1]),
        'icono_asistidor': url_estatico(palmares.TROFEO_ASISTIDOR[1]),
        'icono_valla': url_estatico(dict(
            (clave, imagen) for clave, _, imagen in palmares.TROFEOS_EQUIPO)['valla']),
    })


def _ranking(request, campo, titulo, etiqueta):
    """Tabla de goleadores o de asistencias, segun el campo que se sume.

    Las dos comparten todo menos la columna que ordenan, asi que se arman aca y
    cada vista solo dice cual mirar.
    """
    user = request.user
    ligas = ligas_visibles(user)

    actuaciones = Actuacion.objects.filter(jugador__equipo__liga__in=ligas)
    if user.is_authenticated and user.role == user.ROLE_ENTRENADOR and not user.is_superuser:
        actuaciones = actuaciones.filter(jugador__equipo__entrenador=user)

    seleccion, opciones = cascada_equipos(user, request.GET)
    termino = request.GET.get('q', '')

    if seleccion['liga']:
        actuaciones = actuaciones.filter(jugador__equipo__liga_id=seleccion['liga'])
    if seleccion['categoria']:
        actuaciones = actuaciones.filter(jugador__equipo__categoria_id=seleccion['categoria'])
    if seleccion['equipo']:
        actuaciones = actuaciones.filter(jugador__equipo_id=seleccion['equipo'])
    actuaciones = buscar(actuaciones, termino, [
        'jugador__nombre', 'jugador__apellido', 'jugador__equipo__nombre',
        'jugador__equipo__categoria__nombre', 'jugador__equipo__liga__nombre',
    ])

    # Los partidos jugados son los del equipo: hoy no se registra quien entro a
    # la cancha, y en estas ligas juegan todos los inscritos.
    #
    # `fase=FASE_REGULAR` igual que en tabla.py y porteros.py: sin eso los
    # partidos de liguilla inflaban el divisor y todos los promedios de gol
    # salian mas bajos de lo real.
    jugados = {
        fila['categoria_id']: fila['total']
        for fila in Partido.objects.filter(
            estado=Partido.ESTADO_FINALIZADO, fase=Partido.FASE_REGULAR)
        .values('categoria_id').annotate(total=Count('id'))
    }

    # Cuantos equipos tiene cada categoria, en UNA consulta para toda la tabla.
    # Antes se contaban dentro del bucle, una consulta por renglon: con la tabla
    # completa eran mas de mil ochocientas para dibujar una columna de promedio.
    equipos_por_categoria = {
        fila['categoria_id']: fila['total']
        for fila in Equipo.objects.values('categoria_id').annotate(total=Count('id'))
    }

    # Un solo lote de premios para todas las categorias que aparezcan en la
    # tabla, en vez de una consulta por renglon.
    premios = palmares.trofeos_por_categoria(
        set(actuaciones.values_list('jugador__equipo__categoria_id', flat=True))
    )

    filas = []
    for datos in (
        actuaciones.values(
            'jugador_id', 'jugador__nombre', 'jugador__apellido', 'jugador__numero',
            # El id del equipo va porque su nombre abre el perfil en el modal.
            # No cambia el agrupamiento: ya se agrupa por jugador, que es mas
            # fino que el equipo.
            'jugador__equipo_id',
            'jugador__equipo__nombre', 'jugador__equipo__categoria__nombre',
            'jugador__equipo__categoria_id', 'jugador__equipo__liga__nombre',
        ).annotate(total=Sum(campo)).filter(total__gt=0).order_by('-total')
    ):
        # Cada equipo juega la mitad de los partidos de su categoria: en cada
        # uno participan dos equipos.
        categoria_id = datos['jugador__equipo__categoria_id']
        pj = _partidos_del_equipo(
            jugados.get(categoria_id, 0), equipos_por_categoria.get(categoria_id, 0))
        nombre = f"{datos['jugador__nombre']} {datos['jugador__apellido']}"
        de_la_cat = premios.get(datos['jugador__equipo__categoria_id'], {})
        filas.append({
            'jugador': nombre,
            'trofeos': de_la_cat.get('jugadores', {}).get(nombre, []),
            'trofeos_equipo': de_la_cat.get('equipos', {}).get(datos['jugador__equipo__nombre'], []),
            'numero': datos['jugador__numero'],
            'equipo': datos['jugador__equipo__nombre'],
            'equipo_id': datos['jugador__equipo_id'],
            'categoria': datos['jugador__equipo__categoria__nombre'],
            'liga': datos['jugador__equipo__liga__nombre'],
            'pj': pj,
            'total': datos['total'],
            'promedio': round(datos['total'] / pj, 2) if pj else None,
        })

    filtros = [
        campo_texto('q', 'Buscar', termino, 'Jugador, equipo, categoría o liga'),
        campo_opciones('liga', 'Liga', seleccion['liga'],
                       opciones['ligas'].values_list('id', 'nombre'), vacio='Todas las ligas'),
        campo_opciones('categoria', 'Categoría', seleccion['categoria'],
                       opciones['categorias'].values_list('id', 'nombre'), vacio='Todas'),
        campo_opciones('equipo', 'Equipo', seleccion['equipo'],
                       opciones['equipos'].values_list('id', 'nombre'), vacio='Todos'),
    ]
    return render(request, 'estadisticas/ranking.html', {
        'filas': filas,
        'titulo': titulo,
        'etiqueta': etiqueta,
        'filtros': filtros,
        'filtros_activos': bool(termino or seleccion['liga'] or seleccion['categoria'] or seleccion['equipo']),
        'total_resultados': len(filas),
    })


def _partidos_del_equipo(partidos_de_la_categoria, equipos_de_la_categoria):
    """Cuantos partidos jugo un equipo de esa categoria.

    En cada partido juegan dos equipos, asi que a cada uno le corresponde
    aproximadamente el doble de partidos dividido la cantidad de equipos.

    Recibe los dos numeros ya calculados en vez de ir a buscar los equipos:
    llamada desde el bucle de la tabla, cada consulta propia se multiplicaba por
    la cantidad de renglones.
    """
    if not equipos_de_la_categoria:
        return 0
    return round(partidos_de_la_categoria * 2 / equipos_de_la_categoria)


def liguilla_categoria(request, categoria_id):
    """El cuadro de eliminacion de una categoria.

    Es publico como el resto de las estadisticas. Los botones para poner fecha o
    cargar el resultado no van aca: cada cruce abre la ficha del partido, y
    desde el calendario se administran igual que cualquier otro.
    """
    categoria = get_object_or_404(Categoria.objects.select_related('liga'), pk=categoria_id)
    return render(request, 'estadisticas/liguilla.html', {
        'categoria': categoria,
        'cuadro': liguilla.cuadro(categoria),
    })


def tabla_porteros(request):
    """Porterías menos vencidas: los equipos que menos goles reciben.

    Es por equipo y no por portero porque no se registra quien ataja cada
    partido. El razonamiento completo esta en porteros.py.
    """
    user = request.user
    seleccion, opciones = cascada_equipos(user, request.GET)
    termino = request.GET.get('q', '')

    equipos = Equipo.objects.filter(liga__in=ligas_visibles(user))
    # El entrenador ve su propio equipo en el listado, igual que en los rankings.
    if user.is_authenticated and user.role == user.ROLE_ENTRENADOR and not user.is_superuser:
        equipos = equipos.filter(entrenador=user)

    if seleccion['liga']:
        equipos = equipos.filter(liga_id=seleccion['liga'])
    if seleccion['categoria']:
        equipos = equipos.filter(categoria_id=seleccion['categoria'])
    if seleccion['equipo']:
        equipos = equipos.filter(pk=seleccion['equipo'])
    equipos = buscar(equipos, termino, [
        'nombre', 'categoria__nombre', 'liga__nombre',
        'jugadores__nombre', 'jugadores__apellido',
    ])

    bloques = porteros.calcular(equipos)

    # El guante de oro va al lado del equipo que lo gano. Un solo lote para
    # todas las categorias que se esten mostrando.
    premios = palmares.trofeos_por_categoria([b['categoria'].id for b in bloques])
    for bloque in bloques:
        de_equipos = premios.get(bloque['categoria'].id, {}).get('equipos', {})
        for fila in bloque['filas']:
            fila['trofeos'] = de_equipos.get(fila['equipo'].nombre, [])

    filtros = [
        campo_texto('q', 'Buscar', termino, 'Equipo, portero, categoría o liga'),
        campo_opciones('liga', 'Liga', seleccion['liga'],
                       opciones['ligas'].values_list('id', 'nombre'), vacio='Todas las ligas'),
        campo_opciones('categoria', 'Categoría', seleccion['categoria'],
                       opciones['categorias'].values_list('id', 'nombre'), vacio='Todas'),
        campo_opciones('equipo', 'Equipo', seleccion['equipo'],
                       opciones['equipos'].values_list('id', 'nombre'), vacio='Todos'),
    ]
    return render(request, 'estadisticas/porteros.html', {
        'bloques': bloques,
        'filtros': filtros,
        'filtros_activos': bool(termino or seleccion['liga'] or seleccion['categoria'] or seleccion['equipo']),
        # Se cuentan categorias y no equipos: es lo que devuelve cada bloque, y
        # es la unidad en la que se lee esta pantalla.
        'total_resultados': len(bloques),
    })


def vitrina(request):
    """Las temporadas que ya terminaron, con su palmares.

    Es publica y es el motivo de que una liga concluida no se borre al instante:
    despues de la final la gente todavia quiere ver quien salio campeon, quien
    fue el goleador y como quedo la tabla.

    Se muestran todas las que existan. Las ligas concluidas viven 30 dias y
    despues el superadmin las elimina; el palmares sobrevive a ese borrado,
    porque no guarda claves foraneas sino los nombres.
    """
    from apps.torneos.models import Palmares
    from apps.usuarios.estaticos import url_estatico

    registros = list(Palmares.objects.select_related('categoria', 'categoria__liga'))

    # Las imagenes del podio se resuelven aca y no en el template: la ruta de
    # cada trofeo vive en palmares.py, que es el unico lugar donde se declara.
    podios = {clave: url_estatico(imagen) for clave, _, imagen in palmares.TROFEOS_EQUIPO}

    return render(request, 'estadisticas/vitrina.html', {
        'registros': registros,
        'podios': podios,
        'imagen_bota': url_estatico(palmares.TROFEO_GOLEADOR[1]),
        'imagen_asistidor': url_estatico(palmares.TROFEO_ASISTIDOR[1]),
    })


def pantalla_graficos(request):
    """Los números del torneo en gráficos: goles por jornada, ataque y defensa.

    Pública como el resto de las estadísticas. Se puede acotar a una categoría;
    sin filtro se mezclan todas las visibles, que sirve para el panorama aunque
    la jornada 3 de una categoría no sea el mismo día que la de otra.
    """
    ligas = ligas_visibles(request.user)
    categorias = (Categoria.objects.filter(liga__in=ligas)
                  .select_related('liga').order_by('liga__nombre', 'nombre'))

    # El id llega por la URL: se comprueba que exista y que sea visible, en vez
    # de confiar en el parametro.
    elegida = request.GET.get('categoria', '')
    categoria = None
    if elegida.isdigit():
        categoria = categorias.filter(pk=int(elegida)).first()

    return render(request, 'estadisticas/graficos.html', {
        'datos': graficos.calcular(ligas, categoria),
        'categorias': categorias,
        'categoria': categoria,
        'minimo': graficos.MINIMO,
    })


def tabla_goleo(request):
    return _ranking(request, 'goles', 'Tabla de goleo', 'Goles')


def tabla_asistencias(request):
    return _ranking(request, 'asistencias', 'Tabla de asistencias', 'Asistencias')
