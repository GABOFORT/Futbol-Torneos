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
        queryset=Categoria.objects.select_related('liga').order_by('liga__nombre', 'nombre'),
        label='Categoría',
        help_text='La categoría debe pertenecer a la liga seleccionada.',
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
        self.fields['liga'].queryset = ligas_administradas(user)
        entrenadores = Usuario.objects.entrenadores(user)
        if self.instance.pk and self.instance.entrenador_id:
            entrenadores = entrenadores | Usuario.objects.filter(pk=self.instance.entrenador_id)
        self.fields['entrenador'].queryset = entrenadores.distinct().order_by(
            'first_name', 'last_name', 'username'
        )

    def clean(self):
        cleaned_data = super().clean()
        liga = cleaned_data.get('liga')
        categoria = cleaned_data.get('categoria')
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
