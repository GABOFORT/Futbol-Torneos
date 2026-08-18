"""Llena de jugadores los equipos que todavia no tienen plantel.

    python manage.py llenar_planteles --liga "Serie A" --por-equipo 15
    python manage.py llenar_planteles --liga "Serie A" --por-equipo 15 --resumen
    python manage.py llenar_planteles --liga "Serie A" --categoria Sub-10

Solo toca equipos SIN jugadores: un plantel cargado no se altera.

La edad de cada jugador se sortea dentro de lo que admite su categoria, y antes
de guardarlo se le pregunta a la propia categoria si lo acepta
(`rechazo_para`). Si alguno no pasa, el comando falla y no queda nada escrito:
es la misma regla que aplica el formulario, asi que no puede entrar por aca un
jugador que la pantalla rechazaria.
"""
import datetime
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.torneos.models import Liga

from ._clubes import NOMBRES

SEMILLA = 2026
PAIS = 'italia'
PROPORCION_VARONES = 0.8

PORTERO, DEFENSA, MEDIO, DELANTERO = (p for p, _ in Jugador.POSICIONES)

DOS_PORTEROS_DESDE = 13
PROPORCION_DEFENSAS = 0.38
PROPORCION_MEDIOS = 0.38

EDAD_INFANTIL = (10, 15)
EDAD_LIBRE_TOPE = 45
MARGEN_EDAD_MINIMA = 15


class Command(BaseCommand):
    help = 'Crea los jugadores de los equipos que no tienen plantel.'

    def add_arguments(self, parser):
        parser.add_argument('--liga', required=True)
        parser.add_argument('--categoria', action='append', dest='categorias')
        parser.add_argument('--por-equipo', type=int, default=15, dest='por_equipo')
        parser.add_argument('--minimo', type=int, dest='minimo',
                            help='Con --maximo, sortea el tamaño de cada plantel.')
        parser.add_argument('--maximo', type=int, dest='maximo')
        parser.add_argument('--resumen', action='store_true')

    def handle(self, *args, **opciones):
        self.rng = random.Random(SEMILLA)
        self.minimo, self.maximo = self._rango(opciones)
        if self.minimo < 1:
            raise CommandError('El plantel tiene que ser de 1 jugador o mas.')
        if self.minimo > self.maximo:
            raise CommandError('--minimo no puede ser mayor que --maximo.')

        liga = self._liga(opciones['liga'])
        equipos = self._equipos(liga, opciones['categorias'])
        if not equipos:
            self.stdout.write(self.style.WARNING(
                'No hay equipos sin plantel en esta liga.'))
            return

        if opciones['resumen']:
            self._mostrar_resumen(liga, equipos)
            return

        with transaction.atomic():
            creados = self._llenar(equipos)
        self._mostrar_creado(liga, equipos, creados)

    def _tamano(self):
        return (str(self.minimo) if self.minimo == self.maximo
                else f'{self.minimo}-{self.maximo}')

    @staticmethod
    def _rango(opciones):
        """El tamaño de plantel a usar: un rango si lo piden, o un valor fijo."""
        minimo, maximo = opciones['minimo'], opciones['maximo']
        if minimo is None and maximo is None:
            fijo = opciones['por_equipo']
            return fijo, fijo
        return (minimo if minimo is not None else maximo,
                maximo if maximo is not None else minimo)

    def _liga(self, nombre):
        liga = Liga.objects.filter(nombre=nombre).first()
        if liga is None:
            existentes = ', '.join(Liga.objects.values_list('nombre', flat=True))
            raise CommandError(f'No existe la liga "{nombre}". Hay: {existentes}')
        return liga

    def _equipos(self, liga, nombres):
        equipos = Equipo.objects.filter(liga=liga).select_related('categoria__liga')
        if nombres:
            equipos = equipos.filter(categoria__nombre__in=nombres)
            faltan = set(nombres) - {e.categoria.nombre for e in equipos}
            if faltan:
                raise CommandError(
                    f'"{liga.nombre}" no tiene estas categorias: {", ".join(sorted(faltan))}')
        return [e for e in equipos.order_by('categoria__nombre', 'nombre')
                if not e.jugadores.exists()]

    def _rango_de_edad(self, categoria):
        """Entre que edades sortear, segun lo que admite la categoria."""
        if categoria.edad_minima:
            return categoria.edad_minima, categoria.edad_minima + MARGEN_EDAD_MINIMA
        if categoria.limite_edad:
            tope = categoria.edad_maxima
            return max(1, tope - 3), tope
        if categoria.libre:
            return EDAD_INFANTIL
        return EDAD_INFANTIL

    def _nacimiento(self, categoria, edad):
        """Una fecha del año en que el jugador cumple esa edad en la temporada."""
        anio = categoria.anio_temporada - edad
        dia = self.rng.randint(1, 365)
        return datetime.date(anio, 1, 1) + datetime.timedelta(days=dia - 1)

    def _llenar(self, equipos):
        creados = []
        for equipo in equipos:
            creados += self._plantel(equipo)
        Jugador.objects.bulk_create(creados)
        return creados

    def _plantel(self, equipo):
        categoria = equipo.categoria
        minima, maxima = self._rango_de_edad(categoria)
        datos = NOMBRES[PAIS]
        jugadores = []
        cuantos = self.rng.randint(self.minimo, self.maximo)

        for dorsal, posicion in enumerate(self._posiciones(cuantos), start=1):
            sexo = (Jugador.SEXO_MASCULINO if self.rng.random() < PROPORCION_VARONES
                    else Jugador.SEXO_FEMENINO)
            clave = 'varon' if sexo == Jugador.SEXO_MASCULINO else 'mujer'
            nacimiento = self._nacimiento(categoria, self.rng.randint(minima, maxima))

            rechazo = categoria.rechazo_para(nacimiento, sexo)
            if rechazo:
                raise CommandError(
                    f'{equipo.nombre} ({categoria.nombre}): {rechazo[1]}')

            jugadores.append(Jugador(
                equipo=equipo,
                nombre=self.rng.choice(datos[clave]),
                apellido=self.rng.choice(datos['apellidos']),
                sexo=sexo,
                fecha_nacimiento=nacimiento,
                posicion=posicion,
                numero=dorsal,
            ))
        return jugadores

    @staticmethod
    def _posiciones(cuantos):
        """Un plantel equilibrado del tamaño pedido.

        Se reparte por proporcion y no con una plantilla fija, para que un
        plantel de 11 no quede sin delanteros al recortar el de 15.

            11 -> 1 portero · 4 defensas · 4 medios · 2 delanteros
            15 -> 2 porteros · 5 defensas · 5 medios · 3 delanteros
        """
        porteros = 1 if cuantos < DOS_PORTEROS_DESDE else 2
        campo = cuantos - porteros
        defensas = round(campo * PROPORCION_DEFENSAS)
        medios = round(campo * PROPORCION_MEDIOS)
        delanteros = campo - defensas - medios
        return (
            [PORTERO] * porteros + [DEFENSA] * defensas
            + [MEDIO] * medios + [DELANTERO] * delanteros
        )

    def _resumen_por_categoria(self, equipos):
        resumen = {}
        for equipo in equipos:
            resumen.setdefault(equipo.categoria, []).append(equipo)
        return sorted(resumen.items(), key=lambda par: par[0].nombre)

    def _mostrar_resumen(self, liga, equipos):
        self.stdout.write(self.style.MIGRATE_HEADING(f'SE CREARIA en {liga.nombre}:'))
        for categoria, suyos in self._resumen_por_categoria(equipos):
            minima, maxima = self._rango_de_edad(categoria)
            regla = ('libre' if categoria.libre else
                     categoria.limite_edad or f'desde {categoria.edad_minima} años')
            self.stdout.write(
                f'  {categoria.nombre:10} {len(suyos):3} equipos × {self._tamano()} = '
                f'{len(suyos) * self.minimo}-{len(suyos) * self.maximo} jugadores  '
                f'({regla} → {minima}-{maxima} años)')
        self.stdout.write(
            f'\n  entre {len(equipos) * self.minimo} y {len(equipos) * self.maximo} '
            f'jugadores en total. '
            f'Los equipos con plantel no se tocan.')

    def _mostrar_creado(self, liga, equipos, creados):
        self.stdout.write(self.style.SUCCESS(f'\n{liga.nombre}'))
        for categoria, suyos in self._resumen_por_categoria(equipos):
            total = Jugador.objects.filter(equipo__categoria=categoria).count()
            self.stdout.write(
                f'   {categoria.nombre:10} {len(suyos):3} equipos · {total:4} jugadores')
        self.stdout.write(self.style.SUCCESS(
            f'\n{len(creados)} jugadores creados en {len(equipos)} equipos.'))
