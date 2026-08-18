"""Deshace el cierre de una categoria, para poder volver a probar la final.

Existe para el armado y las pruebas, no para el uso diario: en una liga de
verdad una final se juega una sola vez. Por eso es un comando de consola y no un
boton en pantalla, donde cualquier admin podria borrar un campeon sin querer.

    python manage.py reabrir_categoria 50            <- muestra que haria
    python manage.py reabrir_categoria 50 --aplicar  <- lo hace

Deja el partido de la final en 0-0 y programado, borra sus goleadores, elimina
el palmares y devuelve la categoria (y su liga) al estado de "en juego". No
toca la fecha ni la cancha de la final, ni ningun otro partido.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.partidos.models import Partido
from apps.torneos import palmares
from apps.torneos.models import Categoria, Palmares


class Command(BaseCommand):
    help = 'Deshace el cierre de una categoria y borra su palmares.'

    def add_arguments(self, parser):
        parser.add_argument('categoria_id', type=int)
        parser.add_argument(
            '--aplicar',
            action='store_true',
            help='Sin esta bandera solo se muestra lo que se haria, sin tocar nada.',
        )

    def handle(self, *args, **opciones):
        try:
            categoria = Categoria.objects.select_related('liga').get(pk=opciones['categoria_id'])
        except Categoria.DoesNotExist:
            raise CommandError(f'No existe la categoría {opciones["categoria_id"]}.')

        final = Partido.objects.filter(
            categoria=categoria, fase=Partido.FASE_FINAL
        ).select_related('equipo_local', 'equipo_visitante').first()
        registro = Palmares.objects.filter(categoria=categoria).first()

        self.stdout.write(f'{categoria.liga.nombre} / {categoria.nombre}')
        self.stdout.write(f'  categoría cerrada : {categoria.cerrada}')
        self.stdout.write(f'  liga cerrada      : {categoria.liga.cerrada}')
        self.stdout.write(f'  palmarés          : {"sí, campeón " + registro.campeon if registro else "no hay"}')
        if final:
            self.stdout.write(
                f'  final             : {final.equipo_local} {final.goles_local}-'
                f'{final.goles_visitante} {final.equipo_visitante} [{final.estado}]'
            )
        else:
            self.stdout.write('  final             : no existe todavía')

        if not categoria.cerrada and not registro and not (final and final.jugado):
            self.stdout.write(self.style.WARNING('\nNo hay nada que deshacer.'))
            return

        if not opciones['aplicar']:
            self.stdout.write(self.style.WARNING(
                '\nEsto es solo una vista previa. Vuelve a ejecutarlo con --aplicar para hacerlo.'
            ))
            return

        with transaction.atomic():
            if final and final.jugado:
                final.actuaciones.all().delete()
                final.goles_local = final.goles_visitante = 0
                final.ganador_penales = None
                final.penales_local = final.penales_visitante = None
                final.estado = Partido.ESTADO_PROGRAMADO
                final.save()
            palmares.reabrir(categoria)

        self.stdout.write(self.style.SUCCESS(
            f'\nListo. "{categoria.nombre}" volvió a estar en juego y ya puedes cargar la final otra vez.'
        ))
