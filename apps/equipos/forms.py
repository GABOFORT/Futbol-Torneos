from django import forms

from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.models import Usuario
from apps.usuarios.permissions import ligas_administradas
from apps.torneos.models import Categoria

from .models import Equipo


class EquipoCreateForm(StyledFormMixin, forms.Form):
    nombre = forms.CharField(max_length=140, label='Nombre del equipo')
    entrenador = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(role=Usuario.ROLE_ENTRENADOR).order_by('username'),
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
        self.fields['categorias'].queryset = Categoria.objects.filter(
            liga__in=ligas_administradas(user)
        ).select_related('liga').order_by('liga__nombre', 'nombre')

    def clean_categorias(self):
        categorias = self.cleaned_data['categorias']
        if not categorias:
            raise forms.ValidationError('Selecciona al menos una categoría.')
        return categorias


class EquipoForm(StyledFormMixin, forms.ModelForm):
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.select_related('liga').order_by('liga__nombre', 'nombre'),
        label='Categoría',
        help_text='La categoría debe pertenecer a la liga seleccionada.',
    )
    entrenador = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(role=Usuario.ROLE_ENTRENADOR).order_by('username'),
        label='Entrenador',
    )

    class Meta:
        model = Equipo
        fields = ['nombre', 'liga', 'categoria', 'entrenador', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['liga'].queryset = ligas_administradas(user)

    def clean(self):
        cleaned_data = super().clean()
        liga = cleaned_data.get('liga')
        categoria = cleaned_data.get('categoria')
        if liga and categoria and categoria.liga_id != liga.id:
            self.add_error('categoria', 'Esta categoría no pertenece a la liga seleccionada.')
        return cleaned_data


class EquipoFormacionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['formacion', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }
