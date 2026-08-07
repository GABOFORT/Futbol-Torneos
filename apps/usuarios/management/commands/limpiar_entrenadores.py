"""Elimina las cuentas de entrenador que quedaron sin ningun equipo.

    python manage.py limpiar_entrenadores              # solo lista, no borra
    python manage.py limpiar_entrenadores --confirmar  # borra

Son cuentas que sobraron de ligas eliminadas **antes** de que el borrado de liga
se llevara a sus entrenadores (ver `eliminar.entrenadores_sin_equipo_tras_borrar`).
De aca en adelante no se acumulan mas: se van con su liga.

Sin `--confirmar` no toca nada. Borrar cuentas de usuario no es reversible y
alguien pudo haber repartido esas contraseñas, asi que la lista se mira antes.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Lista o elimina los entrenadores que no dirigen ningun equipo.'

    def add_arguments(self, parser):
        parser.add_argument('--confirmar', action='store_true',
                            help='Elimina de verdad. Sin esto solo muestra la lista.')

    def handle(self, *args, **opciones):
        # `equipos__isnull=True` es la definicion exacta de "no dirige nada".
        # No se filtra por fecha ni por quien las creo: si no tiene equipo, la
        # cuenta no cumple ninguna funcion.
        sueltos = Usuario.objects.filter(
            role=Usuario.ROLE_ENTRENADOR, equipos__isnull=True,
        ).order_by('username')

        total = sueltos.count()
        if not total:
            self.stdout.write(self.style.SUCCESS('No hay entrenadores sin equipo.'))
            return

        nunca_entraron = sueltos.filter(last_login__isnull=True).count()
        self.stdout.write(f'{total} entrenador(es) sin ningun equipo '
                          f'({nunca_entraron} nunca iniciaron sesión):\n')
        for usuario in sueltos[:20]:
            entro = usuario.last_login.date() if usuario.last_login else 'nunca entró'
            self.stdout.write(f'   {usuario.username:24} {usuario.nombre_visible[:34]:34} {entro}')
        if total > 20:
            self.stdout.write(f'   ... y {total - 20} más')

        if not opciones['confirmar']:
            self.stdout.write(self.style.WARNING(
                '\nNo se borró nada. Volvé a correrlo con --confirmar para eliminarlas.'))
            return

        with transaction.atomic():
            borrados, _ = sueltos.delete()
        self.stdout.write(self.style.SUCCESS(
            f'\nEliminadas {total} cuenta(s) de entrenador sin equipo.'))
