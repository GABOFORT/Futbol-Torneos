"""Armado de torneos relámpago de ejemplo, en el estado que se pida.

Lo usan `crear_torneos_demo` y `repartir_torneos`. No escribe partidos a mano:
sortea con `relampago.sortear` y avanza con `relampago.avanzar`, igual que la
pantalla. Si alguna de esas reglas se rompe, los dos comandos fallan.
"""
import datetime
import unicodedata

from django.utils import timezone

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.partidos import relampago
from apps.partidos.models import Actuacion, Partido
from apps.torneos import palmares
from apps.torneos.models import Categoria, Liga, Torneo
from apps.usuarios.models import Usuario

from ._clubes import CLUBES, NOMBRES

PAIS = 'italia'
JUGADORES_POR_EQUIPO = 12
PROPORCION_VARONES = 0.8
MARCADORES = [(2, 0), (1, 0), (3, 1), (1, 1), (0, 2), (2, 3)]

NUEVO = 'nuevo'
SEMIFINAL = 'semifinal'
FINAL = 'final'
TERMINADO = 'terminado'

HASTA = {
    NUEVO: [],
    SEMIFINAL: [Partido.FASE_OCTAVOS, Partido.FASE_CUARTOS],
    FINAL: [Partido.FASE_OCTAVOS, Partido.FASE_CUARTOS,
            Partido.FASE_SEMIFINAL, Partido.FASE_TERCERO],
    TERMINADO: [Partido.FASE_OCTAVOS, Partido.FASE_CUARTOS, Partido.FASE_SEMIFINAL,
                Partido.FASE_TERCERO, Partido.FASE_FINAL],
}


def slug(texto):
    limpio = unicodedata.normalize('NFD', texto)
    limpio = ''.join(c for c in limpio if not unicodedata.combining(c))
    return limpio.lower().replace("'", '').replace('·', '').replace(' ', '-')


class Constructor:
    """Arma torneos completos con sus equipos, planteles y resultados."""

    def __init__(self, rng):
        self.rng = rng

    def armar(self, admin, nombre, equipos, estado, dias_atras):
        fecha = timezone.localdate() - datetime.timedelta(days=dias_atras)
        liga = Liga.objects.create(
            nombre=nombre,
            descripcion=f'Torneo relámpago de {equipos} equipos, un solo día.',
            fecha_inicio=fecha, fecha_final=fecha)
        liga.administradores.add(admin)
        Categoria.objects.create(
            liga=liga, nombre='General', cupo_equipos=equipos, libre=True,
            vueltas=Categoria.VUELTA_UNICA, empate_define_penales=True)
        torneo = Torneo.objects.create(
            liga=liga, fecha=fecha, equipos=equipos, creado_por=admin)

        self._inscribir(torneo, admin, equipos)
        if estado != NUEVO:
            relampago.sortear(torneo, semilla=self.rng.randint(1, 10 ** 6))
            self._jugar(torneo, HASTA[estado], dias_atras)
        return torneo

    def _inscribir(self, torneo, admin, cuantos):
        datos = NOMBRES[PAIS]
        for club in CLUBES[PAIS][:cuantos]:
            dt = Usuario(
                username=f'{slug(torneo.nombre)}-{slug(club)}'[:150],
                first_name=self.rng.choice(datos['varon']),
                last_name=self.rng.choice(datos['apellidos']),
                role=Usuario.ROLE_ENTRENADOR,
                organization=club,
                creado_por=admin)
            dt.set_unusable_password()
            dt.save()
            equipo = Equipo.objects.create(
                nombre=club, liga=torneo.liga, categoria=torneo.categoria, entrenador=dt)
            self._plantel(equipo)

    def _plantel(self, equipo):
        datos = NOMBRES[PAIS]
        posiciones = ([Jugador.POSICIONES[0][0]]
                      + [Jugador.POSICIONES[1][0]] * 4
                      + [Jugador.POSICIONES[2][0]] * 4
                      + [Jugador.POSICIONES[3][0]] * 3)
        anio = equipo.categoria.anio_temporada - 20
        Jugador.objects.bulk_create([
            Jugador(
                equipo=equipo,
                nombre=self.rng.choice(
                    datos['varon'] if self.rng.random() < PROPORCION_VARONES
                    else datos['mujer']),
                apellido=self.rng.choice(datos['apellidos']),
                sexo=(Jugador.SEXO_MASCULINO if self.rng.random() < PROPORCION_VARONES
                      else Jugador.SEXO_FEMENINO),
                fecha_nacimiento=datetime.date(anio, 1, 1) + datetime.timedelta(
                    days=self.rng.randint(0, 364)),
                posicion=posicion,
                numero=dorsal)
            for dorsal, posicion in enumerate(posiciones[:JUGADORES_POR_EQUIPO], start=1)
        ])

    def _jugar(self, torneo, fases, dias_atras):
        cuando = timezone.now() - datetime.timedelta(days=dias_atras, hours=4)
        for fase in fases:
            pendientes = list(Partido.objects.filter(
                categoria=torneo.categoria, fase=fase,
                estado=Partido.ESTADO_PROGRAMADO))
            for partido in pendientes:
                partido.fecha = cuando
                self._resultado(partido)
                if partido.fase == Partido.FASE_FINAL:
                    palmares.cerrar_torneo_si_termino(partido)
            cuando += datetime.timedelta(hours=1)

    def _resultado(self, partido):
        locales, visitantes = self.rng.choice(MARCADORES)
        partido.goles_local, partido.goles_visitante = locales, visitantes
        if locales == visitantes:
            gana_local = self.rng.random() < 0.5
            partido.penales_local, partido.penales_visitante = (
                (4, 2) if gana_local else (2, 4))
            partido.ganador_penales = (partido.equipo_local if gana_local
                                       else partido.equipo_visitante)
        partido.estado = Partido.ESTADO_FINALIZADO
        partido.save()
        self._actuaciones(partido, locales, visitantes)
        relampago.avanzar(partido)

    def _actuaciones(self, partido, locales, visitantes):
        registro = {}
        for equipo, goles in ((partido.equipo_local, locales),
                              (partido.equipo_visitante, visitantes)):
            plantel = list(Jugador.objects.filter(equipo=equipo))
            for _ in range(goles):
                autor = self.rng.choice(plantel)
                registro.setdefault(autor, {'goles': 0})['goles'] += 1
        Actuacion.objects.bulk_create([
            Actuacion(partido=partido, jugador=jugador, **datos)
            for jugador, datos in registro.items()])
