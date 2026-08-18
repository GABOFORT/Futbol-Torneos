"""Juega la liguilla de una categoria, hasta donde se le pida.

    python manage.py simular_liguilla --liga "Serie A" --categoria Sub-11
    python manage.py simular_liguilla --liga "Serie A" --categoria Sub-10 --hasta cuartos
    python manage.py simular_liguilla --liga "Serie A" --resumen

`--hasta` corta el avance en esa ronda; sin el se juega hasta la final y la
categoria queda cerrada con su palmares.

No arma los cruces a mano: los crea `liguilla.iniciar`, los encadena
`liguilla.avanzar` y el palmares lo graba `palmares.cerrar_si_termino`, que es
exactamente lo que hace la pantalla al cargar un resultado. Si alguna de esas
reglas se rompiera, este comando falla.
"""
import datetime
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.jugadores.models import Jugador
from apps.partidos import liguilla
from apps.partidos.models import Actuacion, Partido
from apps.torneos import palmares
from apps.torneos.models import Liga

SEMILLA = 2026
HORAS_ENTRE_RONDAS = 12
PROBABILIDAD_PENAL = 0.12
PROBABILIDAD_EN_CONTRA = 0.05
PROBABILIDAD_EMPATE = 0.28


class Command(BaseCommand):
    help = 'Juega la liguilla de las categorias de una liga.'

    def add_arguments(self, parser):
        parser.add_argument('--liga', required=True)
        parser.add_argument('--categoria', action='append', dest='categorias')
        parser.add_argument('--hasta', choices=Partido.ORDEN_FASES,
                            help='Ultima ronda a jugar. Sin esto se juega la final.')
        parser.add_argument('--resumen', action='store_true')

    def handle(self, *args, **opciones):
        self.rng = random.Random(SEMILLA)
        liga = self._liga(opciones['liga'])
        categorias = self._categorias(liga, opciones['categorias'])
        self.tope = (Partido.ORDEN_FASES.index(opciones['hasta'])
                     if opciones['hasta'] else len(Partido.ORDEN_FASES))

        if not categorias:
            self.stdout.write(self.style.WARNING('No hay categorias para jugar.'))
            return

        if opciones['resumen']:
            self._mostrar_resumen(categorias, opciones['hasta'])
            return

        informe = []
        for categoria in categorias:
            with transaction.atomic():
                informe.append(self._jugar(liga, categoria))
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
        return list(categorias)

    def _jugar(self, liga, categoria):
        creados = self._arrancar(categoria)
        canchas = list(liga.sedes.all())
        planteles = self._planteles(categoria)
        rondas, jugados = [], 0

        while True:
            pendientes = self._ronda_pendiente(categoria)
            if not pendientes:
                break
            fase = pendientes[0].fase
            for indice, partido in enumerate(pendientes):
                self._programar(partido, len(rondas), indice, canchas)
                self._resolver(partido, planteles)
                partido.save()
                liguilla.avanzar(partido)
                palmares.cerrar_si_termino(partido)
            etiqueta = pendientes[0].get_fase_display()
            cuadro = 'mini' if pendientes[0].es_consolacion else 'principal'
            rondas.append(f'{etiqueta} ({cuadro}) × {len(pendientes)}')
            jugados += len(pendientes)

        categoria.refresh_from_db()
        return {
            'categoria': categoria,
            'creados': creados,
            'rondas': rondas,
            'jugados': jugados,
        }

    def _arrancar(self, categoria):
        motivo = liguilla.motivo_para_no_iniciar(categoria)
        if not motivo:
            return len(liguilla.iniciar(categoria))
        if 'ya está en marcha' in motivo:
            return 0
        raise CommandError(f'{categoria.nombre}: {motivo}')

    def _ronda_pendiente(self, categoria):
        """La ronda mas temprana que falte jugar, si entra dentro del tope."""
        pendientes = (Partido.objects
                      .filter(categoria=categoria)
                      .exclude(fase=Partido.FASE_REGULAR)
                      .exclude(estado=Partido.ESTADO_FINALIZADO)
                      .select_related('equipo_local', 'equipo_visitante'))
        if not pendientes:
            return []
        orden = sorted(pendientes, key=lambda p: (
            Partido.ORDEN_FASES.index(p.fase), p.cuadro, p.orden, p.vuelta))
        primera = orden[0]
        if Partido.ORDEN_FASES.index(primera.fase) > self.tope:
            return []
        return [p for p in orden
                if p.fase == primera.fase and p.cuadro == primera.cuadro]

    def _planteles(self, categoria):
        planteles = {}
        for jugador in Jugador.objects.filter(equipo__categoria=categoria):
            planteles.setdefault(jugador.equipo_id, []).append(jugador)
        return planteles

    def _programar(self, partido, ronda, indice, canchas):
        """Fechas hacia atras desde hoy: una ronda cada medio dia, ya jugadas."""
        atras = (12 - ronda) * HORAS_ENTRE_RONDAS - indice
        momento = timezone.now() - datetime.timedelta(hours=max(1, atras))
        cancha = canchas[(ronda + indice) % len(canchas)]
        partido.fecha_original = partido.fecha_original or momento
        partido.sede_original = partido.sede_original or cancha
        partido.fecha = momento
        partido.sede = cancha

    def _resolver(self, partido, planteles):
        partido.estado = Partido.ESTADO_FINALIZADO
        locales, visitantes = self._marcador(partido)
        partido.goles_local, partido.goles_visitante = locales, visitantes

        if partido.fase == Partido.FASE_FINAL and locales == visitantes:
            self._tanda(partido)

        Actuacion.objects.bulk_create(
            self._actuaciones(partido, planteles, locales, visitantes))

    def _marcador(self, partido):
        if self.rng.random() < PROBABILIDAD_EMPATE:
            iguales = self.rng.randint(0, 2)
            return iguales, iguales
        fuerte = self.rng.randint(1, 4)
        flojo = self.rng.randint(0, max(0, fuerte - 1))
        return (fuerte, flojo) if self.rng.random() < 0.5 else (flojo, fuerte)

    def _tanda(self, partido):
        gana_local = self.rng.random() < 0.5
        alto = self.rng.randint(3, 5)
        bajo = self.rng.randint(1, alto - 1)
        partido.penales_local, partido.penales_visitante = (
            (alto, bajo) if gana_local else (bajo, alto))
        partido.ganador_penales = (
            partido.equipo_local if gana_local else partido.equipo_visitante)

    def _actuaciones(self, partido, planteles, locales, visitantes):
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
        for _ in range(goles):
            if self.rng.random() < PROBABILIDAD_EN_CONTRA:
                autor = self.rng.choice(rivales)
                registro.setdefault(autor, self._fila())['goles_en_contra'] += 1
                continue
            autor = self.rng.choice(propios)
            datos = registro.setdefault(autor, self._fila())
            datos['goles'] += 1
            if self.rng.random() < PROBABILIDAD_PENAL:
                datos['goles_de_penal'] += 1
            companeros = [j for j in propios if j != autor]
            if companeros and self.rng.random() < 0.55:
                registro.setdefault(self.rng.choice(companeros), self._fila())['asistencias'] += 1

    @staticmethod
    def _fila():
        return {'goles': 0, 'goles_en_contra': 0, 'goles_de_penal': 0, 'asistencias': 0}

    def _mostrar_resumen(self, categorias, hasta):
        limite = hasta or 'la final (cierra la categoria)'
        self.stdout.write(self.style.MIGRATE_HEADING(f'SE JUGARIA hasta {limite}:'))
        for categoria in categorias:
            motivo = liguilla.motivo_para_no_iniciar(categoria)
            estado = 'ya iniciada' if 'en marcha' in motivo else (motivo or 'lista para arrancar')
            mini = ' + mini-liguilla' if categoria.juega_mini_liguilla else ''
            self.stdout.write(f'  {categoria.nombre:10} {estado}{mini}')

    def _mostrar_jugado(self, liga, informe):
        self.stdout.write(self.style.SUCCESS(f'\n{liga.nombre}'))
        for datos in informe:
            categoria = datos['categoria']
            estado = 'CERRADA' if categoria.cerrada else 'en juego'
            self.stdout.write(
                f'\n  {categoria.nombre} · {datos["jugados"]} partidos · {estado}')
            for ronda in datos['rondas']:
                self.stdout.write(f'      {ronda}')
            registro = categoria.palmares.first()
            if registro:
                self.stdout.write(self.style.SUCCESS(
                    f'      campeon: {registro.campeon} · sub: {registro.subcampeon} '
                    f'· 3o: {registro.tercero}'))
            faltan = (Partido.objects.filter(categoria=categoria)
                      .exclude(fase=Partido.FASE_REGULAR)
                      .exclude(estado=Partido.ESTADO_FINALIZADO))
            if faltan.exists():
                pendiente = sorted({p.etiqueta for p in faltan})
                self.stdout.write(f'      pendiente: {", ".join(pendiente)}')
