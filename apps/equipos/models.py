from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.urls import reverse

from apps.usuarios import rutas
from apps.usuarios.estaticos import url_estatico
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

    LETRAS_GRUPO = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    GRUPO_CHOICES = [(letra, f'Grupo {letra}') for letra in LETRAS_GRUPO]

    nombre = models.CharField('Nombre del equipo', max_length=140)
    slug = models.SlugField('Nombre en la dirección', max_length=120, blank=True)
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
    grupo = models.CharField(
        'Grupo',
        max_length=1,
        choices=GRUPO_CHOICES,
        blank=True,
        default='',
        help_text='Solo en las categorías de torneo que se juegan por grupos.',
    )
    INSIGNIAS = [
        ('titulos_campeon', 'Campeón', 'img/insignias/titulo-oro.png'),
        ('titulos_subcampeon', 'Subcampeón', 'img/insignias/titulo-plata.png'),
        ('titulos_tercero', 'Tercer lugar', 'img/insignias/titulo-bronce.png'),
    ]

    TOPE_TITULOS = 50

    titulos_campeon = models.PositiveSmallIntegerField(
        'Veces campeón', default=0,
        validators=[MaxValueValidator(TOPE_TITULOS)],
    )
    titulos_subcampeon = models.PositiveSmallIntegerField(
        'Veces subcampeón', default=0,
        validators=[MaxValueValidator(TOPE_TITULOS)],
    )
    titulos_tercero = models.PositiveSmallIntegerField(
        'Veces tercer lugar', default=0,
        validators=[MaxValueValidator(TOPE_TITULOS)],
    )

    formacion = models.CharField('Formación', max_length=20, choices=FORMACION_CHOICES, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        unique_together = ('nombre', 'liga', 'categoria')
        constraints = [
            models.UniqueConstraint(fields=['categoria', 'slug'],
                                    name='equipo_slug_unico_por_categoria'),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        achicar_imagen(self.escudo)
        rutas.asignar(self, Equipo.objects.filter(categoria_id=self.categoria_id))
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('equipo-detail',
                       args=[self.liga.slug, self.categoria.slug, self.slug])

    @property
    def iniciales(self):
        """'Bayern Munchen' -> 'BM'. Lo que va dentro del escudo generado."""
        return iniciales_de(self.nombre)

    @property
    def color(self):
        """El color propio del club, derivado de su nombre. Siempre el mismo."""
        return color_de(self.nombre)

    @property
    def insignias(self):
        """Los titulos que el equipo traia antes de entrar a la liga.

        Salen del propio equipo y no del palmares: ese guarda lo que se gano
        aqui dentro y se calcula solo al cerrar una categoria. Estos los carga
        el administrador al dar de alta al equipo, y son la unica forma de
        reconocer lo que ganó en otro lado.

        Se resuelve como propiedad para que cualquier pantalla que ya tenga el
        equipo pueda pintarlas sin que su vista tenga que prepararlas.
        """
        salida = []
        for campo, etiqueta, imagen in self.INSIGNIAS:
            veces = getattr(self, campo)
            if veces:
                salida.append({
                    'imagen': url_estatico(imagen),
                    'etiqueta': etiqueta,
                    'veces': veces,
                    'titulo': f'{etiqueta} · {veces} vez' if veces == 1
                              else f'{etiqueta} · {veces} veces',
                })
        return salida

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
