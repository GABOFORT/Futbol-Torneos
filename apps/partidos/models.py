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

    # Fase de la liguilla. Vacio es el torneo regular, el de todos contra todos.
    # Los partidos de liguilla no cuentan para la tabla de posiciones ni para
    # las porterias menos vencidas: esas tablas miden el torneo regular, y si
    # entraran los de liguilla se moverian solas despues de terminado.
    FASE_REGULAR = ''
    FASE_CUARTOS = 'cuartos'
    FASE_SEMIFINAL = 'semifinal'
    FASE_TERCERO = 'tercero'
    FASE_FINAL = 'final'

    FASE_CHOICES = [
        (FASE_REGULAR, 'Torneo regular'),
        (FASE_CUARTOS, 'Cuartos de final'),
        (FASE_SEMIFINAL, 'Semifinal'),
        (FASE_TERCERO, 'Tercer lugar'),
        (FASE_FINAL, 'Final'),
    ]

    # El orden en que se juegan, para saber que ronda alimenta a cual: el tercer
    # lugar y la final se juegan al final, y en ese orden se muestran.
    ORDEN_FASES = [FASE_CUARTOS, FASE_SEMIFINAL, FASE_TERCERO, FASE_FINAL]

    # Las rondas de eliminacion van a ida y vuelta; la final y el tercer lugar
    # se definen en un solo encuentro. Son los dos partidos que cierran el
    # torneo y se juegan como una definicion, no como una serie.
    FASES_PARTIDO_UNICO = (FASE_TERCERO, FASE_FINAL)

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
    fase = models.CharField(
        'Fase', max_length=20, choices=FASE_CHOICES, default=FASE_REGULAR, blank=True,
        help_text='Vacío es el torneo regular. Las demás son las rondas de la liguilla.',
    )
    orden = models.PositiveIntegerField(
        'Posición en la ronda',
        default=0,
        help_text='Qué llave del cuadro ocupa. Define qué cruce alimenta a cuál en la ronda siguiente.',
    )
    # La liguilla se juega a doble partido: cada llave son dos encuentros y pasa
    # el que suma mas goles entre los dos. `fase` + `orden` identifican la llave,
    # y este campo distingue cual de los dos partidos es.
    # El tercer lugar es la excepcion: va a partido unico y siempre es ida.
    vuelta = models.BooleanField(
        'Partido de vuelta',
        default=False,
        help_text='La llave se juega ida y vuelta. La vuelta la recibe el mejor ubicado en la tabla.',
    )
    # En que lugar de la tabla termino cada uno el torneo regular. Se guarda al
    # armar el cruce y viaja con el equipo a la ronda siguiente: es lo que
    # resuelve el empate, y en semifinales el local ya no es necesariamente el
    # mejor sembrado, asi que no alcanza con saber quien juega de local.
    siembra_local = models.PositiveIntegerField('Siembra del local', null=True, blank=True)
    siembra_visitante = models.PositiveIntegerField('Siembra del visitante', null=True, blank=True)
    fecha = models.DateTimeField('Fecha y hora', null=True, blank=True)
    fecha_original = models.DateTimeField(
        'Fecha asignada al principio',
        null=True,
        blank=True,
        help_text='Se guarda la primera vez que se programa. Si despues cambia, el partido figura reprogramado.',
    )
    sede = models.ForeignKey(
        'torneos.Sede',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='partidos',
        verbose_name='Cancha',
        help_text='Dónde se juega. Se marca en el mapa al programar el partido.',
    )
    sede_original = models.ForeignKey(
        'torneos.Sede',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='partidos_mudados',
        verbose_name='Cancha asignada al principio',
        help_text='Se guarda la primera vez que se asigna. Si después cambia, se avisa el cambio de cancha.',
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
    # El marcador de la tanda, para poder mostrarla como en television. Se
    # guarda aparte de los goles porque un penal convertido en la tanda no es un
    # gol del partido: el marcador sigue siendo el empate.
    penales_local = models.PositiveIntegerField('Penales del local', null=True, blank=True)
    penales_visitante = models.PositiveIntegerField('Penales del visitante', null=True, blank=True)
    # Se guarda QUE equipo falto y no un simple si/no: con el equipo se sabe
    # tambien quien gano, y la ficha puede nombrarlo en vez de mostrar un 3-0
    # pelado que se lee como un partido normal.
    no_se_presento = models.ForeignKey(
        'equipos.Equipo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ausencias',
        verbose_name='Equipo que no se presentó',
        help_text='Si un equipo no llega, el rival gana por default 3-0.',
    )
    estado = models.CharField('Estado', max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PROGRAMADO)

    class Meta:
        verbose_name = 'Partido'
        verbose_name_plural = 'Partidos'
        ordering = ['jornada', 'fecha', 'id']

    def __str__(self):
        fecha = self.fecha.strftime('%Y-%m-%d') if self.fecha else 'sin fecha'
        return f'J{self.jornada}: {self.equipo_local} vs {self.equipo_visitante} - {fecha}'

    # Marcador con el que se resuelve un partido que no se jugo por ausencia.
    # Es el mismo en todas las ligas: no se configura por liga porque nadie lo
    # cambia y un campo mas seria una decision para nada.
    MARCADOR_DEFAULT = 3

    @property
    def jugado(self):
        return self.estado == self.ESTADO_FINALIZADO

    @property
    def ganado_por_default(self):
        """Si se resolvio 3-0 porque uno de los dos no llego a la cancha."""
        return self.no_se_presento_id is not None

    @property
    def equipo_presentado(self):
        """El que si llego, y por lo tanto se llevo el partido. None si jugaron los dos."""
        if not self.ganado_por_default:
            return None
        if self.no_se_presento_id == self.equipo_local_id:
            return self.equipo_visitante
        return self.equipo_local

    @property
    def aviso_default(self):
        """El texto que explica el 3-0. Vive aca para que el calendario, la ficha
        y el perfil del equipo digan exactamente lo mismo."""
        if not self.ganado_por_default:
            return ''
        return f'Ganó por default · {self.no_se_presento.nombre} no se presentó'

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
    def es_liguilla(self):
        return self.fase != self.FASE_REGULAR

    @property
    def tramo(self):
        """'Ida' o 'Vuelta'. Vacio en el torneo regular y en el tercer lugar.

        Sin esto un partido de liguilla no se distingue de su gemelo: los dos
        cruzan a los mismos equipos y solo cambia quien juega de local, que no
        alcanza para saber cual se esta mirando.
        """
        if not self.es_liguilla or self.fase in self.FASES_PARTIDO_UNICO:
            return ''
        return 'Vuelta' if self.vuelta else 'Ida'

    @property
    def cierra_la_llave(self):
        """Si con este partido se termina de definir su llave.

        En una serie de ida y vuelta es la vuelta; en las fases a partido unico
        es el unico encuentro. Lo usa el formulario para saber cuando ofrecer
        los penales: solo se patean cuando ya no queda otro partido por jugarse.
        """
        if not self.es_liguilla:
            return False
        return self.vuelta or self.fase in self.FASES_PARTIDO_UNICO

    @property
    def etiqueta(self):
        """Como se nombra este partido en pantalla.

            Torneo regular  ->  'Jornada 5'
            Liguilla        ->  'Liguilla · Semifinal · Ida'
            Tercer lugar    ->  'Liguilla · Tercer lugar'   (va a partido unico)

        Se nombra la liguilla y no solo la ronda porque 'Semifinal' sola no dice
        que ya se esta en la eliminacion directa, y quien mira el calendario
        necesita ubicarse.

        Se resuelve en el modelo porque lo usan el calendario, la ficha, el
        perfil de equipo y el formulario de resultado, y tienen que decir lo mismo.
        """
        if not self.es_liguilla:
            return f'Jornada {self.jornada}'
        partes = ['Liguilla', self.get_fase_display()]
        if self.tramo:
            partes.append(self.tramo)
        return ' · '.join(partes)

    # Version abreviada de cada fase, para los lugares donde solo entran unos
    # pocos caracteres: la rachita de los ultimos cinco, las listas apretadas.
    FASE_CORTA = {
        FASE_CUARTOS: '4tos',
        FASE_SEMIFINAL: 'Semi',
        FASE_TERCERO: '3er',
        FASE_FINAL: 'Final',
    }

    @property
    def etiqueta_corta(self):
        """'J5' o '4tos I'. Para cuando no hay lugar para el nombre completo."""
        if not self.es_liguilla:
            return f'J{self.jornada}'
        corta = self.FASE_CORTA.get(self.fase, self.get_fase_display())
        return f'{corta} {self.tramo[:1]}' if self.tramo else corta

    @property
    def ganador(self):
        """Quien paso de ronda. None si todavia no se jugo o quedo sin resolver.

        Con el marcador empatado pasa el que termino mejor ubicado en la tabla
        del torneo regular: es la ventaja que se gano durante todo el ano y
        evita tener que jugar penales en cada cruce.

        Si igual se jugaron penales y se cargo el ganador, eso manda: si de
        verdad se patearon, el resultado de la cancha vale mas que la tabla.
        """
        if not self.jugado:
            return None
        if self.goles_local > self.goles_visitante:
            return self.equipo_local
        if self.goles_local < self.goles_visitante:
            return self.equipo_visitante

        # Empatados. En la final se patea: es el ultimo partido del torneo y no
        # se puede coronar campeon a nadie por una tabla que ya termino.
        if self.fase == self.FASE_FINAL:
            return self.ganador_penales

        # En las rondas anteriores decide la tabla, sin penales: es la ventaja
        # que el equipo se gano durante todo el torneo regular.
        if self.es_liguilla:
            if self.siembra_local is not None and self.siembra_visitante is not None:
                return (
                    self.equipo_local if self.siembra_local < self.siembra_visitante
                    else self.equipo_visitante
                )
            return None

        # Torneo regular: el empate no tiene ganador, solo el punto extra.
        return self.ganador_penales

    @property
    def motivo_del_pase(self):
        """Por que paso el que paso, para poder decirlo en pantalla.

        Devuelve '' cuando gano en la cancha, que es lo normal y no hace falta
        explicarlo.
        """
        if not self.jugado or self.goles_local != self.goles_visitante:
            return ''
        if self.fase == self.FASE_FINAL:
            return 'Se definió desde el punto penal'
        if self.es_liguilla and self.siembra_local is not None and self.siembra_visitante is not None:
            mejor = min(self.siembra_local, self.siembra_visitante)
            return f'Empataron: pasa el {mejor}º de la tabla'
        return ''

    @property
    def hubo_tanda(self):
        """Si este partido se definio en una tanda de penales con marcador cargado."""
        return self.penales_local is not None and self.penales_visitante is not None

    @property
    def tanda(self):
        """La tanda dibujada como en television: un circulito por penal.

        Solo se guarda cuantos convirtio cada uno, no la secuencia de aciertos y
        fallos. Con eso alcanza para el verde de los convertidos; el rojo se usa
        para emparejar al que quedo mas corto, que son penales que si o si erro
        de mas respecto del que gano.
        """
        if not self.hubo_tanda:
            return None
        tiros = max(self.penales_local, self.penales_visitante)
        return {
            'local': self._circulitos(self.penales_local, tiros),
            'visitante': self._circulitos(self.penales_visitante, tiros),
        }

    @staticmethod
    def _circulitos(convertidos, tiros):
        return [True] * convertidos + [False] * (tiros - convertidos)

    @property
    def perdedor(self):
        """El otro. Sirve para armar el partido por el tercer lugar."""
        ganador = self.ganador
        if ganador is None:
            return None
        return self.equipo_visitante if ganador.id == self.equipo_local_id else self.equipo_local

    @property
    def cambio_de_cancha(self):
        """Si el partido se mudo respecto de la cancha que tenia asignada.

        Va aparte de `estado` por el mismo motivo que `fue_movido`: al cargar el
        resultado el estado pasa a finalizado, y sin esto se perderia el rastro.
        Cambiar de cancha no marca el partido como reprogramado, pero igual hay
        que avisarlo: quien pensaba ir ya tenia anotado el lugar anterior.
        """
        return (
            self.sede_id is not None
            and self.sede_original_id is not None
            and self.sede_id != self.sede_original_id
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

    El minuto se dejo afuera a proposito: no se consulta y partir esta fila en
    una por evento no se paga con lo que aporta.

    `goles_de_penal` va DENTRO de `goles`, no aparte. Un penal convertido durante
    el juego es un gol como cualquier otro: suma al marcador, a la tabla de goleo
    y a la bota de oro. Se guarda solo para poder decirlo en la ficha.

    No confundirlo con `Partido.penales_local` / `penales_visitante`, que son la
    tanda que desempata: esos no son goles, no crean ninguna Actuacion y solo
    definen el punto extra en el regular o quien pasa en la liguilla.
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
    goles_de_penal = models.PositiveIntegerField(
        'De penal',
        default=0,
        help_text='Cuantos de sus goles fueron desde el punto penal. Es un subconjunto '
                  'de "Goles", no se suma aparte.',
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
