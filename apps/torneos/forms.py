from django import forms

from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.permissions import ligas_administradas

from .models import Categoria


class CategoriaForm(StyledFormMixin, forms.ModelForm):
    """Alta y edicion de una categoria, con la definicion de como se juega."""

    CAMPOS_OBLIGATORIOS = ('liga', 'nombre', 'cupo_equipos')
    CAMPOS_CAPITALIZAR = ('nombre',)

    SECCIONES = [
        {
            'titulo': 'Identificación',
            'descripcion': 'Qué categoría es y dentro de qué liga vive.',
            'campos': ['liga', 'nombre', 'cupo_equipos', 'descripcion'],
        },
        {
            'titulo': 'Quién puede inscribirse',
            'descripcion': 'La puerta de entrada. Si es libre, no se valida nada.',
            'campos': ['libre', 'limite_edad', 'edad_minima', 'peso_minimo'],
        },
        {
            'titulo': 'Cómo se juega',
            'descripcion': 'El formato de la competencia. Se congela al generar los partidos.',
            'campos': ['formato', 'grupos', 'cruces_entre_grupos',
                       'vueltas', 'empate_define_penales', 'mini_liguilla'],
        },
        {
            'titulo': 'Detalles',
            'descripcion': '',
            'campos': ['reglas', 'activa'],
        },
    ]

    CAMPOS_DE_FORMATO = ('formato', 'grupos', 'cruces_entre_grupos',
                         'vueltas', 'empate_define_penales', 'mini_liguilla')

    CAMPOS_DE_RESTRICCION = ('limite_edad', 'edad_minima', 'peso_minimo')

    CAMPOS_A_VALIDAR = (
        'libre', 'limite_edad', 'edad_minima', 'peso_minimo',
        'cupo_equipos', 'mini_liguilla', 'grupos', 'cruces_entre_grupos',
    )

    FORMATO_UNICO = 'unico'
    FORMATO_GRUPOS = 'grupos'

    FORMATO_CHOICES = [
        (FORMATO_UNICO, 'Todos contra todos · una sola tabla'),
        (FORMATO_GRUPOS, 'Round robin por grupos · cada grupo con su tabla'),
    ]

    formato = forms.ChoiceField(
        label='Formato del torneo regular',
        choices=FORMATO_CHOICES,
        initial=FORMATO_UNICO,
        widget=forms.RadioSelect,
        help_text='Por grupos, cada grupo juega su propio todos contra todos y '
                  'la liguilla se arma a mano con los que pasen.',
    )

    grupos = forms.TypedChoiceField(
        label='¿En cuántos grupos se reparten?',
        coerce=int,
        empty_value=Categoria.SIN_GRUPOS,
        required=False,
        help_text='Cada grupo lleva su propia tabla y nunca se cruza con otro.',
    )


    class Meta:
        model = Categoria
        fields = [
            'liga', 'nombre', 'cupo_equipos', 'descripcion',
            'libre', 'limite_edad', 'edad_minima', 'peso_minimo',
            'grupos', 'cruces_entre_grupos',
            'vueltas', 'empate_define_penales', 'mini_liguilla',
            'reglas', 'activa',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'reglas': forms.Textarea(attrs={'rows': 3}),
            'limite_edad': forms.RadioSelect,
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['liga'].queryset = ligas_administradas(user)

        self.fields['limite_edad'].choices = (
            [('', 'Ninguno')] + list(Categoria.LIMITE_EDAD_CHOICES)
        )
        self.fields['limite_edad'].help_text = (
            'Se cuenta por año de nacimiento. Las mujeres entran con un año más: '
            'en U17 juega una jugadora de 18.'
        )

        self.fields['libre'].widget.attrs['data-libre'] = '1'
        for nombre in self.CAMPOS_DE_RESTRICCION:
            self.fields[nombre].widget.attrs['data-restriccion'] = nombre

        vacias = {
            'edad_minima': ('Sin edad mínima', Categoria.EDAD_MINIMA_CHOICES),
            'peso_minimo': ('Sin peso mínimo', Categoria.PESO_MINIMO_CHOICES),
        }
        for nombre, (rotulo, opciones) in vacias.items():
            self.fields[nombre].choices = [('', rotulo)] + list(opciones)
            self.fields[nombre].widget.attrs['data-desplegable'] = '1'

        self._preparar_grupos()
        self._congelar_formato_si_ya_empezo()

    def _preparar_grupos(self):
        """El selector de grupos: cuantos son y con que letras quedan.

        El campo del modelo guarda un numero y cero significa sin grupos, pero
        en pantalla eso se parte en dos: un formato que se elige y, solo si es
        por grupos, cuantos. Asi el administrador no tiene que deducir que
        "cero grupos" es el torneo corrido de siempre.
        """
        campo = self.fields['grupos']
        campo.choices = Categoria.opciones_de_grupos()
        campo.widget.attrs['data-grupos'] = '1'
        self.fields['formato'].widget.attrs['data-formato'] = '1'

        if self.instance.pk and self.instance.juega_por_grupos:
            self.initial['formato'] = self.FORMATO_GRUPOS
            self.initial['grupos'] = self.instance.grupos
        else:
            self.initial['formato'] = self.FORMATO_UNICO
            self.initial.setdefault('grupos', Categoria.MINIMO_GRUPOS)

    def _congelar_formato_si_ya_empezo(self):
        """Bloquea el formato cuando la categoria ya tiene partidos generados.

        Con `disabled` Django ignora lo que venga por POST y conserva el valor
        guardado, asi que mandar el formulario a mano tampoco los cambia.
        """
        if not self.instance.pk or not self.instance.ajustes_congelados:
            return
        for nombre in self.CAMPOS_DE_FORMATO:
            campo = self.fields[nombre]
            campo.disabled = True
            campo.help_text = (
                'No se puede cambiar: la categoría ya tiene partidos generados. '
                'Cambiarlo ahora dejaría media temporada jugada con otro formato.'
            )

    def secciones(self):
        """Los campos ya agrupados y en orden, listos para la plantilla."""
        for seccion in self.SECCIONES:
            campos = [self[nombre] for nombre in seccion['campos']]
            yield {
                'titulo': seccion['titulo'],
                'descripcion': seccion['descripcion'],
                'campos': campos,
                'tiene_restricciones': any(
                    campo.name in self.CAMPOS_DE_RESTRICCION for campo in campos
                ),
            }

    @property
    def muestra_grupos(self):
        """Si el bloque de grupos arranca a la vista.

        Lo decide el servidor y no solo el JS: el bloque llega con `hidden`
        puesto cuando no corresponde, asi que no se asoma mientras carga la
        pagina ni se queda a la vista si el navegador trae en cache un
        `categoria_form.js` viejo.
        """
        datos = self.data if self.is_bound else self.initial
        return datos.get('formato') == self.FORMATO_GRUPOS

    @property
    def formato_congelado(self):
        """Si la categoria que se esta editando ya no admite cambios de formato."""
        return bool(self.instance.pk) and self.instance.ajustes_congelados

    def clean_grupos(self):
        grupos = self.cleaned_data.get('grupos')
        return int(grupos) if grupos else Categoria.SIN_GRUPOS

    def clean(self):
        """Normaliza las restricciones adelantando `Categoria.clean()`.

        Se adelanta por el efecto de lado, no por los errores: `libre` y un
        limite U limpian los campos que ganan, y esa limpieza tiene que estar
        hecha ANTES de que `_post_clean()` arme la instancia con `cleaned_data`.

        Los errores que levante se dejan pasar en silencio a proposito. Django
        vuelve a correr `Categoria.clean()` en `_post_clean()` y los reporta el
        solo —los tres campos que devuelve el modelo (`libre`, `cupo_equipos`,
        `mini_liguilla`) estan los tres en este formulario, asi que los mapea
        sin ayuda—. Reportarlos aca tambien los mostraba DOS VECES en pantalla.
        """
        cleaned_data = super().clean()

        if cleaned_data.get('formato') != self.FORMATO_GRUPOS:
            cleaned_data['grupos'] = Categoria.SIN_GRUPOS
            cleaned_data['cruces_entre_grupos'] = False
        elif not cleaned_data.get('grupos'):
            self.add_error('grupos', 'Elige en cuántos grupos se reparten los equipos.')

        if self.errors:
            return cleaned_data

        instancia = self.instance
        for campo in self.CAMPOS_A_VALIDAR:
            setattr(instancia, campo, cleaned_data.get(campo))

        try:
            instancia.clean()
        except forms.ValidationError:
            return cleaned_data

        for campo in self.CAMPOS_DE_RESTRICCION:
            cleaned_data[campo] = getattr(instancia, campo)

        return cleaned_data
