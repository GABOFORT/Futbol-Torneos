import datetime

from django.conf import settings
from django.db import models


class Liga(models.Model):
    nombre = models.CharField('Nombre de la liga', max_length=150)
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
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name='categorias')
    nombre = models.CharField('Categoría', max_length=120)
    cupo_equipos = models.PositiveIntegerField('Cupo de equipos', default=8)
    descripcion = models.TextField('Descripción', blank=True)

    fecha_inicio = models.DateField('Fecha de inicio', null=True, blank=True)
    fecha_final = models.DateField('Fecha de finalización', null=True, blank=True)
    reglas = models.TextField('Reglas de la competencia', blank=True)
    inscripcion_abierta = models.BooleanField('Inscripción abierta', default=True)
    activa = models.BooleanField('Categoría activa', default=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        unique_together = ('liga', 'nombre')

    def __str__(self):
        return f'{self.liga.nombre} - {self.nombre}'
