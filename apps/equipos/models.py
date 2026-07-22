from django.conf import settings
from django.db import models


class Equipo(models.Model):
    FORMACION_CHOICES = [
        ('4-4-2', '4-4-2'),
        ('4-3-3', '4-3-3'),
        ('3-5-2', '3-5-2'),
        ('5-3-2', '5-3-2'),
        ('4-2-3-1', '4-2-3-1'),
    ]

    nombre = models.CharField('Nombre del equipo', max_length=140)
    entrenador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='equipos',
        limit_choices_to={'role': 'entrenador'},
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
    formacion = models.CharField('Formación', max_length=20, choices=FORMACION_CHOICES, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        unique_together = ('nombre', 'liga', 'categoria')

    def __str__(self):
        return self.nombre
