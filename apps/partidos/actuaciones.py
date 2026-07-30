"""Lectura y validacion de los goles y asistencias que se cargan con el resultado.

El formulario manda dos listas paralelas por seccion (jugador + cantidad), asi
que no encajan en un formset de Django. Se arman a mano aca para poder validar
lo que importa: que los goles cuadren con el marcador.
"""
from collections import defaultdict

from apps.jugadores.models import Jugador

from .models import Actuacion


def leer(datos, jugadores_validos):
    """Convierte lo que llego por POST en {jugador_id: {goles, en_contra, asistencias}}.

    `jugadores_validos` acota a los jugadores de los dos equipos del partido:
    sin eso se podria cargar un goleador de otro equipo pasando su id a mano.
    """
    permitidos = {j.id for j in jugadores_validos}
    filas = defaultdict(lambda: {'goles': 0, 'goles_en_contra': 0, 'asistencias': 0})

    def numero(valor):
        try:
            return max(0, int(valor))
        except (TypeError, ValueError):
            return 0

    goleadores = datos.getlist('gol_jugador')
    cantidades = datos.getlist('gol_cantidad')
    en_contra = datos.getlist('gol_en_contra')
    for indice, jugador_id in enumerate(goleadores):
        if not jugador_id.isdigit() or int(jugador_id) not in permitidos:
            continue
        cantidad = numero(cantidades[indice] if indice < len(cantidades) else 0)
        if not cantidad:
            continue
        campo = 'goles_en_contra' if _marcado(en_contra, indice) else 'goles'
        filas[int(jugador_id)][campo] += cantidad

    asistentes = datos.getlist('asistencia_jugador')
    cantidades = datos.getlist('asistencia_cantidad')
    for indice, jugador_id in enumerate(asistentes):
        if not jugador_id.isdigit() or int(jugador_id) not in permitidos:
            continue
        cantidad = numero(cantidades[indice] if indice < len(cantidades) else 0)
        if cantidad:
            filas[int(jugador_id)]['asistencias'] += cantidad
    return dict(filas)


def _marcado(valores, indice):
    """El checkbox de 'en contra' viaja con el indice de su fila como valor."""
    return str(indice) in valores


def errores(filas, partido, goles_local, goles_visitante):
    """Los problemas que impiden guardar. Lista vacia si esta todo bien."""
    problemas = []
    equipos = _por_equipo(filas, partido)

    for etiqueta, propios, contra_del_rival, marcador in (
        (partido.equipo_local.nombre, equipos['local'], equipos['visitante'], goles_local),
        (partido.equipo_visitante.nombre, equipos['visitante'], equipos['local'], goles_visitante),
    ):
        # El marcador de un equipo son los goles de sus jugadores mas los que el
        # rival se hizo en su propia puerta.
        asignados = propios['goles'] + contra_del_rival['goles_en_contra']
        if asignados != marcador:
            problemas.append(
                f'{etiqueta}: marcaste {marcador} gol(es) pero asignaste {asignados}.'
            )
        # No hay asistencia sin gol que asistir.
        if propios['asistencias'] > marcador:
            problemas.append(
                f'{etiqueta}: {propios["asistencias"]} asistencia(s) para {marcador} gol(es).'
            )
    return problemas


def _por_equipo(filas, partido):
    totales = {
        'local': {'goles': 0, 'goles_en_contra': 0, 'asistencias': 0},
        'visitante': {'goles': 0, 'goles_en_contra': 0, 'asistencias': 0},
    }
    jugadores = Jugador.objects.filter(pk__in=filas).values('id', 'equipo_id')
    equipo_de = {j['id']: j['equipo_id'] for j in jugadores}
    for jugador_id, valores in filas.items():
        lado = 'local' if equipo_de.get(jugador_id) == partido.equipo_local_id else 'visitante'
        for campo, cantidad in valores.items():
            totales[lado][campo] += cantidad
    return totales


def guardar(partido, filas):
    """Reemplaza las actuaciones del partido por las que llegaron.

    Se borran y se vuelven a crear en vez de actualizar una por una: al corregir
    un resultado puede desaparecer un goleador, y asi no queda ninguno viejo
    colgado.
    """
    partido.actuaciones.all().delete()
    Actuacion.objects.bulk_create([
        Actuacion(partido=partido, jugador_id=jugador_id, **valores)
        for jugador_id, valores in filas.items()
        if any(valores.values())
    ])
