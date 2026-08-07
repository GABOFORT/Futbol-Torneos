from django.db import models

from apps.usuarios.imagenes import achicar_imagen


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

    SEXO_MASCULINO = 'masculino'
    SEXO_FEMENINO = 'femenino'

    SEXO_CHOICES = [
        (SEXO_MASCULINO, 'Masculino'),
        (SEXO_FEMENINO, 'Femenino'),
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
    # No es un dato descriptivo: define en que categoria puede jugar. Las mujeres
    # entran con un año mas que el limite (en U17 juega una de 18), asi que sin
    # este campo no se puede validar la edad. La regla vive en
    # Categoria.ANIOS_EXTRA_FEMENINO, no aca.
    #
    # El default es masculino porque es el limite estricto: si alguien se guarda
    # sin elegir, no se regala un año de gracia. El formulario igual lo pide
    # siempre de forma explicita.
    sexo = models.CharField(
        'Sexo',
        max_length=10,
        choices=SEXO_CHOICES,
        default=SEXO_MASCULINO,
        help_text='Define el límite de edad: las mujeres entran con un año más que la categoría.',
    )
    fecha_nacimiento = models.DateField('Fecha de nacimiento', null=True, blank=True)
    posicion = models.CharField('Posición', max_length=20, choices=POSICIONES, default='medio')
    numero = models.PositiveIntegerField('Número', null=True, blank=True)
    estado = models.CharField('Estado del jugador', max_length=20, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Jugador'
        verbose_name_plural = 'Jugadores'
        constraints = [
            # El dorsal no se puede repetir dentro del mismo equipo. La condicion
            # deja fuera a los que no tienen numero: de esos puede haber varios.
            models.UniqueConstraint(
                fields=['equipo', 'numero'],
                condition=models.Q(numero__isnull=False),
                name='dorsal_unico_por_equipo',
                violation_error_message='Ese número ya lo tiene otro jugador del equipo.',
            ),
        ]

    def __str__(self):
        return f'{self.nombre} {self.apellido} ({self.equipo.nombre})'

    @property
    def es_femenino(self):
        return self.sexo == self.SEXO_FEMENINO

    @property
    def edad_maxima_permitida(self):
        """Los años que puede tener este jugador en su categoria.

        Se pregunta desde la plantilla para poder explicar por que una jugadora
        de 18 esta en U17 sin que parezca un error de carga.
        """
        categoria = self.equipo.categoria if self.equipo_id else None
        return categoria.edad_maxima_para(self.sexo) if categoria else None

    def save(self, *args, **kwargs):
        achicar_imagen(self.foto)
        super().save(*args, **kwargs)
