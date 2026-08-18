from django.conf import settings
from django.db import models

from apps.usuarios.imagenes import achicar_imagen
from apps.usuarios.monograma import color_de, iniciales_de, monograma


class Equipo(models.Model):
    FORMACION_CHOICES = [
        ('4-4-2', '4-4-2'),
        ('4-3-3', '4-3-3'),
        ('3-5-2', '3-5-2'),
        ('5-3-2', '5-3-2'),
        ('4-2-3-1', '4-2-3-1'),
    ]

    nombre = models.CharField('Nombre del equipo', max_length=140)
    escudo = models.ImageField(
        'Escudo del equipo', upload_to='escudos/', blank=True, null=True,
        help_text='Opcional. Si lo dejas vacío se muestra un escudo neutro.',
    )
    entrenador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='equipos',
        limit_choices_to={'role': 'entrenador', 'is_superuser': False},
    )
    liga = models.ForeignKey(
        'torneos.Liga',
        on_delete=models.PROTECT,
        related_name='equipos',
    )
    categoria = models.ForeignKey(
        'torneos.Categoria',
        on_delete=models.PROTECT,
        related_name='equipos',
    )
    fecha_creacion = models.DateField('Fecha de registro', auto_now_add=True)
    jornada_ingreso = models.PositiveSmallIntegerField(
        'Entró en la jornada',
        null=True,
        blank=True,
        help_text='Solo si se inscribió con el calendario ya generado. Vacío es desde el inicio.',
    )
    formacion = models.CharField('Formación', max_length=20, choices=FORMACION_CHOICES, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        unique_together = ('nombre', 'liga', 'categoria')

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        achicar_imagen(self.escudo)
        super().save(*args, **kwargs)

    @property
    def iniciales(self):
        """'Bayern Munchen' -> 'BM'. Lo que va dentro del escudo generado."""
        return iniciales_de(self.nombre)

    @property
    def color(self):
        """El color propio del club, derivado de su nombre. Siempre el mismo."""
        return color_de(self.nombre)

    @property
    def escudo_url(self):
        """El escudo del equipo, o un monograma con sus iniciales si no tiene.

        Se resuelve aca y no en cada template para que el reemplazo sea uno solo:
        las trece pantallas que muestran un escudo piden esto.

        Antes devolvia una imagen gris igual para todos. Con 211 equipos sin
        escudo cargado, el calendario y las tablas quedaban llenos de manchas
        identicas y no se distinguia un club de otro. El monograma le da a cada
        uno sus iniciales y su color, y el dia que se suba un escudo de verdad
        pasa a mostrarse ese sin tocar nada.
        """
        if self.escudo:
            return self.escudo.url
        return monograma(self.nombre)
