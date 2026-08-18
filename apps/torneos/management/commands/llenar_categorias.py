"""Llena las categorias vacias de una liga con equipos y sus entrenadores.

    python manage.py llenar_categorias --liga "Serie A"
    python manage.py llenar_categorias --liga "Serie A" --resumen
    python manage.py llenar_categorias --liga "Serie A" --categoria Sub-10 --categoria Sub-11

Solo toca categorias SIN equipos: una categoria en juego no se altera. No crea
jugadores.

Las contrasenas se generan al azar y se guardan en `credenciales-<liga>.csv`,
que esta en .gitignore. Es la unica copia: en la base quedan hasheadas.
"""
import csv
import random
import unicodedata
from pathlib import Path

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.crypto import get_random_string

from apps.equipos.models import Equipo
from apps.torneos.models import Categoria, Liga
from apps.usuarios.models import Usuario

from ._clubes import CLUBES, NOMBRES

SEMILLA = 2026
PAIS = 'italia'
LARGO_CONTRASENA = 12
ALFABETO = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
PROPORCION_VARONES = 0.8


def sin_acentos(texto):
    normalizado = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in normalizado if not unicodedata.combining(c))


def slug(texto):
    limpio = sin_acentos(texto).lower().replace("'", '')
    return '-'.join(limpio.split())


class Command(BaseCommand):
    help = 'Crea equipos y entrenadores en las categorias vacias de una liga.'

    def add_arguments(self, parser):
        parser.add_argument('--liga', required=True,
                            help='Nombre exacto de la liga.')
        parser.add_argument('--categoria', action='append', dest='categorias',
                            help='Limita a estas categorias. Se puede repetir.')
        parser.add_argument('--resumen', action='store_true',
                            help='Muestra que se crearia, sin tocar la base.')

    def handle(self, *args, **opciones):
        self.rng = random.Random(SEMILLA)
        liga = self._liga(opciones['liga'])
        categorias = self._categorias(liga, opciones['categorias'])

        if not categorias:
            self.stdout.write(self.style.WARNING(
                'No hay categorias vacias que llenar en esta liga.'))
            return

        if opciones['resumen']:
            self._mostrar_resumen(liga, categorias)
            return

        with transaction.atomic():
            filas = self._llenar(liga, categorias)

        ruta = self._guardar_credenciales(liga, filas)
        self._mostrar_creado(liga, categorias, filas, ruta)

    def _liga(self, nombre):
        liga = Liga.objects.filter(nombre=nombre).first()
        if liga is None:
            existentes = ', '.join(Liga.objects.values_list('nombre', flat=True))
            raise CommandError(f'No existe la liga "{nombre}". Hay: {existentes}')
        if self._responsable(liga) is None:
            raise CommandError(
                f'"{nombre}" no tiene administrador ni creador, y los entrenadores '
                f'tienen que quedar a nombre de alguien para que se puedan administrar.')
        return liga

    @staticmethod
    def _responsable(liga):
        """A nombre de quien quedan los entrenadores.

        Un torneo creado por el Administrador General no tiene administradores en
        su liga: el responsable es quien lo creo.
        """
        admin = liga.administradores.first()
        if admin is not None:
            return admin
        torneo = getattr(liga, 'torneo', None)
        return torneo.creado_por if torneo else None

    @staticmethod
    def _es_torneo(liga):
        return hasattr(liga, 'torneo')

    def _categorias(self, liga, nombres):
        categorias = liga.categorias.order_by('nombre')
        if nombres:
            categorias = categorias.filter(nombre__in=nombres)
            faltan = set(nombres) - {c.nombre for c in categorias}
            if faltan:
                raise CommandError(
                    f'"{liga.nombre}" no tiene estas categorias: {", ".join(sorted(faltan))}')
        return [c for c in categorias if not c.equipos.exists()]

    def _clubes_para(self, categoria):
        disponibles = CLUBES[PAIS]
        if categoria.cupo_equipos > len(disponibles):
            raise CommandError(
                f'"{categoria.nombre}" tiene cupo {categoria.cupo_equipos} y solo hay '
                f'{len(disponibles)} clubes cargados en _clubes.py.')
        return disponibles[:categoria.cupo_equipos]

    def _llenar(self, liga, categorias):
        admin = self._responsable(liga)
        filas = []
        for categoria in categorias:
            for club in self._clubes_para(categoria):
                entrenador, clave = self._crear_entrenador(liga, categoria, club, admin)
                Equipo.objects.create(
                    nombre=club, liga=liga, categoria=categoria, entrenador=entrenador)
                filas.append({
                    'liga': liga.nombre,
                    'categoria': categoria.nombre,
                    'equipo': club,
                    'entrenador': entrenador.get_full_name(),
                    'usuario': entrenador.username,
                    'contrasena': clave,
                })
        return filas

    def _crear_entrenador(self, liga, categoria, club, admin):
        sexo = 'varon' if self.rng.random() < PROPORCION_VARONES else 'mujer'
        datos = NOMBRES[PAIS]
        nombre = self.rng.choice(datos[sexo])
        apellido = self.rng.choice(datos['apellidos'])
        usuario = self._usuario_libre(liga, club, categoria)
        clave = self._contrasena(usuario)

        entrenador = Usuario(
            username=usuario,
            first_name=nombre,
            last_name=apellido,
            role=Usuario.ROLE_ENTRENADOR,
            organization=club,
            creado_por=admin,
        )
        entrenador.set_password(clave)
        entrenador.save()
        return entrenador, clave

    def _usuario_libre(self, liga, club, categoria):
        if self._es_torneo(liga):
            base = f'{slug(liga.nombre)}-{slug(club)}'[:140]
        else:
            base = f'{slug(club)}-{slug(categoria.nombre)}'[:140]
        candidato, sufijo = base, 2
        while Usuario.objects.filter(username=candidato).exists():
            candidato = f'{base}-{sufijo}'
            sufijo += 1
        return candidato

    def _contrasena(self, usuario):
        """Una clave al azar que pase los validadores del proyecto."""
        for _ in range(20):
            clave = get_random_string(LARGO_CONTRASENA, ALFABETO)
            try:
                validate_password(clave, Usuario(username=usuario))
            except ValidationError:
                continue
            return clave
        raise CommandError('No se pudo generar una contrasena valida.')

    def _guardar_credenciales(self, liga, filas):
        """Agrega al CSV de la liga. Nunca lo pisa: es la unica copia que hay.

        Las contrasenas se guardan hasheadas en la base, asi que reescribir el
        archivo dejaria sin acceso a los entrenadores de una corrida anterior.
        """
        ruta = Path(settings.BASE_DIR) / f'credenciales-{slug(liga.nombre)}.csv'
        columnas = ['liga', 'categoria', 'equipo', 'entrenador', 'usuario', 'contrasena']
        existia = ruta.exists()
        with ruta.open('a', newline='', encoding='utf-8-sig') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=columnas)
            if not existia:
                escritor.writeheader()
            escritor.writerows(filas)
        return ruta

    def _mostrar_resumen(self, liga, categorias):
        self.stdout.write(self.style.MIGRATE_HEADING(f'SE CREARIA en {liga.nombre}:'))
        total = 0
        for categoria in categorias:
            clubes = self._clubes_para(categoria)
            total += len(clubes)
            self.stdout.write(
                f'  {categoria.nombre:10} {len(clubes):3} equipos  '
                f'({clubes[0]} … {clubes[-1]})')
        self.stdout.write(f'\n  {total} equipos y {total} entrenadores. Sin jugadores.')
        self.stdout.write('  Las categorias con equipos no se tocan.')

    def _mostrar_creado(self, liga, categorias, filas, ruta):
        self.stdout.write(self.style.SUCCESS(f'\n{liga.nombre}'))
        for categoria in categorias:
            self.stdout.write(
                f'   {categoria.nombre:10} {categoria.equipos.count():3} equipos '
                f'· cupo {categoria.cupo_equipos}')
        self.stdout.write(self.style.SUCCESS(
            f'\n{len(filas)} equipos y {len(filas)} entrenadores creados. Sin jugadores.'))
        self.stdout.write(f'Credenciales en: {ruta}')
        self.stdout.write(self.style.WARNING(
            'Es la unica copia de las contrasenas: en la base quedan hasheadas.'))
