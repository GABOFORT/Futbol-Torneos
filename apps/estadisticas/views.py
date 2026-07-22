from django.shortcuts import get_object_or_404, render

from apps.equipos.models import Equipo
from apps.partidos.models import Partido
from apps.torneos.models import Categoria, Liga


def estadisticas_ligas(request):
    ligas = Liga.objects.filter(activa=True).order_by('nombre')
    return render(request, 'estadisticas/estadisticas_ligas.html', {'ligas': ligas})


def estadisticas_liga_categorias(request, liga_id):
    liga = get_object_or_404(Liga, pk=liga_id)
    categorias = liga.categorias.filter(activa=True).order_by('nombre')
    return render(request, 'estadisticas/estadisticas_liga_categorias.html', {'liga': liga, 'categorias': categorias})


def _tabla_vacia(equipo):
    return {
        'equipo': equipo,
        'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0,
        'gf': 0, 'gc': 0, 'dg': 0, 'pts': 0,
    }


def tabla_posiciones(request, categoria_id):
    categoria = get_object_or_404(Categoria.objects.select_related('liga'), pk=categoria_id)
    tabla = {equipo.id: _tabla_vacia(equipo) for equipo in Equipo.objects.filter(categoria=categoria)}

    partidos = Partido.objects.filter(categoria=categoria, estado=Partido.ESTADO_FINALIZADO).select_related(
        'equipo_local', 'equipo_visitante'
    )
    for partido in partidos:
        local = tabla.setdefault(partido.equipo_local_id, _tabla_vacia(partido.equipo_local))
        visitante = tabla.setdefault(partido.equipo_visitante_id, _tabla_vacia(partido.equipo_visitante))

        local['pj'] += 1
        visitante['pj'] += 1
        local['gf'] += partido.goles_local
        local['gc'] += partido.goles_visitante
        visitante['gf'] += partido.goles_visitante
        visitante['gc'] += partido.goles_local

        if partido.goles_local > partido.goles_visitante:
            local['pg'] += 1
            local['pts'] += 3
            visitante['pp'] += 1
        elif partido.goles_local < partido.goles_visitante:
            visitante['pg'] += 1
            visitante['pts'] += 3
            local['pp'] += 1
        else:
            local['pe'] += 1
            visitante['pe'] += 1
            local['pts'] += 1
            visitante['pts'] += 1

    for fila in tabla.values():
        fila['dg'] = fila['gf'] - fila['gc']

    posiciones = sorted(tabla.values(), key=lambda fila: (-fila['pts'], -fila['dg'], -fila['gf']))
    return render(request, 'estadisticas/tabla_posiciones.html', {'categoria': categoria, 'posiciones': posiciones})
