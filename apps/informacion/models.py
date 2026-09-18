from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

from apps.usuarios.imagenes import achicar_imagen
from apps.usuarios.monograma import monograma


class PatrocinadorOficialQuerySet(models.QuerySet):
    def visibles(self):
        return self.filter(activo=True)


class PatrocinadorOficial(models.Model):
    nombre = models.CharField('Nombre del patrocinador', max_length=140)
    logo = models.ImageField(
        'Logo', upload_to='aliados-oficiales/', blank=True, null=True,
        help_text='Opcional. Si lo dejas vacío se muestran sus iniciales.',
    )
    giro = models.CharField(
        'Giro o actividad', max_length=120, blank=True,
        help_text='Taquería, refaccionaria, farmacia… Se muestra en su ficha.',
    )
    direccion = models.CharField('Dirección', max_length=255, blank=True)
    latitud = models.DecimalField(
        'Latitud', max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(
        'Longitud', max_digits=9, decimal_places=6, null=True, blank=True)
    telefono = models.CharField(
        'Teléfono', max_length=10, blank=True,
        validators=[RegexValidator(
            r'^\d{10}$',
            'El teléfono debe tener exactamente 10 dígitos, sin letras ni signos.',
        )],
    )
    enlace = models.URLField(
        'Sitio web o red social', max_length=300, blank=True,
        help_text='Opcional. Aparece como un botón dentro de su ficha.',
    )
    orden = models.PositiveSmallIntegerField('Orden', default=0)
    activo = models.BooleanField(
        'Visible', default=True,
        help_text='Desmárcalo para esconderlo sin perder sus datos.',
    )

    objects = PatrocinadorOficialQuerySet.as_manager()

    class Meta:
        verbose_name = 'Patrocinador oficial'
        verbose_name_plural = 'Patrocinadores oficiales'
        ordering = ['orden', 'nombre']
        constraints = [
            models.UniqueConstraint(
                Lower('nombre'),
                name='patrocinador_oficial_nombre_unico',
                violation_error_message='Ya hay un patrocinador oficial con ese nombre.',
            ),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        achicar_imagen(self.logo)
        super().save(*args, **kwargs)

    def clean(self):
        if (self.latitud is None) != (self.longitud is None):
            raise ValidationError(
                'Marca el punto en el mapa o déjalo sin marcar, pero no a medias.')

    @property
    def logo_url(self):
        if self.logo:
            return self.logo.url
        return monograma(self.nombre)

    @property
    def ubicado(self):
        return self.latitud is not None and self.longitud is not None

    @property
    def _consulta_de_mapa(self):
        if self.ubicado:
            return f'{self.latitud},{self.longitud}'
        return quote(self.direccion) if self.direccion else ''

    @property
    def url_mapa(self):
        consulta = self._consulta_de_mapa
        return f'https://maps.google.com/maps?q={consulta}&z=16&output=embed' if consulta else ''

    @property
    def url_como_llegar(self):
        consulta = self._consulta_de_mapa
        return f'https://www.google.com/maps/search/?api=1&query={consulta}' if consulta else ''
