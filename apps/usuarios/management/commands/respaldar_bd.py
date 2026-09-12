import os
import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

CARPETA_POSTGRES = Path(r'C:\Program Files\PostgreSQL')

CONSERVAR = 30

EXTENSION = '.dump'

TIEMPO_LIMITE = 1800


class Command(BaseCommand):
    help = 'Guarda un respaldo comprimido de la base de datos y comprueba que se pueda leer.'

    def add_arguments(self, parser):
        parser.add_argument('--carpeta',
                            help='Donde guardar los respaldos. Por defecto, respaldos/ del proyecto.')
        parser.add_argument('--conservar', type=int, default=CONSERVAR,
                            help=f'Cuantos respaldos mantener. Por defecto {CONSERVAR}.')
        parser.add_argument('--bin',
                            help='Carpeta bin de PostgreSQL, si no se encuentra sola.')

    def handle(self, *args, **opciones):
        volcar, restaurar = self._herramientas(opciones['bin'])
        base = settings.DATABASES['default']
        carpeta = self._carpeta(opciones['carpeta'])

        marca = timezone.localtime().strftime('%Y%m%d-%H%M%S')
        destino = carpeta / f'{base["NAME"]}_{marca}{EXTENSION}'

        self.stdout.write(f'Respaldando {base["NAME"]} en {destino.name}')

        inicio = timezone.now()
        self._volcar(volcar, base, destino)
        tablas = self._comprobar(restaurar, destino)
        segundos = (timezone.now() - inicio).total_seconds()

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {tablas} tablas, {self._peso(destino)}, {segundos:.1f} s'))

        borrados = self._rotar(carpeta, opciones['conservar'])
        if borrados:
            self.stdout.write(f'Se quitaron {borrados} respaldos viejos.')

        self.stdout.write(f'Se conservan {len(self._respaldos(carpeta))} en {carpeta}')

    def _herramientas(self, indicada):
        carpetas = [Path(indicada)] if indicada else sorted(
            CARPETA_POSTGRES.glob('*/bin'),
            key=lambda ruta: self._version(ruta.parent.name),
            reverse=True,
        )
        for carpeta in carpetas:
            volcar = carpeta / 'pg_dump.exe'
            restaurar = carpeta / 'pg_restore.exe'
            if volcar.is_file() and restaurar.is_file():
                return volcar, restaurar
        buscado = ', '.join(str(carpeta) for carpeta in carpetas) or str(CARPETA_POSTGRES)
        raise CommandError(
            f'No se encontro pg_dump.exe ni pg_restore.exe en: {buscado}\n'
            f'Con --bin se puede indicar la carpeta bin de PostgreSQL.')

    def _version(self, nombre):
        numeros = re.findall(r'\d+', nombre)
        return [int(numero) for numero in numeros] or [0]

    def _carpeta(self, indicada):
        carpeta = Path(indicada) if indicada else Path(settings.BASE_DIR) / 'respaldos'
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise CommandError(f'No se pudo crear la carpeta {carpeta}: {error}')
        return carpeta

    def _volcar(self, volcar, base, destino):
        orden = [
            str(volcar),
            '--host', base['HOST'] or 'localhost',
            '--port', str(base['PORT'] or 5432),
            '--username', base['USER'],
            '--dbname', base['NAME'],
            '--format', 'custom',
            '--compress', '9',
            '--no-password',
            '--file', str(destino),
        ]
        entorno = {**os.environ, 'PGPASSWORD': base['PASSWORD']}
        resultado = self._correr(orden, entorno)
        if resultado.returncode or not destino.is_file() or not destino.stat().st_size:
            destino.unlink(missing_ok=True)
            raise CommandError(
                f'pg_dump fallo y no se guardo nada.\n{resultado.stderr.strip()}')

    def _comprobar(self, restaurar, destino):
        resultado = self._correr([str(restaurar), '--list', str(destino)], os.environ)
        if resultado.returncode:
            destino.unlink(missing_ok=True)
            raise CommandError(
                f'El respaldo se escribio pero no se puede leer, asi que se descarto.\n'
                f'{resultado.stderr.strip()}')
        tablas = resultado.stdout.count('TABLE DATA')
        if not tablas:
            destino.unlink(missing_ok=True)
            raise CommandError('El respaldo no contiene ninguna tabla con datos. Se descarto.')
        return tablas

    def _correr(self, orden, entorno):
        try:
            return subprocess.run(
                orden, env=entorno, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=TIEMPO_LIMITE)
        except subprocess.TimeoutExpired:
            raise CommandError(f'{Path(orden[0]).name} tardo mas de {TIEMPO_LIMITE} segundos.')
        except OSError as error:
            raise CommandError(f'No se pudo ejecutar {orden[0]}: {error}')

    def _respaldos(self, carpeta):
        return sorted(carpeta.glob(f'*{EXTENSION}'),
                      key=lambda ruta: ruta.stat().st_mtime, reverse=True)

    def _rotar(self, carpeta, conservar):
        if conservar < 1:
            return 0
        sobrantes = self._respaldos(carpeta)[conservar:]
        for ruta in sobrantes:
            ruta.unlink(missing_ok=True)
        return len(sobrantes)

    def _peso(self, ruta):
        tamano = ruta.stat().st_size
        for unidad in ('B', 'KB', 'MB', 'GB'):
            if tamano < 1024 or unidad == 'GB':
                return f'{tamano:.0f} {unidad}' if unidad == 'B' else f'{tamano:.1f} {unidad}'
            tamano /= 1024
