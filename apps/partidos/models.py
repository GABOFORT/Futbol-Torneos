from django.db import models
from django.utils import timezone


class Partido(models.Model):
    ESTADO_PROGRAMADO = 'programado'
    ESTADO_REPROGRAMADO = 'reprogramado'
    ESTADO_FINALIZADO = 'finalizado'
    ESTADO_CANCELADO = 'cancelado'

    ESTADO_CHOICES = [
        (ESTADO_PROGRAMADO, 'Programado'),
        (ESTADO_REPROGRAMADO, 'Reprogramado'),
        (ESTADO_FINALIZADO, 'Finalizado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    # Los dos estados de un partido que todavia se va a jugar. Se usan juntos
    # para no tener que enumerarlos en cada consulta y olvidarse de uno.
    ESTADOS_POR_JUGARSE = (ESTADO_PROGRAMADO, ESTADO_REPROGRAMADO)

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
    jornada = models.PositiveIntegerField('Jornada', default=1)
    fecha = models.DateTimeField('Fecha y hora', null=True, blank=True)
    fecha_original = models.DateTimeField(
        'Fecha asignada al principio',
        null=True,
        blank=True,
        help_text='Se guarda la primera vez que se programa. Si despues cambia, el partido figura reprogramado.',
    )
    goles_local = models.PositiveIntegerField('Goles local', default=0)
    goles_visitante = models.PositiveIntegerField('Goles visitante', default=0)
    ganador_penales = models.ForeignKey(
        'equipos.Equipo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='penales_ganados',
        verbose_name='Ganador de los penales',
        help_text='Solo cuando el partido termina empatado. Suma un punto extra.',
    )
    estado = models.CharField('Estado', max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PROGRAMADO)

    class Meta:
        verbose_name = 'Partido'
        verbose_name_plural = 'Partidos'
        ordering = ['jornada', 'fecha', 'id']

    def __str__(self):
        fecha = self.fecha.strftime('%Y-%m-%d') if self.fecha else 'sin fecha'
        return f'J{self.jornada}: {self.equipo_local} vs {self.equipo_visitante} - {fecha}'

    @property
    def jugado(self):
        return self.estado == self.ESTADO_FINALIZADO

    @property
    def goles_asignados_local(self):
        return self._asignados(self.equipo_local_id, self.equipo_visitante_id)

    @property
    def goles_asignados_visitante(self):
        return self._asignados(self.equipo_visitante_id, self.equipo_local_id)

    def _asignados(self, equipo_id, rival_id):
        """Goles que suman al marcador de un equipo.

        Son los que anotaron sus jugadores mas los que el rival se hizo en
        contra: un gol en contra sube el marcador del otro equipo.
        """
        total = 0
        for actuacion in self.actuaciones.all():
            if actuacion.jugador.equipo_id == equipo_id:
                total += actuacion.goles
            elif actuacion.jugador.equipo_id == rival_id:
                total += actuacion.goles_en_contra
        return total

    @property
    def empatado(self):
        return self.jugado and self.goles_local == self.goles_visitante

    @property
    def reprogramado(self):
        """Si el partido figura como reprogramado."""
        return self.estado == self.ESTADO_REPROGRAMADO

    @property
    def fue_movido(self):
        """Si la fecha cambio respecto de la primera que se le asigno.

        Va aparte de `estado` a proposito: cuando se carga el resultado el estado
        pasa a finalizado, y sin esto se perderia el rastro de que el partido se
        habia movido y de para cuando era.
        """
        return (
            self.fecha is not None
            and self.fecha_original is not None
            and self.fecha != self.fecha_original
        )

    @property
    def ya_empezo(self):
        """Si llego la fecha y hora del partido.

        Es lo que decide que accion se ofrece: antes solo se toca el cuando,
        desde la hora en adelante solo el marcador.
        """
        return self.fecha is not None and self.fecha <= timezone.now()


class Actuacion(models.Model):
    """Lo que hizo un jugador en un partido: goles y asistencias.

    Una fila por jugador y no una por gol: si alguien anota dos, se guarda el
    numero 2. Alcanza para las tablas de goleo y asistencias, y hace la carga
    mucho mas corta. Lo que no permite es saber que asistencia fue de que gol ni
    en que minuto; si algun dia hace falta la cronica del partido, hay que
    cambiar este modelo.
    """

    partido = models.ForeignKey(
        Partido,
        on_delete=models.CASCADE,
        related_name='actuaciones',
    )
    jugador = models.ForeignKey(
        'jugadores.Jugador',
        on_delete=models.CASCADE,
        related_name='actuaciones',
    )
    goles = models.PositiveIntegerField('Goles', default=0)
    goles_en_contra = models.PositiveIntegerField(
        'Goles en contra',
        default=0,
        help_text='Suman al marcador del rival y no cuentan para la tabla de goleo.',
    )
    asistencias = models.PositiveIntegerField('Asistencias', default=0)

    class Meta:
        verbose_name = 'Actuación'
        verbose_name_plural = 'Actuaciones'
        ordering = ['-goles', '-asistencias']
        constraints = [
            # Un jugador aparece una sola vez por partido: si anoto dos veces
            # es la misma fila con goles=2, no dos filas.
            models.UniqueConstraint(
                fields=['partido', 'jugador'],
                name='una_actuacion_por_jugador_y_partido',
                violation_error_message='Ese jugador ya está cargado en este partido.',
            ),
        ]

    def __str__(self):
        return f'{self.jugador}: {self.goles} gol(es), {self.asistencias} asistencia(s)'
