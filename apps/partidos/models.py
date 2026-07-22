from django.db import models


class Partido(models.Model):
    ESTADO_PROGRAMADO = 'programado'
    ESTADO_FINALIZADO = 'finalizado'
    ESTADO_CANCELADO = 'cancelado'

    ESTADO_CHOICES = [
        (ESTADO_PROGRAMADO, 'Programado'),
        (ESTADO_FINALIZADO, 'Finalizado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    categoria = models.ForeignKey(
        'torneos.Categoria',
        on_delete=models.CASCADE,
        related_name='partidos',
    )
    equipo_local = models.ForeignKey(
        'equipos.Equipo',
        on_delete=models.CASCADE,
        related_name='partidos_local',
    )
    equipo_visitante = models.ForeignKey(
        'equipos.Equipo',
        on_delete=models.CASCADE,
        related_name='partidos_visitante',
    )
    fecha = models.DateTimeField('Fecha y hora', null=True, blank=True)
    goles_local = models.PositiveIntegerField('Goles local', default=0)
    goles_visitante = models.PositiveIntegerField('Goles visitante', default=0)
    estado = models.CharField('Estado', max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PROGRAMADO)

    class Meta:
        verbose_name = 'Partido'
        verbose_name_plural = 'Partidos'
        ordering = ['fecha']

    def __str__(self):
        fecha = self.fecha.strftime('%Y-%m-%d') if self.fecha else 'sin fecha'
        return f'{self.equipo_local} vs {self.equipo_visitante} - {fecha}'
