"""Reparte los torneos relámpago entre los administradores de liga.

    python manage.py repartir_torneos
    python manage.py repartir_torneos --resumen
    python manage.py repartir_torneos --terminados 2 --en-curso 1

Cada admin queda con la misma cartera: unos cuantos torneos ya terminados y uno
solo en curso. Primero se reparten los que ya existen —según su estado— y solo
se crean los que falten, para no tirar nada de lo que ya hay cargado.

Los entrenadores de un torneo se mudan con él: `creado_por` define quién los ve,
y un torneo sin sus entrenadores no se puede administrar.
"""
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.equipos.models import Equipo
from apps.torneos.models import Torneo
from apps.usuarios.models import Usuario

from ._torneos_demo import Constructor, FINAL, NUEVO, SEMIFINAL, TERMINADO

SEMILLA = 2026

PLANTILLAS_TERMINADOS = [
    ('Copa Apertura', 8, 55),
    ('Copa Invierno', 8, 20),
    ('Copa Otoño', 16, 35),
    ('Copa Aniversario', 8, 12),
]
PLANTILLAS_EN_CURSO = [
    ('Copa Clausura', 8, NUEVO, 0),
    ('Copa Primavera', 8, FINAL, 1),
    ('Copa Verano', 16, SEMIFINAL, 1),
]


class Command(BaseCommand):
    help = 'Reparte los torneos relámpago entre los administradores de liga.'

    def add_arguments(self, parser):
        parser.add_argument('--terminados', type=int, default=2)
        parser.add_argument('--en-curso', type=int, default=1, dest='en_curso')
        parser.add_argument('--resumen', action='store_true')

    def handle(self, *args, **opciones):
        self.rng = random.Random(SEMILLA)
        self.constructor = Constructor(self.rng)
        self.cuantos_terminados = opciones['terminados']
        self.cuantos_en_curso = opciones['en_curso']

        admins = list(Usuario.objects.filter(
            role=Usuario.ROLE_ADMIN_LIGA).order_by('username'))
        if opciones['resumen']:
            self._mostrar_resumen(admins)
            return

        with transaction.atomic():
            reparto = self._repartir(admins)
        self._mostrar_reparto(reparto)

    def _libres(self):
        """Los torneos disponibles, separados por estado."""
        todos = Torneo.objects.select_related('liga')
        return (list(todos.terminados().order_by('fecha')),
                list(todos.en_curso().order_by('fecha')))

    def _repartir(self, admins):
        terminados, en_curso = self._libres()
        reparto = []

        for admin in admins:
            fila = {'admin': admin, 'terminados': [], 'en_curso': [], 'creados': 0}

            for destino, disponibles, ya_termino in (
                    ('terminados', terminados, True),
                    ('en_curso', en_curso, False)):
                cuantos = (self.cuantos_terminados if ya_termino
                           else self.cuantos_en_curso)
                for _ in range(cuantos):
                    if disponibles:
                        torneo = self._mudar(disponibles.pop(0), admin)
                    else:
                        torneo = self._crear(admin, ya_termino)
                        fila['creados'] += 1
                    fila[destino].append(torneo)

            admin.limite_torneos = self.cuantos_en_curso
            admin.save(update_fields=['limite_torneos'])
            reparto.append(fila)

        return reparto

    def _mudar(self, torneo, admin):
        """Pasa el torneo a otro admin, con sus entrenadores."""
        torneo.liga.administradores.set([admin])
        if torneo.creado_por_id != admin.pk:
            torneo.creado_por = admin
            torneo.save(update_fields=['creado_por'])
        Usuario.objects.filter(
            equipos__in=Equipo.objects.filter(liga=torneo.liga)
        ).distinct().update(creado_por=admin)
        return torneo

    def _nombre_libre(self, admin, base):
        propia = admin.ligas_administradas.filter(torneo__isnull=True).first()
        etiqueta = propia.nombre if propia else admin.nombre_visible
        propuesto = f'{etiqueta} · {base}'
        numero = 2
        while Torneo.objects.filter(liga__nombre=propuesto).exists():
            propuesto = f'{etiqueta} · {base} {numero}'
            numero += 1
        return propuesto

    def _crear(self, admin, ya_termino):
        if ya_termino:
            base, equipos, dias = self.rng.choice(PLANTILLAS_TERMINADOS)
            estado = TERMINADO
        else:
            base, equipos, estado, dias = self.rng.choice(PLANTILLAS_EN_CURSO)
        return self.constructor.armar(
            admin, self._nombre_libre(admin, base), equipos, estado, dias)

    def _mostrar_resumen(self, admins):
        terminados, en_curso = self._libres()
        faltan_t = max(0, self.cuantos_terminados * len(admins) - len(terminados))
        faltan_c = max(0, self.cuantos_en_curso * len(admins) - len(en_curso))
        self.stdout.write(self.style.MIGRATE_HEADING('REPARTO:'))
        self.stdout.write(
            f'  {len(admins)} admin(s) × ({self.cuantos_terminados} terminado(s) + '
            f'{self.cuantos_en_curso} en curso)')
        self.stdout.write(
            f'  disponibles: {len(terminados)} terminados, {len(en_curso)} en curso')
        self.stdout.write(f'  se crearían: {faltan_t} terminados, {faltan_c} en curso')
        for admin in admins:
            self.stdout.write(f'     {admin.username}')

    def _mostrar_reparto(self, reparto):
        for fila in reparto:
            admin = fila['admin']
            self.stdout.write(self.style.SUCCESS(
                f'\n{admin.username} · {admin.nombre_visible} '
                f'(límite {admin.limite_torneos})'))
            for torneo in fila['terminados']:
                torneo.refresh_from_db()
                campeon = torneo.campeon.nombre if torneo.campeon else '—'
                self.stdout.write(
                    f'   terminado  {torneo.nombre:36} {torneo.equipos:2}eq · '
                    f'{campeon} · vitrina {torneo.dias_en_vitrina}d')
            for torneo in fila['en_curso']:
                torneo.refresh_from_db()
                estado = 'sorteado' if torneo.sorteado else 'sin sortear'
                self.stdout.write(
                    f'   en curso   {torneo.nombre:36} {torneo.equipos:2}eq · {estado}')

        creados = sum(f['creados'] for f in reparto)
        self.stdout.write(self.style.SUCCESS(
            f'\n{len(reparto)} admin(s) repartidos. {creados} torneo(s) creados; '
            f'el resto se reasignó.'))
