from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render

from apps.equipos.models import Equipo
from apps.partidos import liguilla
from apps.partidos.models import Actuacion, Partido
from apps.torneos.models import Categoria, Liga
from apps.usuarios.filtros import buscar, campo_texto, campo_opciones
from apps.usuarios.permissions import cascada_equipos, ligas_visibles

from . import porteros, tabla


def estadisticas_ligas(request):
    # Mismo criterio que en equipos y partidos: el admin de liga solo ve las suyas.
    ligas = ligas_visibles(request.user).order_by('nombre')
    return render(request, 'estadisticas/estadisticas_ligas.html', {'ligas': ligas})


def estadisticas_liga_categorias(request, liga_id):
    liga = get_object_or_404(Liga, pk=liga_id)
    categorias = liga.categorias.filter(activa=True).order_by('nombre')
    return render(request, 'estadisticas/estadisticas_liga_categorias.html', {'liga': liga, 'categorias': categorias})


def tabla_posiciones(request, categoria_id):
    categoria = get_object_or_404(Categoria.objects.select_related('liga'), pk=categoria_id)
    # El calculo vive en tabla.py: la ficha de partido lo usa para mostrar en
    # que puesto va cada equipo, y no puede quedar dentro de esta vista.
    return render(request, 'estadisticas/tabla_posiciones.html', {
        'categoria': categoria,
        'posiciones': tabla.calcular(categoria),
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
    jugados = {
        fila['categoria_id']: fila['total']
        for fila in Partido.objects.filter(estado=Partido.ESTADO_FINALIZADO)
        .values('categoria_id').annotate(total=Count('id'))
    }

    filas = []
    for datos in (
        actuaciones.values(
            'jugador_id', 'jugador__nombre', 'jugador__apellido', 'jugador__numero',
            'jugador__equipo__nombre', 'jugador__equipo__categoria__nombre',
            'jugador__equipo__categoria_id', 'jugador__equipo__liga__nombre',
        ).annotate(total=Sum(campo)).filter(total__gt=0).order_by('-total')
    ):
        # Cada equipo juega la mitad de los partidos de su categoria: en cada
        # uno participan dos equipos.
        de_la_categoria = jugados.get(datos['jugador__equipo__categoria_id'], 0)
        pj = _partidos_del_equipo(datos['jugador__equipo__categoria_id'], de_la_categoria)
        filas.append({
            'jugador': f"{datos['jugador__nombre']} {datos['jugador__apellido']}",
            'numero': datos['jugador__numero'],
            'equipo': datos['jugador__equipo__nombre'],
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


def _partidos_del_equipo(categoria_id, partidos_de_la_categoria):
    """Cuantos partidos jugo un equipo de esa categoria.

    En cada partido juegan dos equipos, asi que a cada uno le corresponde
    aproximadamente el doble de partidos dividido la cantidad de equipos.
    """
    equipos = Equipo.objects.filter(categoria_id=categoria_id).count()
    if not equipos:
        return 0
    return round(partidos_de_la_categoria * 2 / equipos)


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


def tabla_goleo(request):
    return _ranking(request, 'goles', 'Tabla de goleo', 'Goles')


def tabla_asistencias(request):
    return _ranking(request, 'asistencias', 'Tabla de asistencias', 'Asistencias')
