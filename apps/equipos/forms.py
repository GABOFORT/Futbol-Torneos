from django import forms
from django.db.models import Count, F

from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.models import Usuario
from apps.usuarios.permissions import ligas_administradas
from apps.torneos.models import Categoria

from .models import Equipo


class EntrenadorChoiceField(forms.ModelChoiceField):
    """Desplegable de entrenadores que muestra el nombre y apellido.

    Por defecto Django dibuja el __str__ del usuario, que es el nombre de
    cuenta ('OMAR.27'); quien arma el equipo necesita ver a la persona.
    """

    def label_from_instance(self, usuario):
        return usuario.nombre_visible


class EquipoCreateForm(StyledFormMixin, forms.Form):
    CAMPOS_CAPITALIZAR = ('nombre',)

    nombre = forms.CharField(max_length=140, label='Nombre del equipo')
    escudo = forms.ImageField(
        required=False,
        label='Escudo del equipo',
        help_text='Opcional. Si lo dejas vacío se usa un escudo neutro.',
    )
    entrenador = EntrenadorChoiceField(
        queryset=Usuario.objects.entrenadores().order_by('first_name', 'last_name', 'username'),
        label='Entrenador',
        help_text='Quién va a manejar este equipo.',
    )
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label='Categorías',
        help_text='Marca en qué categorías participará este equipo. Se crea un equipo por cada una.',
    )
    observaciones = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label='Observaciones')

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        disponibles = Categoria.objects.filter(
            liga__in=ligas_administradas(user), inscripcion_abierta=True
        ).annotate(
            inscritos=Count('equipos')
        ).filter(
            inscritos__lt=F('cupo_equipos')
        ).select_related('liga').order_by('liga__nombre', 'nombre')
        self.fields['categorias'].queryset = disponibles.exclude(
            pk__in=[c.pk for c in disponibles if c.motivo_para_no_recibir_equipos()]
        )
        self.fields['entrenador'].queryset = Usuario.objects.entrenadores(user).order_by(
            'first_name', 'last_name', 'username'
        )

    def clean_categorias(self):
        categorias = self.cleaned_data['categorias']
        if not categorias:
            raise forms.ValidationError('Selecciona al menos una categoría.')
        motivos = [m for m in (c.motivo_para_no_recibir_equipos() for c in categorias) if m]
        if motivos:
            raise forms.ValidationError(motivos)
        return categorias


class EquipoForm(StyledFormMixin, forms.ModelForm):
    CAMPOS_CAPITALIZAR = ('nombre',)

    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        label='Categoría',
    )
    entrenador = EntrenadorChoiceField(
        queryset=Usuario.objects.entrenadores().order_by('first_name', 'last_name', 'username'),
        label='Entrenador',
    )

    class Meta:
        model = Equipo
        fields = ['nombre', 'escudo', 'liga', 'categoria', 'entrenador', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        liga = self.instance.liga if self.instance.liga_id else None
        self.torneo = getattr(liga, 'torneo', None)

        if self.torneo:
            self._fijar_categoria_del_torneo()
        else:
            self._ofrecer_ligas_de(user)

        entrenadores = Usuario.objects.entrenadores(user)
        if self.instance.pk and self.instance.entrenador_id:
            entrenadores = entrenadores | Usuario.objects.filter(pk=self.instance.entrenador_id)
        self.fields['entrenador'].queryset = entrenadores.distinct().order_by(
            'first_name', 'last_name', 'username'
        )

    def _fijar_categoria_del_torneo(self):
        """Un equipo de torneo no elige liga: la suya no es una liga del apartado.

        La categoria se deja a la vista pero cerrada con `disabled`, que hace que
        Django ignore lo que llegue por POST y reponga el valor guardado: quien
        edite el HTML a mano no consigue mover el equipo de torneo ni de grupo.
        """
        del self.fields['liga']
        campo = self.fields['categoria']
        campo.queryset = Categoria.objects.filter(pk=self.instance.categoria_id)
        campo.disabled = True
        campo.help_text = (
            f'Este equipo juega el torneo «{self.torneo.liga.nombre}». '
            f'Su categoría se administra desde el torneo.'
        )
        campo.widget.attrs['class'] += ' bg-gray-100 text-gray-600'

    def _ofrecer_ligas_de(self, user):
        """Solo las ligas que administra, y solo las categorias de esas ligas.

        `ligas_administradas` ya descarta los torneos, asi que acotar las
        categorias a esas ligas deja fuera de un golpe las de torneo y las de
        ligas ajenas.
        """
        suyas = ligas_administradas(user)
        self.fields['liga'].queryset = suyas
        campo = self.fields['categoria']
        campo.queryset = (Categoria.objects
                          .filter(liga__in=suyas)
                          .select_related('liga')
                          .order_by('liga__nombre', 'nombre'))
        campo.help_text = 'La categoría debe pertenecer a la liga seleccionada.'

    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')
        liga = cleaned_data.get('liga')
        if liga is None and self.instance.liga_id:
            liga = self.instance.liga
        if liga and categoria and categoria.liga_id != liga.id:
            self.add_error('categoria', 'Esta categoría no pertenece a la liga seleccionada.')
        if categoria and categoria.pk != self.instance.categoria_id:
            motivo = categoria.motivo_para_no_recibir_equipos()
            if motivo:
                self.add_error('categoria', motivo)
        return cleaned_data


class EquipoFormacionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['formacion', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }
