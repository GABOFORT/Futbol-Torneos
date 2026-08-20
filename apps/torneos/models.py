import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.usuarios.imagenes import TOPE_PANTALLA_PX, achicar_imagen
from apps.usuarios.monograma import iniciales_de


class Liga(models.Model):
    nombre = models.CharField('Nombre de la liga', max_length=150)
    logo = models.ImageField(
        'Logo de la liga', upload_to='logos-ligas/', blank=True, null=True,
        help_text='Opcional. Si lo dejas vacío se muestran las iniciales de la liga.',
    )
    portada = models.ImageField(
        'Portada de la liga', upload_to='portadas-ligas/', blank=True, null=True,
        help_text='Opcional. Se muestra de fondo en las pantallas de esta liga horizontal.',
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

    cerrada = models.BooleanField('Liga concluida', default=False)
    fecha_cierre = models.DateTimeField('Concluida el', null=True, blank=True)

    class Meta:
        verbose_name = 'Liga'
        verbose_name_plural = 'Ligas'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        achicar_imagen(self.logo)
        achicar_imagen(self.portada, tope=TOPE_PANTALLA_PX)
        super().save(*args, **kwargs)

    @property
    def portada_url(self):
        """La portada de la liga, o '' si no cargó ninguna.

        Se resuelve aca y no en la plantilla para que preguntar por la imagen no
        reviente cuando el campo esta vacio: `self.portada.url` sin archivo lanza
        ValueError, y eso tumbaria el base.html de todas las pantallas de la liga.
        """
        return self.portada.url if self.portada else ''

    @property
    def iniciales(self):
        """Reemplazo del logo cuando no hay: 'LIGA MX' -> 'LM'.

        Usa el mismo criterio que el escudo de los equipos, para que una liga y
        un club sin imagen no se abrevien con reglas distintas.
        """
        return iniciales_de(self.nombre)

    @property
    def fecha_vencimiento(self):
        if not self.fecha_pago:
            return None
        mes_siguiente = self.fecha_pago.month % 12 + 1
        anio_siguiente = self.fecha_pago.year + (1 if self.fecha_pago.month == 12 else 0)
        try:
            return self.fecha_pago.replace(year=anio_siguiente, month=mes_siguiente)
        except ValueError:
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

    DIAS_EN_VITRINA = 30

    @property
    def dias_en_vitrina(self):
        """Dias que le quedan de exhibicion. 0 cuando ya se puede eliminar.

        None si la liga no esta cerrada, que es lo mismo que decir que no aplica.
        """
        if not self.cerrada or not self.fecha_cierre:
            return None
        transcurridos = (timezone.now() - self.fecha_cierre).days
        return max(0, self.DIAS_EN_VITRINA - transcurridos)

    @property
    def lista_para_eliminar(self):
        """Si ya cumplio su mes en vitrina y el superadmin puede borrarla."""
        return self.dias_en_vitrina == 0


class Sede(models.Model):
    """Una cancha donde se juegan partidos.

    Va en tabla aparte y no como texto dentro de Partido porque la misma cancha
    se repite en muchos partidos: asi las coordenadas se guardan una vez, y
    corregir un pin mal puesto arregla todos los partidos que juegan ahi.

    Pertenece a una liga, igual que las categorias y los equipos: cada admin ve
    unicamente las canchas de las ligas que administra.
    """

    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name='sedes')
    nombre = models.CharField('Nombre de la cancha', max_length=150)
    direccion = models.CharField('Dirección', max_length=255, blank=True)
    latitud = models.DecimalField('Latitud', max_digits=9, decimal_places=6)
    longitud = models.DecimalField('Longitud', max_digits=9, decimal_places=6)

    class Meta:
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'
        ordering = ['nombre']
        unique_together = ('liga', 'nombre')

    def __str__(self):
        return self.nombre

    @property
    def punto(self):
        """Las coordenadas como las piden Google Maps y las apps de navegacion."""
        return f'{self.latitud},{self.longitud}'

    @property
    def url_mapa(self):
        """Mapa incrustable, el mismo truco que usa la pagina '¿Dónde estamos?'.

        output=embed no necesita llave de API ni cuenta de Google.
        """
        return f'https://maps.google.com/maps?q={self.punto}&z=16&output=embed'

    @property
    def url_como_llegar(self):
        """Abre la navegacion en el celular o Google Maps en la computadora."""
        return f'https://www.google.com/maps/search/?api=1&query={self.punto}'


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

    MAXIMO_GRUPOS = 26
    SIN_GRUPOS = 0

    grupos = models.PositiveSmallIntegerField(
        'Grupos',
        default=SIN_GRUPOS,
        help_text='En cuántos grupos se reparten los equipos. Cero es sin grupos.',
    )

    limite_edad = models.CharField(
        'Límite de edad', max_length=4, choices=LIMITE_EDAD_CHOICES, blank=True,
        help_text='U9 entra un jugador de 9 años o menos, no uno de 10.',
    )
    reglas = models.TextField('Reglas de la competencia', blank=True)
    inscripcion_abierta = models.BooleanField('Inscripción abierta', default=True)
    activa = models.BooleanField('Categoría activa', default=True)

    VUELTA_UNICA = 1
    VUELTA_IDA_Y_VUELTA = 2

    VUELTAS_CHOICES = [
        (VUELTA_UNICA, 'Una vuelta · todos se enfrentan una vez'),
        (VUELTA_IDA_Y_VUELTA, 'Ida y vuelta · todos se enfrentan dos veces'),
    ]

    vueltas = models.PositiveSmallIntegerField(
        'Vueltas del torneo regular',
        choices=VUELTAS_CHOICES,
        default=VUELTA_UNICA,
        help_text='Con ida y vuelta se duplican las jornadas y se invierte la localía en la segunda.',
    )

    empate_define_penales = models.BooleanField(
        'El empate se define en penales',
        default=True,
        help_text='Si lo desmarcas, un empate en jornada vale 1 punto para cada uno y no habra ganador.',
    )

    libre = models.BooleanField(
        'Categoría libre',
        default=False,
        help_text='Sin restricción: entra cualquier jugador, de cualquier edad, peso y sexo.',
    )

    EDAD_MINIMA_CHOICES = [(edad, f'{edad} años') for edad in range(30, 81)]

    edad_minima = models.PositiveSmallIntegerField(
        'Categoría con edad mínima',
        choices=EDAD_MINIMA_CHOICES,
        null=True,
        blank=True,
        help_text='Vacío es sin edad mínima.',
    )

    PESO_MINIMO_CHOICES = [(kilos, f'{kilos} kg') for kilos in range(50, 101)]

    peso_minimo = models.PositiveSmallIntegerField(
        'Categoría con peso mínimo',
        choices=PESO_MINIMO_CHOICES,
        null=True,
        blank=True,
        help_text='Requisito para poder inscribirse. Se verifica en báscula: el sistema '
                  'no registra el peso de cada jugador.',
    )

    MINIMO_EQUIPOS_MINI_LIGUILLA = 12
    EQUIPOS_MINI_LIGUILLA = 4

    mini_liguilla = models.BooleanField(
        'Mini-liguilla de consolación',
        default=False,
        help_text='Los puestos 9 a 12 juegan su propio cuadro. Necesita 12 equipos o más.',
    )

    cerrada = models.BooleanField('Categoría concluida', default=False)
    fecha_cierre = models.DateTimeField('Concluida el', null=True, blank=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        unique_together = ('liga', 'nombre')

    def __str__(self):
        return f'{self.liga.nombre} - {self.nombre}'

    @property
    def juega_por_grupos(self):
        return self.grupos > self.SIN_GRUPOS

    @property
    def letras_de_grupo(self):
        from apps.equipos.models import Equipo

        return list(Equipo.LETRAS_GRUPO[:self.grupos])

    @property
    def reparto(self):
        conteo = {letra: 0 for letra in self.letras_de_grupo}
        for equipo in self.equipos.all():
            if equipo.grupo in conteo:
                conteo[equipo.grupo] += 1
        return conteo

    @property
    def equipos_sin_grupo(self):
        return self.equipos.exclude(grupo__in=self.letras_de_grupo).count()

    def motivo_para_no_recibir_equipos(self):
        """Por que la categoria no admite un equipo mas, o '' si si admite.

        Devuelve el texto del motivo para que quien valide no tenga que volver
        a razonar la regla ni redactar el mensaje.
        """
        from apps.partidos import altas

        if not self.inscripcion_abierta:
            return f'La categoría {self.nombre} tiene la inscripción cerrada.'
        inscritos = self.equipos.count()
        if inscritos >= self.cupo_equipos:
            return (
                f'La categoría {self.nombre} ya llegó a su cupo de {self.cupo_equipos} '
                f'equipo(s).'
            )
        return altas.motivo_para_no_agregar(self)

    @property
    def admite_equipos(self):
        return not self.motivo_para_no_recibir_equipos()

    ANIOS_EXTRA_FEMENINO = 1

    @property
    def edad_maxima(self):
        """De 'U9' saca el 9. None mientras la categoria no tenga limite.

        Es el limite base, el de los varones. Para el de una jugadora hay que
        pedir `edad_maxima_para(sexo)`.
        """
        return int(self.limite_edad[1:]) if self.limite_edad else None

    @property
    def edad_maxima_femenino(self):
        """El limite de las mujeres: el de la categoria mas el año de tolerancia."""
        if self.edad_maxima is None:
            return None
        return self.edad_maxima + self.ANIOS_EXTRA_FEMENINO

    def edad_maxima_para(self, sexo):
        """Los años que puede tener quien se inscribe, segun su sexo.

        El sexo llega como el valor guardado en Jugador.sexo. Cualquier otra
        cosa se trata como varon, que es el limite estricto: ante la duda no se
        regala un año de gracia.
        """
        from apps.jugadores.models import Jugador

        if self.edad_maxima is None:
            return None
        if sexo == Jugador.SEXO_FEMENINO:
            return self.edad_maxima_femenino
        return self.edad_maxima

    @property
    def anio_temporada(self):
        """La edad se cuenta por año de nacimiento contra el año en que arranca la liga."""
        if self.liga.fecha_inicio:
            return self.liga.fecha_inicio.year
        return datetime.date.today().year

    def nacimiento_minimo_para(self, sexo):
        """La fecha de nacimiento mas antigua que entra en la categoria.

        Como la edad se cuenta por año, es el 1 de enero del año en que nacio
        el jugador de mayor edad permitido. Sirve para poner el tope del
        selector de fecha y que ni siquiera se pueda elegir algo invalido.

        Depende del sexo porque el limite depende del sexo: para una jugadora la
        fecha se corre un año hacia atras.
        """
        maxima = self.edad_maxima_para(sexo)
        if maxima is None:
            return None
        return datetime.date(self.anio_temporada - maxima, 1, 1)

    @property
    def nacimiento_maximo(self):
        """La fecha de nacimiento mas reciente que alcanza la edad minima.

        Espejo de `nacimiento_minimo_para()`: como la edad se cuenta por año, es
        el 31 de diciembre del año en que nacio el jugador mas joven admitido.
        None cuando la categoria no pide edad minima.
        """
        if self.edad_minima is None:
            return None
        return datetime.date(self.anio_temporada - self.edad_minima, 12, 31)

    def edad_en_temporada(self, fecha_nacimiento):
        """Los años que cumple el jugador durante la temporada."""
        return self.anio_temporada - fecha_nacimiento.year

    def acepta(self, fecha_nacimiento, sexo=None):
        """Si la edad del jugador entra en la categoria."""
        if self.libre or not fecha_nacimiento:
            return True
        edad = self.edad_en_temporada(fecha_nacimiento)
        if self.limite_edad and edad > self.edad_maxima_para(sexo):
            return False
        if self.edad_minima and edad < self.edad_minima:
            return False
        return True

    def rechazo_para(self, fecha_nacimiento=None, sexo=None):
        """Por que este jugador no entra como `(campo, mensaje)`, o None si entra.

        Solo mira la edad. El peso minimo de la categoria es un requisito que se
        verifica en bascula, fuera del sistema: no se registra por jugador y por
        lo tanto no se puede —ni se debe— validar aca.
        """
        if self.libre:
            return None

        if fecha_nacimiento:
            edad = self.edad_en_temporada(fecha_nacimiento)
            if self.limite_edad and edad > self.edad_maxima_para(sexo):
                return ('fecha_nacimiento', (
                    f'La categoría {self.nombre} es {self.limite_edad}: admite hasta '
                    f'{self.edad_maxima} años en varones y {self.edad_maxima_femenino} '
                    f'en mujeres. Este jugador cumple {edad} en la temporada '
                    f'{self.anio_temporada}.'
                ))
            if self.edad_minima and edad < self.edad_minima:
                return ('fecha_nacimiento', (
                    f'La categoría {self.nombre} admite de {self.edad_minima} años para '
                    f'arriba. Este jugador cumple {edad} en la temporada '
                    f'{self.anio_temporada}.'
                ))

        return None

    @property
    def restricciones_texto(self):
        """La puerta de entrada de la categoria resumida en una linea."""
        if self.libre:
            return 'Libre · sin restricción de edad ni peso'
        partes = []
        if self.limite_edad:
            partes.append(self.limites_texto)
        if self.edad_minima:
            partes.append(f'desde {self.edad_minima} años')
        if self.peso_minimo:
            partes.append(f'desde {self.peso_minimo} kg')
        return ' · '.join(partes)

    @property
    def limites_texto(self):
        """Los dos limites en una linea, para mostrarlos donde se nombra la categoria.

        'hasta 17 años · 18 en mujeres'. Se arma aca y no en cada plantilla para
        que todas digan lo mismo, y sobre todo para que ninguna siga anunciando
        un solo limite cuando en realidad hay dos.
        """
        if self.edad_maxima is None:
            return ''
        return f'hasta {self.edad_maxima} años · {self.edad_maxima_femenino} en mujeres'

    @property
    def admite_mini_liguilla(self):
        """Si hay equipos suficientes para armar el cuadro de consolacion."""
        return self.equipos.count() >= self.MINIMO_EQUIPOS_MINI_LIGUILLA

    @property
    def juega_mini_liguilla(self):
        """Si esta categoria va a tener mini-liguilla: la pidieron Y alcanza."""
        return self.mini_liguilla and self.admite_mini_liguilla

    @property
    def motivo_sin_mini_liguilla(self):
        """Por que no habra mini-liguilla aunque este pedida, o '' si si habra."""
        if not self.mini_liguilla:
            return ''
        faltan = self.MINIMO_EQUIPOS_MINI_LIGUILLA - self.equipos.count()
        if faltan > 0:
            return (
                f'La mini-liguilla necesita {self.MINIMO_EQUIPOS_MINI_LIGUILLA} equipos '
                f'y en esta categoría hay {self.equipos.count()}: faltan {faltan}.'
            )
        return ''

    @property
    def ajustes_congelados(self):
        """Si ya no se puede cambiar como se juega esta categoria."""
        return self.partidos.exists()

    def clean(self):
        """Las combinaciones que no pueden existir.

        Se juntan todos los errores y se lanzan de una: corregir uno y descubrir
        el siguiente al volver a guardar es peor que verlos juntos.
        """
        super().clean()

        errores = {}
        errores.update(self._error_de_cupo())
        errores.update(self._error_de_restricciones())
        if errores:
            raise ValidationError(errores)

    def _error_de_cupo(self):
        """El cupo tiene que dar para los puestos 9 a 12 si hay mini-liguilla."""
        if not self.mini_liguilla:
            return {}
        if self.cupo_equipos is None or self.cupo_equipos >= self.MINIMO_EQUIPOS_MINI_LIGUILLA:
            return {}
        return {'cupo_equipos': (
            f'La mini-liguilla juega los puestos 9 a 12, así que necesita '
            f'{self.MINIMO_EQUIPOS_MINI_LIGUILLA} equipos y el cupo es '
            f'{self.cupo_equipos}. Sube el cupo a {self.MINIMO_EQUIPOS_MINI_LIGUILLA} '
            f'o más, o desmarca la mini-liguilla.'
        )}

    def _error_de_restricciones(self):
        """Quien puede inscribirse. Hay una sola puerta de entrada por categoria.

        Manda en cascada: `libre` gana sobre todo, y un limite U gana sobre los
        minimos. El que gana limpia a los demas en vez de rechazar, porque la
        pantalla ya los esconde: un valor que sobrevive ahi es residuo de una
        edicion anterior, no algo que el usuario acabe de pedir.
        """
        if self.libre:
            self.limite_edad = ''
            self.edad_minima = None
            self.peso_minimo = None
            return {}

        if self.limite_edad:
            self.edad_minima = None
            self.peso_minimo = None
            return {}

        if not (self.edad_minima or self.peso_minimo):
            return {'libre': (
                'Elegí una opción: un límite de edad (U5 a U17), una edad mínima, '
                'un peso mínimo, o palomeá "Categoría libre" si puede entrar cualquiera.'
            )}

        return {}


class TorneoQuerySet(models.QuerySet):
    def terminados(self):
        """Los que ya jugaron la final de TODAS sus categorias.

        Con una sola categoria —la eliminacion directa— es lo de siempre. Con
        varias importa: un torneo al que le falta jugar media parrilla de edades
        sigue en curso y sigue ocupando cuota.
        """
        from apps.partidos.models import Partido

        return self.annotate(
            _cuantas_categorias=models.Count('liga__categorias', distinct=True),
            _cuantas_finales=models.Count(
                'liga__categorias__partidos',
                filter=models.Q(
                    liga__categorias__partidos__fase=Partido.FASE_FINAL,
                    liga__categorias__partidos__estado=Partido.ESTADO_FINALIZADO),
                distinct=True),
        ).filter(
            _cuantas_categorias__gt=0,
            _cuantas_finales__gte=models.F('_cuantas_categorias'),
        )

    def en_curso(self):
        """Los que todavia no terminan. Son los que ocupan cuota.

        Se resuelve en la consulta y no recorriendo torneo por torneo: la cuota
        se comprueba en cada alta y con `terminado` serian tantas consultas como
        torneos tenga el admin.
        """
        return self.exclude(pk__in=self.terminados().values('pk'))


class Torneo(models.Model):
    """Un torneo: eliminación directa de un día, o por categorías y grupos.

    Se apoya en una Liga. No es un rodeo: así los equipos, jugadores, partidos y
    actuaciones son los mismos de siempre, y el entrenador carga su plantilla
    con las pantallas que ya conoce. La Liga aporta el nombre, el logo, la
    portada y la descripción; aquí solo vive lo propio del torneo.

    En `directa` la Liga lleva una sola Categoría y el cuadro sale de un sorteo.
    En `grupos` lleva las que el administrador cree —una por edad o división—,
    cada una con sus propios grupos, su tabla y su liguilla, sin cruzarse entre
    ellas. Las categorías de torneo no validan edad ni peso: entra quien el
    administrador inscriba.

    Las ligas con torneo quedan fuera del apartado de ligas: los cuatro sitios
    que las listan las descartan.
    """

    EQUIPOS_OCHO = 8
    EQUIPOS_DIECISEIS = 16

    EQUIPOS_CHOICES = [
        (EQUIPOS_OCHO, '8 equipos · cuartos, semifinal y final'),
        (EQUIPOS_DIECISEIS, '16 equipos · octavos, cuartos, semifinal y final'),
    ]

    FORMATO_DIRECTA = 'directa'
    FORMATO_GRUPOS = 'grupos'

    FORMATO_CHOICES = [
        (FORMATO_DIRECTA, 'Eliminación directa'),
        (FORMATO_GRUPOS, 'Por categorías y grupos'),
    ]

    MODALIDADES = [
        ('8', EQUIPOS_OCHO, FORMATO_DIRECTA,
         '8 equipos · un día, cuartos, semifinal y final'),
        ('16', EQUIPOS_DIECISEIS, FORMATO_DIRECTA,
         '16 equipos · un día, octavos, cuartos, semifinal y final'),
        ('grupos', None, FORMATO_GRUPOS,
         'Por categorías y grupos · tú armas la liguilla'),
    ]

    MODALIDAD_CHOICES = [(clave, etiqueta) for clave, _, _, etiqueta in MODALIDADES]

    liga = models.OneToOneField(
        Liga, on_delete=models.CASCADE, related_name='torneo')
    fecha = models.DateField(
        'Día del torneo',
        help_text='En eliminación directa se juega entero ese día. Por grupos es '
                  'la fecha de arranque: cada partido lleva la suya.',
    )
    equipos = models.PositiveSmallIntegerField(
        'Equipos que participan',
        choices=EQUIPOS_CHOICES,
        default=EQUIPOS_OCHO,
    )
    formato = models.CharField(
        'Formato',
        max_length=20,
        choices=FORMATO_CHOICES,
        default=FORMATO_DIRECTA,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='torneos_creados',
        verbose_name='Creado por',
    )

    objects = TorneoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Torneo'
        verbose_name_plural = 'Torneos'
        ordering = ['-fecha']

    def __str__(self):
        return self.liga.nombre

    @property
    def nombre(self):
        return self.liga.nombre

    @property
    def es_por_grupos(self):
        return self.formato == self.FORMATO_GRUPOS

    @property
    def categorias(self):
        return self.liga.categorias.order_by('nombre')

    @property
    def categoria(self):
        return self.liga.categorias.first()

    @property
    def inscritos(self):
        from apps.equipos.models import Equipo

        return Equipo.objects.filter(categoria__liga_id=self.liga_id).count()

    @property
    def completo(self):
        if self.es_por_grupos:
            return False
        return self.inscritos == self.equipos

    @property
    def faltan(self):
        if self.es_por_grupos:
            return 0
        return max(0, self.equipos - self.inscritos)

    @property
    def modalidad(self):
        for clave, equipos, formato, _ in self.MODALIDADES:
            if formato != self.formato:
                continue
            if equipos is None or equipos == self.equipos:
                return clave
        return self.MODALIDADES[0][0]

    @classmethod
    def desde_modalidad(cls, clave):
        for actual, equipos, formato, _ in cls.MODALIDADES:
            if actual == clave:
                return equipos, formato
        return cls.EQUIPOS_OCHO, cls.FORMATO_DIRECTA

    @property
    def formato_texto(self):
        if self.es_por_grupos:
            return 'por categorías y grupos'
        return 'eliminación directa'

    @property
    def fecha_inicio(self):
        return self.liga.fecha_inicio or self.fecha

    @property
    def fecha_fin(self):
        return self.liga.fecha_final or self.fecha

    @property
    def de_un_solo_dia(self):
        return self.fecha_inicio == self.fecha_fin

    @property
    def fechas_texto(self):
        if self.de_un_solo_dia:
            return f'{self.fecha_inicio:%d/%m/%Y}'
        return f'del {self.fecha_inicio:%d/%m/%Y} al {self.fecha_fin:%d/%m/%Y}'

    @property
    def resumen_texto(self):
        if not self.es_por_grupos:
            return f'{self.equipos} equipos · eliminación directa'
        cuantas = self.categorias.count()
        if not cuantas:
            return 'Por categorías y grupos · sin categorías todavía'
        return (f'{cuantas} categoría(s) · {self.inscritos} equipo(s) · '
                f'por categorías y grupos')

    @property
    def sorteado(self):
        from apps.partidos.models import Partido

        return Partido.objects.filter(categoria__liga_id=self.liga_id).exists()

    @property
    def _finales_jugadas(self):
        from apps.partidos.models import Partido

        return (Partido.objects
                .filter(categoria__liga_id=self.liga_id,
                        fase=Partido.FASE_FINAL,
                        estado=Partido.ESTADO_FINALIZADO)
                .select_related('categoria', 'equipo_local', 'equipo_visitante',
                                'ganador_penales')
                .order_by('categoria__nombre'))

    @property
    def _final_jugada(self):
        return self._finales_jugadas.first()

    @property
    def campeon(self):
        final = self._final_jugada
        return final.ganador if final else None

    @property
    def campeones(self):
        return [{'categoria': final.categoria, 'equipo': final.ganador}
                for final in self._finales_jugadas if final.ganador]

    @property
    def terminado(self):
        """Terminado es que TODAS sus categorías jugaron su final.

        Con una sola categoría —la eliminación directa— coincide con lo de
        siempre. Importa porque de esto depende la cuota de `limite_torneos`:
        un torneo con la mitad de las edades sin jugar sigue en curso.
        """
        categorias = self.categorias.count()
        if not categorias:
            return False
        return self._finales_jugadas.count() >= categorias

    DIAS_EN_VITRINA = 30

    @property
    def fecha_cierre(self):
        """Cuando termino, que es cuando se jugo su final.

        Se deduce en vez de guardarse: el torneo no tiene estado propio, y un
        campo aparte podria quedar desincronizado si se corrige el resultado de
        la final.
        """
        final = self._final_jugada
        return final.fecha if final and final.ganador else None

    @property
    def dias_en_vitrina(self):
        """Dias que le quedan de exhibicion. 0 cuando ya se puede eliminar."""
        cierre = self.fecha_cierre
        if cierre is None:
            return None
        transcurridos = (timezone.now() - cierre).days
        return max(0, self.DIAS_EN_VITRINA - transcurridos)

    @property
    def lista_para_eliminar(self):
        return self.dias_en_vitrina == 0


class Palmares(models.Model):
    """Lo que quedo de una categoria terminada: el podio y los premiados.

    Se llena una sola vez, al cargar el resultado de la final. La logica del
    calculo esta en apps/torneos/palmares.py, junto con el razonamiento de por
    que se congela en vez de calcularse al vuelo.

    Casi todo va como texto y no como clave foranea a proposito: los nombres del
    campeon y de los premiados tienen que seguir leyendose aunque los equipos y
    los jugadores ya no existan.

    **Al eliminar la liga o el torneo, esta fila se va con ellos.** Borrar es
    borrar: si el Administrador General decide que ese torneo no tiene que
    quedar, tampoco debe seguir apareciendo en la vitrina. Se hace explicito en
    `liga_delete` y `torneo_delete`, no con un CASCADE: la relacion es
    SET_NULL para que borrar una sola categoria no se lleve por delante el
    palmares de toda la temporada.
    """

    liga_nombre = models.CharField('Liga', max_length=150)
    categoria_nombre = models.CharField('Categoría', max_length=120)

    es_torneo = models.BooleanField('Torneo relámpago', default=False)

    categoria = models.ForeignKey(
        'torneos.Categoria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='palmares',
    )

    fecha_cierre = models.DateTimeField('Concluida el', auto_now_add=True)

    campeon = models.CharField('Campeón', max_length=140, blank=True)
    subcampeon = models.CharField('Subcampeón', max_length=140, blank=True)
    tercero = models.CharField('Tercer lugar', max_length=140, blank=True)

    goleadores = models.CharField('Bota de oro', max_length=400, blank=True)
    goles_del_goleador = models.PositiveIntegerField('Goles', default=0)

    asistidores = models.CharField('Trofeo de asistencias', max_length=400, blank=True)
    asistencias_del_asistidor = models.PositiveIntegerField('Asistencias', default=0)

    vallas = models.CharField('Guante de oro', max_length=400, blank=True)
    goles_recibidos = models.PositiveIntegerField('Goles recibidos', default=0)

    tabla_final = models.JSONField('Tabla final', default=list, blank=True)

    class Meta:
        verbose_name = 'Palmarés'
        verbose_name_plural = 'Palmarés'
        ordering = ['-fecha_cierre']

    def __str__(self):
        return f'{self.liga_nombre} - {self.categoria_nombre}: {self.campeon or "sin campeón"}'

    @property
    def lista_goleadores(self):
        return [n for n in self.goleadores.split(' / ') if n]

    @property
    def lista_asistidores(self):
        return [n for n in self.asistidores.split(' / ') if n]

    @property
    def lista_vallas(self):
        return [n for n in self.vallas.split(' / ') if n]
