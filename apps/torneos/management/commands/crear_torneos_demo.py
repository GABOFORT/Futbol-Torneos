"""Arma torneos relámpago de un admin de liga en distintos puntos de su vida.

    python manage.py crear_torneos_demo --admin MHERRERA
    python manage.py crear_torneos_demo --admin MHERRERA --resumen

Uno recién creado, uno en semifinales, uno esperando la final y dos terminados
—uno de hace poco, otro con el mes de exhibición ya cumplido—, para poder ver
cómo se comporta la cuota y la regla de los 30 días.

Para repartir torneos entre todos los admins está `repartir_torneos`.
"""
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.torneos.models import Torneo
from apps.usuarios.models import Usuario

from ._torneos_demo import Constructor, FINAL, NUEVO, SEMIFINAL, TERMINADO

SEMILLA = 2026

PLANES = [
    ('Copa Apertura', 8, TERMINADO, 40),
    ('Copa Invierno', 8, TERMINADO, 5),
    ('Copa Primavera', 8, FINAL, 1),
    ('Copa Verano', 16, SEMIFINAL, 1),
    ('Copa Clausura', 8, NUEVO, 0),
]


class Command(BaseCommand):
    help = 'Crea torneos relámpago de ejemplo en distintos estados.'

    def add_arguments(self, parser):
        parser.add_argument('--admin', required=True,
                            help='username del Administrador de Liga.')
        parser.add_argument('--resumen', action='store_true')

    def handle(self, *args, **opciones):
        self.rng = random.Random(SEMILLA)
        self.constructor = Constructor(self.rng)
        admin = self._admin(opciones['admin'])

        if opciones['resumen']:
            self._mostrar_resumen(admin)
            return

        with transaction.atomic():
            creados = [
                (self.constructor.armar(admin, nombre, equipos, estado, dias), estado)
                for nombre, equipos, estado, dias in PLANES
                if not Torneo.objects.filter(liga__nombre=nombre).exists()
            ]
            self._ajustar_cuota(admin)
        self._mostrar_creado(admin, creados)

    def _admin(self, username):
        admin = Usuario.objects.filter(username=username).first()
        if admin is None:
            raise CommandError(f'No existe el usuario "{username}".')
        if not admin.es_admin_liga():
            raise CommandError(f'"{username}" no es Administrador de Liga.')
        return admin

    def _ajustar_cuota(self, admin):
        """La cuota tiene que dar para los que quedan en curso."""
        en_curso = Torneo.objects.filter(liga__administradores=admin).en_curso().count()
        if admin.limite_torneos < en_curso:
            admin.limite_torneos = en_curso
            admin.save(update_fields=['limite_torneos'])

    def _mostrar_resumen(self, admin):
        self.stdout.write(self.style.MIGRATE_HEADING(f'SE CREARIA para {admin.username}:'))
        for nombre, equipos, estado, dias in PLANES:
            existe = Torneo.objects.filter(liga__nombre=nombre).exists()
            marca = ' (ya existe)' if existe else ''
            self.stdout.write(
                f'  {nombre:16} {equipos:2} equipos · {estado:10} · '
                f'hace {dias:2} día(s){marca}')

    def _mostrar_creado(self, admin, creados):
        self.stdout.write(self.style.SUCCESS(f'\nTorneos de {admin.username}'))
        for torneo, estado in creados:
            torneo.refresh_from_db()
            detalle = f'campeón: {torneo.campeon.nombre}' if torneo.terminado else estado
            vitrina = (f' · en vitrina {torneo.dias_en_vitrina} día(s)'
                       if torneo.terminado else '')
            self.stdout.write(
                f'  {torneo.nombre:16} {torneo.equipos:2} equipos · '
                f'{torneo.fecha} · {detalle}{vitrina}')

        en_curso = Torneo.objects.filter(liga__administradores=admin).en_curso().count()
        self.stdout.write(self.style.SUCCESS(
            f'\n{en_curso} en curso de {admin.limite_torneos} de cuota. '
            f'Los terminados no ocupan lugar.'))
