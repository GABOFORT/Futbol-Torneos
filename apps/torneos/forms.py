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
            'campos': ['vueltas', 'empate_define_penales', 'mini_liguilla'],
        },
        {
            'titulo': 'Detalles',
            'descripcion': '',
            'campos': ['reglas', 'activa'],
        },
    ]

    CAMPOS_DE_FORMATO = ('vueltas', 'empate_define_penales', 'mini_liguilla')

    CAMPOS_DE_RESTRICCION = ('limite_edad', 'edad_minima', 'peso_minimo')

    CAMPOS_A_VALIDAR = (
        'libre', 'limite_edad', 'edad_minima', 'peso_minimo',
        'cupo_equipos', 'mini_liguilla',
    )


    class Meta:
        model = Categoria
        fields = [
            'liga', 'nombre', 'cupo_equipos', 'descripcion',
            'libre', 'limite_edad', 'edad_minima', 'peso_minimo',
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

        self._congelar_formato_si_ya_empezo()

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
    def formato_congelado(self):
        """Si la categoria que se esta editando ya no admite cambios de formato."""
        return bool(self.instance.pk) and self.instance.ajustes_congelados

    def clean(self):
        """Valida la combinacion de restricciones reusando `Categoria.clean()`."""
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        instancia = self.instance
        for campo in self.CAMPOS_A_VALIDAR:
            setattr(instancia, campo, cleaned_data.get(campo))

        try:
            instancia.clean()
        except forms.ValidationError as error:
            self.add_error(None, error)
            return cleaned_data

        for campo in self.CAMPOS_DE_RESTRICCION:
            cleaned_data[campo] = getattr(instancia, campo)

        return cleaned_data
