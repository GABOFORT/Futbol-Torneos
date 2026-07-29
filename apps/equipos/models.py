from django.conf import settings
from django.db import models

from apps.usuarios.estaticos import url_estatico
from apps.usuarios.imagenes import achicar_imagen


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
        # is_superuser=False acompana a Usuario.objects.entrenadores(): una
        # cuenta de superadmin no debe ofrecerse como entrenador de un equipo.
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
    def escudo_url(self):
        """El escudo del equipo, o el neutro cuando no cargaron ninguno.

        Se resuelve aca y no en cada template para que el placeholder sea uno
        solo: si algun dia cambia la imagen, se cambia en un unico lugar.
        """
        if self.escudo:
            return self.escudo.url
        return url_estatico('img/escudo-vacio.jpg')
