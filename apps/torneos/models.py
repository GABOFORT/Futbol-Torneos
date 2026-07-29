import datetime

from django.conf import settings
from django.db import models

from apps.usuarios.imagenes import achicar_imagen


class Liga(models.Model):
    nombre = models.CharField('Nombre de la liga', max_length=150)
    logo = models.ImageField(
        'Logo de la liga', upload_to='logos-ligas/', blank=True, null=True,
        help_text='Opcional. Si lo dejas vacío se muestran las iniciales de la liga.',
    )
    descripcion = models.TextField('Descripción', blank=True)
    administradores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='ligas_administradas',
        limit_choices_to={'role': 'adminliga'},
    )
    fecha_inicio = models.DateField('Fecha de inicio', null=True, blank=True)
    fecha_final = models.DateField('Fecha de finalización', null=True, blank=True)
    activa = models.BooleanField('Liga activa', default=True)

    fecha_pago = models.DateField('Fecha del último pago', null=True, blank=True)
    dias_gracia = models.PositiveIntegerField('Días de gracia', default=3)

    class Meta:
        verbose_name = 'Liga'
        verbose_name_plural = 'Ligas'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        achicar_imagen(self.logo)
        super().save(*args, **kwargs)

    @property
    def iniciales(self):
        """Reemplazo del logo cuando no hay: 'LIGA MX' -> 'LM'."""
        palabras = [p for p in self.nombre.split() if p]
        if len(palabras) >= 2:
            return (palabras[0][:1] + palabras[1][:1]).upper()
        return self.nombre[:2].upper()

    @property
    def fecha_vencimiento(self):
        if not self.fecha_pago:
            return None
        mes_siguiente = self.fecha_pago.month % 12 + 1
        anio_siguiente = self.fecha_pago.year + (1 if self.fecha_pago.month == 12 else 0)
        try:
            return self.fecha_pago.replace(year=anio_siguiente, month=mes_siguiente)
        except ValueError:
            # día 31 en un mes que no lo tiene: cae al último día de ese mes
            siguiente_mes_inicio = datetime.date(anio_siguiente, mes_siguiente, 1)
            ultimo_dia = (siguiente_mes_inicio.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
            return ultimo_dia

    @property
    def fecha_limite(self):
        vencimiento = self.fecha_vencimiento
        if not vencimiento:
            return None
        return vencimiento + datetime.timedelta(days=self.dias_gracia)

    @property
    def esta_vencida(self):
        limite = self.fecha_limite
        if not limite:
            return False
        return datetime.date.today() > limite

    @property
    def dias_para_vencer(self):
        vencimiento = self.fecha_vencimiento
        if not vencimiento:
            return None
        return (vencimiento - datetime.date.today()).days


class Categoria(models.Model):
    LIMITE_EDAD_CHOICES = [
        ('U5', 'U5'),
        ('U7', 'U7'),
        ('U9', 'U9'),
        ('U11', 'U11'),
        ('U13', 'U13'),
        ('U15', 'U15'),
        ('U17', 'U17'),
    ]

    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name='categorias')
    nombre = models.CharField('Categoría', max_length=120)
    cupo_equipos = models.PositiveIntegerField('Cupo de equipos', default=8)
    descripcion = models.TextField('Descripción', blank=True)

    limite_edad = models.CharField(
        'Límite de edad', max_length=4, choices=LIMITE_EDAD_CHOICES, blank=True,
        help_text='U9 entra un jugador de 9 años o menos, no uno de 10.',
    )
    reglas = models.TextField('Reglas de la competencia', blank=True)
    inscripcion_abierta = models.BooleanField('Inscripción abierta', default=True)
    activa = models.BooleanField('Categoría activa', default=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        unique_together = ('liga', 'nombre')

    def __str__(self):
        return f'{self.liga.nombre} - {self.nombre}'

    def motivo_para_no_recibir_equipos(self):
        """Por que la categoria no admite un equipo mas, o '' si si admite.

        Devuelve el texto del motivo para que quien valide no tenga que volver
        a razonar la regla ni redactar el mensaje.
        """
        if not self.inscripcion_abierta:
            return f'La categoría {self.nombre} tiene la inscripción cerrada.'
        inscritos = self.equipos.count()
        if inscritos >= self.cupo_equipos:
            return (
                f'La categoría {self.nombre} ya llegó a su cupo de {self.cupo_equipos} '
                f'equipo(s).'
            )
        return ''

    @property
    def admite_equipos(self):
        return not self.motivo_para_no_recibir_equipos()

    @property
    def edad_maxima(self):
        """De 'U9' saca el 9. None mientras la categoria no tenga limite."""
        return int(self.limite_edad[1:]) if self.limite_edad else None

    @property
    def anio_temporada(self):
        """La edad se cuenta por año de nacimiento contra el año en que arranca la liga."""
        if self.liga.fecha_inicio:
            return self.liga.fecha_inicio.year
        return datetime.date.today().year

    @property
    def nacimiento_minimo(self):
        """La fecha de nacimiento mas antigua que entra en la categoria.

        Como la edad se cuenta por año, es el 1 de enero del año en que nacio
        el jugador de mayor edad permitido. Sirve para poner el tope del
        selector de fecha y que ni siquiera se pueda elegir algo invalido.
        """
        if not self.limite_edad:
            return None
        return datetime.date(self.anio_temporada - self.edad_maxima, 1, 1)

    def edad_en_temporada(self, fecha_nacimiento):
        """Los años que cumple el jugador durante la temporada."""
        return self.anio_temporada - fecha_nacimiento.year

    def acepta(self, fecha_nacimiento):
        """Si el jugador entra en la categoria. Sin limite cargado no se restringe nada."""
        if not self.limite_edad or not fecha_nacimiento:
            return True
        return self.edad_en_temporada(fecha_nacimiento) <= self.edad_maxima
