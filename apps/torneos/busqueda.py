"""El buscador del sitio: una caja que encuentra jugadores, equipos, torneos y canchas.

Un visitante no sabe si lo que busca es un equipo, una categoria o una cancha:
escribe un nombre y espera resultados. Por eso es una sola busqueda que mira las
cuatro cosas a la vez y agrupa el resultado, en vez de cuatro filtros separados.

**Acotado por `ligas_visibles`**, igual que el resto: el visitante ve lo de las
ligas activas y un Administrador de Liga solo lo suyo.

**No busca arbitros.** El sistema no los registra: no hay modelo, no hay campo y
nadie los carga. Ofrecer el filtro y no devolver nunca nada seria peor que no
tenerlo.
"""
from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.torneos.models import Categoria, Sede
from apps.usuarios.filtros import buscar
from apps.usuarios.permissions import ligas_visibles

TOPE = 8

MINIMO = 2


def hay_termino(termino):
    return len((termino or '').strip()) >= MINIMO


def buscar_todo(user, termino):
    """Los resultados agrupados por tipo, cada uno acotado a `TOPE`.

    Devuelve tambien `total` para poder decir cuantos se encontraron sin que la
    pantalla tenga que sumar las listas a mano.
    """
    if not hay_termino(termino):
        return {'jugadores': [], 'equipos': [], 'torneos': [], 'sedes': [], 'total': 0}

    ligas = ligas_visibles(user)

    jugadores = list(buscar(
        Jugador.objects.filter(equipo__liga__in=ligas)
        .select_related('equipo', 'equipo__categoria', 'equipo__liga'),
        termino, ['nombre', 'apellido'],
    ).order_by('apellido', 'nombre')[:TOPE])

    equipos = list(buscar(
        Equipo.objects.filter(liga__in=ligas).select_related('categoria', 'liga'),
        termino, ['nombre'],
    ).order_by('nombre')[:TOPE])

    torneos = list(buscar(
        Categoria.objects.filter(liga__in=ligas, activa=True).select_related('liga'),
        termino, ['nombre', 'liga__nombre'],
    ).order_by('liga__nombre', 'nombre')[:TOPE])

    sedes = list(buscar(
        Sede.objects.filter(liga__in=ligas).select_related('liga'),
        termino, ['nombre', 'direccion'],
    ).order_by('nombre')[:TOPE])

    return {
        'jugadores': jugadores,
        'equipos': equipos,
        'torneos': torneos,
        'sedes': sedes,
        'total': len(jugadores) + len(equipos) + len(torneos) + len(sedes),
    }
