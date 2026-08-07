import datetime

from django.conf import settings
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
    # La identidad visual de la liga: se pinta detrás de todas sus pantallas, en
    # lugar del gris neutro del sistema. Va en Liga y no en Categoria porque la
    # marca es de la liga; una portada por categoria multiplicaria las imagenes
    # sin que nadie distinga de cual es cual.
    #
    # Nunca se muestra tal cual: siempre lleva un velo encima (ver .fondo-liga en
    # sistema.css). Sin el, una foto oscura o muy cargada deja el texto ilegible,
    # y el sistema entero esta armado sobre fondo claro con tarjetas blancas.
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

    # `cerrada` no es lo mismo que `activa`: activa=False la esconde del publico,
    # y una liga terminada es justo lo que hay que mostrar. Se cierra sola cuando
    # todas sus categorias terminaron su final.
    cerrada = models.BooleanField('Liga concluida', default=False)
    fecha_cierre = models.DateTimeField('Concluida el', null=True, blank=True)

    class Meta:
        verbose_name = 'Liga'
        verbose_name_plural = 'Ligas'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        achicar_imagen(self.logo)
        # La portada se reduce con su propio tope: se muestra a pantalla completa
        # y con los 512 px del resto de las imagenes quedaria pixelada.
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

    # Cuanto queda visible una liga concluida antes de que el superadmin pueda
    # eliminarla. Es para que la gente alcance a ver como termino: si se borrara
    # al cerrar, no quedaria nada que mostrar.
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
    # Con 6 decimales se distingue un punto de otro a menos de un metro, de
    # sobra para ubicar una cancha. Los grados de latitud llegan a 3 enteros
    # (-180 a 180 en longitud), asi que 9 digitos en total.
    latitud = models.DecimalField('Latitud', max_digits=9, decimal_places=6)
    longitud = models.DecimalField('Longitud', max_digits=9, decimal_places=6)

    class Meta:
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'
        ordering = ['nombre']
        # Dos canchas con el mismo nombre en la misma liga serian imposibles de
        # distinguir en el desplegable al programar un partido.
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

    limite_edad = models.CharField(
        'Límite de edad', max_length=4, choices=LIMITE_EDAD_CHOICES, blank=True,
        help_text='U9 entra un jugador de 9 años o menos, no uno de 10.',
    )
    reglas = models.TextField('Reglas de la competencia', blank=True)
    inscripcion_abierta = models.BooleanField('Inscripción abierta', default=True)
    activa = models.BooleanField('Categoría activa', default=True)

    # Se cierra sola al cargar el resultado de la final. Igual que en Liga, no
    # se reutiliza `activa`: una categoria terminada tiene que seguir visible.
    cerrada = models.BooleanField('Categoría concluida', default=False)
    fecha_cierre = models.DateTimeField('Concluida el', null=True, blank=True)

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

    # Las mujeres entran con un año mas que el limite de la categoria: en U17
    # juega una jugadora de 18, en U15 una de 16. Es un solo año, no dos.
    #
    # Va como constante y no como campo configurable por el mismo motivo que
    # Partido.MARCADOR_DEFAULT: es reglamento, igual en todas las ligas, y un
    # campo mas seria una decision para nada en cada alta de categoria.
    #
    # Todas las categorias son mixtas: no hay rama varonil ni femenil. Lo que
    # define el limite es el sexo del jugador, no el de la categoria.
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

    def edad_en_temporada(self, fecha_nacimiento):
        """Los años que cumple el jugador durante la temporada."""
        return self.anio_temporada - fecha_nacimiento.year

    def acepta(self, fecha_nacimiento, sexo=None):
        """Si el jugador entra en la categoria. Sin limite cargado no se restringe nada.

        Sin `sexo` se aplica el limite estricto, el de los varones.
        """
        if not self.limite_edad or not fecha_nacimiento:
            return True
        return self.edad_en_temporada(fecha_nacimiento) <= self.edad_maxima_para(sexo)

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


class Palmares(models.Model):
    """Lo que quedo de una categoria terminada: el podio y los premiados.

    Se llena una sola vez, al cargar el resultado de la final. La logica del
    calculo esta en apps/torneos/palmares.py, junto con el razonamiento de por
    que se congela en vez de calcularse al vuelo.

    Casi todo va como texto y no como clave foranea a proposito: pasado el mes
    de exhibicion, el superadmin elimina la liga con sus equipos, jugadores y
    partidos, y esta fila tiene que poder seguir contando quien gano.
    """

    liga_nombre = models.CharField('Liga', max_length=150)
    categoria_nombre = models.CharField('Categoría', max_length=120)

    # La referencia sirve para enlazar a las pantallas de la categoria mientras
    # exista. Al borrar la liga queda en null y sobreviven los nombres.
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

    # Los premios compartidos se guardan separados por ' / ': puede haber mas de
    # un ganador y el empate no se rompe con un criterio inventado.
    goleadores = models.CharField('Bota de oro', max_length=400, blank=True)
    goles_del_goleador = models.PositiveIntegerField('Goles', default=0)

    asistidores = models.CharField('Trofeo de asistencias', max_length=400, blank=True)
    asistencias_del_asistidor = models.PositiveIntegerField('Asistencias', default=0)

    vallas = models.CharField('Guante de oro', max_length=400, blank=True)
    goles_recibidos = models.PositiveIntegerField('Goles recibidos', default=0)

    # La tabla final completa, para mostrar quienes participaron y en que puesto
    # termino cada uno cuando ya no queden ni los equipos. Va como JSON y no como
    # tabla aparte porque no se filtra ni se ordena: se muestra entera o nada.
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
