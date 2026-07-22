from django.db import models


class Jugador(models.Model):
    POSICIONES = [
        ('portero', 'Portero'),
        ('defensa', 'Defensa'),
        ('medio', 'Mediocampista'),
        ('delantero', 'Delantero'),
    ]

    ESTADO_ACTIVO = 'activo'
    ESTADO_BAJA = 'baja'
    ESTADO_LESION = 'lesion'
    ESTADO_SANCION = 'sancion'

    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, 'Activo'),
        (ESTADO_BAJA, 'Baja'),
        (ESTADO_LESION, 'Lesionado'),
        (ESTADO_SANCION, 'Sancionado'),
    ]

    equipo = models.ForeignKey(
        'equipos.Equipo',
        on_delete=models.CASCADE,
        related_name='jugadores',
    )
    foto = models.ImageField('Foto', upload_to='jugadores/', blank=True, null=True)
    nombre = models.CharField('Nombre', max_length=100)
    apellido = models.CharField('Apellido', max_length=100)
    documento = models.CharField('Documento', max_length=50, blank=True)
    fecha_nacimiento = models.DateField('Fecha de nacimiento', null=True, blank=True)
    posicion = models.CharField('Posición', max_length=20, choices=POSICIONES, default='medio')
    numero = models.PositiveIntegerField('Número', null=True, blank=True)
    estado = models.CharField('Estado del jugador', max_length=20, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)
    activo = models.BooleanField('Activo', default=True)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Jugador'
        verbose_name_plural = 'Jugadores'

    def __str__(self):
        return f'{self.nombre} {self.apellido} ({self.equipo.nombre})'
