"""Programa y juega el torneo regular de una categoria, hasta la ultima jornada.

    python manage.py simular_temporada --liga "Serie A"
    python manage.py simular_temporada --liga "Serie A" --resumen
    python manage.py simular_temporada --liga "Serie A" --categoria Sub-10

Le pone fecha y cancha a cada partido y le carga un resultado, dejando la
categoria lista para iniciar la liguilla.

Recorre TODOS los escenarios que el sistema sabe representar: victorias, empates,
empates definidos por penales —solo donde la categoria lo permite—, partidos
ganados por default, goleadas, 0-0, partidos reprogramados y cambios de cancha.
Cada escenario aparece al menos una vez por categoria.

Los goles se reparten en actuaciones de jugadores reales, cuadrando con el
marcador, para que las tablas de goleo, asistencias y porterias tengan de donde
salir.
"""
import datetime
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.jugadores.models import Jugador
from apps.partidos.models import Actuacion, Partido
from apps.torneos.models import Liga

SEMILLA = 2026

GANA_LOCAL = 'gana local'
GANA_VISITANTE = 'gana visitante'
EMPATE = 'empate'
EMPATE_PENALES = 'empate con penales'
DEFAULT_LOCAL = 'no se presento el local'
DEFAULT_VISITANTE = 'no se presento el visitante'
SIN_GOLES = 'cero a cero'
GOLEADA = 'goleada'

ESCENARIOS_BASE = [
    GANA_LOCAL, GANA_VISITANTE, EMPATE, SIN_GOLES, GOLEADA,
    DEFAULT_LOCAL, DEFAULT_VISITANTE,
]

UNO_DE_CADA_REPROGRAMADO = 17
UNO_DE_CADA_MUDADO = 23

HORARIOS = [9, 11, 13, 15, 17]
DIAS_ANTES_DE_HOY = 3
PROBABILIDAD_PENAL = 0.12
PROBABILIDAD_EN_CONTRA = 0.06


class Command(BaseCommand):
    help = 'Programa y juega el torneo regular de las categorias de una liga.'

    def add_arguments(self, parser):
        parser.add_argument('--liga', required=True)
        parser.add_argument('--categoria', action='append', dest='categorias')
        parser.add_argument('--resumen', action='store_true')

    def handle(self, *args, **opciones):
        self.rng = random.Random(SEMILLA)
        liga = self._liga(opciones['liga'])
        categorias = self._categorias(liga, opciones['categorias'])

        if not categorias:
            self.stdout.write(self.style.WARNING(
                'No hay categorias con partidos pendientes en esta liga.'))
            return

        if opciones['resumen']:
            self._mostrar_resumen(liga, categorias)
            return

        with transaction.atomic():
            informe = [self._jugar(liga, c) for c in categorias]
        self._mostrar_jugado(liga, informe)

    def _liga(self, nombre):
        liga = Liga.objects.filter(nombre=nombre).first()
        if liga is None:
            existentes = ', '.join(Liga.objects.values_list('nombre', flat=True))
            raise CommandError(f'No existe la liga "{nombre}". Hay: {existentes}')
        if not liga.sedes.exists():
            raise CommandError(f'"{nombre}" no tiene canchas cargadas.')
        return liga

    def _categorias(self, liga, nombres):
        categorias = liga.categorias.order_by('nombre')
        if nombres:
            categorias = categorias.filter(nombre__in=nombres)
            faltan = set(nombres) - {c.nombre for c in categorias}
            if faltan:
                raise CommandError(
                    f'"{liga.nombre}" no tiene estas categorias: {", ".join(sorted(faltan))}')
        return [c for c in categorias if self._pendientes(c).exists()]

    def _pendientes(self, categoria):
        return Partido.objects.filter(
            categoria=categoria, fase=Partido.FASE_REGULAR,
        ).exclude(estado=Partido.ESTADO_FINALIZADO)

    def _fechas(self, liga, jornadas):
        """Una fecha por jornada, repartidas entre el inicio de la liga y hoy.

        Se calcula el paso en vez de fijar una semana: una categoria de 34
        jornadas no entra en el calendario semanal sin irse al futuro, y un
        partido con fecha por venir no se puede dar por jugado.
        """
        arranque = liga.fecha_inicio or (timezone.localdate() - datetime.timedelta(days=180))
        final = timezone.localdate() - datetime.timedelta(days=DIAS_ANTES_DE_HOY)
        margen = (final - arranque).days
        if margen < jornadas:
            arranque = final - datetime.timedelta(days=jornadas * 2)
            margen = (final - arranque).days
        paso = margen / jornadas
        return [arranque + datetime.timedelta(days=round(paso * numero))
                for numero in range(jornadas)]

    def _momento(self, dia, indice):
        hora = HORARIOS[indice % len(HORARIOS)]
        ingenuo = datetime.datetime.combine(dia, datetime.time(hora, 0))
        return timezone.make_aware(ingenuo)

    def _escenarios_para(self, categoria, cuantos):
        """La lista de escenarios del torneo, con todos representados."""
        posibles = list(ESCENARIOS_BASE)
        if categoria.empate_define_penales:
            posibles.append(EMPATE_PENALES)

        obligatorios = posibles[:cuantos]
        pesos = [self._peso(e) for e in posibles]
        resto = self.rng.choices(posibles, weights=pesos, k=max(0, cuantos - len(obligatorios)))
        mezcla = obligatorios + resto
        self.rng.shuffle(mezcla)
        return mezcla

    @staticmethod
    def _peso(escenario):
        if escenario in (GANA_LOCAL, GANA_VISITANTE):
            return 30
        if escenario in (EMPATE, EMPATE_PENALES):
            return 18
        if escenario == SIN_GOLES:
            return 8
        if escenario == GOLEADA:
            return 6
        return 1

    def _marcador(self, escenario):
        if escenario == GANA_LOCAL:
            return self.rng.randint(1, 3) + 1, self.rng.randint(0, 1)
        if escenario == GANA_VISITANTE:
            return self.rng.randint(0, 1), self.rng.randint(1, 3) + 1
        if escenario in (EMPATE, EMPATE_PENALES):
            iguales = self.rng.randint(1, 3)
            return iguales, iguales
        if escenario == SIN_GOLES:
            return 0, 0
        if escenario == GOLEADA:
            fuerte = self.rng.randint(5, 7)
            return (fuerte, 0) if self.rng.random() < 0.5 else (0, fuerte)
        return Partido.MARCADOR_DEFAULT, 0

    def _jugar(self, liga, categoria):
        partidos = list(self._pendientes(categoria)
                        .select_related('equipo_local', 'equipo_visitante')
                        .order_by('jornada', 'id'))
        jornadas = sorted({p.jornada for p in partidos})
        dias = dict(zip(jornadas, self._fechas(liga, len(jornadas))))
        canchas = list(liga.sedes.all())
        planteles = self._planteles(categoria)

        escenarios = self._escenarios_para(categoria, len(partidos))
        conteo = {}
        actuaciones = []

        for indice, (partido, escenario) in enumerate(zip(partidos, escenarios)):
            conteo[escenario] = conteo.get(escenario, 0) + 1
            self._programar(partido, dias[partido.jornada], indice, canchas)
            self._resolver(partido, escenario, planteles, actuaciones)

        Partido.objects.bulk_update(partidos, [
            'fecha', 'fecha_original', 'sede', 'sede_original', 'estado',
            'goles_local', 'goles_visitante', 'ganador_penales',
            'penales_local', 'penales_visitante', 'no_se_presento',
        ])
        Actuacion.objects.bulk_create(actuaciones)
        return {
            'categoria': categoria,
            'partidos': len(partidos),
            'actuaciones': len(actuaciones),
            'escenarios': conteo,
        }

    def _planteles(self, categoria):
        planteles = {}
        for jugador in Jugador.objects.filter(equipo__categoria=categoria):
            planteles.setdefault(jugador.equipo_id, []).append(jugador)
        return planteles

    def _programar(self, partido, dia, indice, canchas):
        momento = self._momento(dia, indice)
        cancha = canchas[indice % len(canchas)]
        partido.fecha_original = momento
        partido.sede_original = cancha
        partido.fecha = momento
        partido.sede = cancha

        if indice % UNO_DE_CADA_REPROGRAMADO == 0:
            partido.fecha = momento + datetime.timedelta(days=2)
        if indice % UNO_DE_CADA_MUDADO == 0 and len(canchas) > 1:
            partido.sede = canchas[(indice + 1) % len(canchas)]

    def _resolver(self, partido, escenario, planteles, actuaciones):
        partido.estado = Partido.ESTADO_FINALIZADO
        locales, visitantes = self._marcador(escenario)

        if escenario == DEFAULT_LOCAL:
            partido.no_se_presento = partido.equipo_local
            partido.goles_local, partido.goles_visitante = 0, Partido.MARCADOR_DEFAULT
            return
        if escenario == DEFAULT_VISITANTE:
            partido.no_se_presento = partido.equipo_visitante
            partido.goles_local, partido.goles_visitante = Partido.MARCADOR_DEFAULT, 0
            return

        partido.goles_local, partido.goles_visitante = locales, visitantes

        if escenario == EMPATE_PENALES:
            self._tanda(partido)

        actuaciones += self._actuaciones(partido, planteles, locales, visitantes)

    def _tanda(self, partido):
        """La tanda que desempata en el torneo regular: da el punto extra."""
        gana_local = self.rng.random() < 0.5
        alto = self.rng.randint(3, 5)
        bajo = self.rng.randint(1, alto - 1)
        partido.penales_local, partido.penales_visitante = (
            (alto, bajo) if gana_local else (bajo, alto))
        partido.ganador_penales = (
            partido.equipo_local if gana_local else partido.equipo_visitante)

    def _actuaciones(self, partido, planteles, locales, visitantes):
        """Reparte los goles del marcador entre jugadores de verdad."""
        del_local = planteles.get(partido.equipo_local_id, [])
        del_visitante = planteles.get(partido.equipo_visitante_id, [])
        if not del_local or not del_visitante:
            return []

        registro = {}
        self._anotar(registro, del_local, del_visitante, locales)
        self._anotar(registro, del_visitante, del_local, visitantes)
        return [Actuacion(partido=partido, jugador=jugador, **datos)
                for jugador, datos in registro.items()]

    def _anotar(self, registro, propios, rivales, goles):
        """Suma `goles` al marcador de un equipo, repartidos entre sus jugadores.

        Un gol puede entrar como gol en contra de un rival: eso sube el marcador
        de este equipo sin contar para su tabla de goleo, que es justo como lo
        resuelve `Partido._asignados`.
        """
        for _ in range(goles):
            if self.rng.random() < PROBABILIDAD_EN_CONTRA:
                autor = self.rng.choice(rivales)
                datos = registro.setdefault(autor, self._fila())
                datos['goles_en_contra'] += 1
                continue

            autor = self.rng.choice(propios)
            datos = registro.setdefault(autor, self._fila())
            datos['goles'] += 1
            if self.rng.random() < PROBABILIDAD_PENAL:
                datos['goles_de_penal'] += 1

            companeros = [j for j in propios if j != autor]
            if companeros and self.rng.random() < 0.55:
                asistente = self.rng.choice(companeros)
                registro.setdefault(asistente, self._fila())['asistencias'] += 1

    @staticmethod
    def _fila():
        return {'goles': 0, 'goles_en_contra': 0, 'goles_de_penal': 0, 'asistencias': 0}

    def _mostrar_resumen(self, liga, categorias):
        self.stdout.write(self.style.MIGRATE_HEADING(f'SE JUGARIA en {liga.nombre}:'))
        for categoria in categorias:
            pendientes = self._pendientes(categoria)
            jornadas = pendientes.values('jornada').distinct().count()
            penales = 'con penales' if categoria.empate_define_penales else 'sin penales'
            self.stdout.write(
                f'  {categoria.nombre:10} {pendientes.count():4} partidos · '
                f'{jornadas:2} jornadas · empates {penales}')
        self.stdout.write('\n  Se les pone fecha, cancha y resultado. Sin tocar la liguilla.')

    def _mostrar_jugado(self, liga, informe):
        self.stdout.write(self.style.SUCCESS(f'\n{liga.nombre}'))
        for datos in informe:
            categoria = datos['categoria']
            self.stdout.write(
                f'\n  {categoria.nombre} · {datos["partidos"]} partidos · '
                f'{datos["actuaciones"]} actuaciones')
            for escenario, cuantos in sorted(datos['escenarios'].items()):
                self.stdout.write(f'      {escenario:28} {cuantos:4}')
        total = sum(d['partidos'] for d in informe)
        self.stdout.write(self.style.SUCCESS(
            f'\n{total} partidos jugados. Listos para iniciar la liguilla.'))
