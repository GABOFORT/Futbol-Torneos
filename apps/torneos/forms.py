from django import forms

from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.permissions import ligas_administradas

from .models import Categoria


class CategoriaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = [
            'liga', 'nombre', 'cupo_equipos', 'descripcion',
            'fecha_inicio', 'fecha_final', 'reglas', 'activa',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'reglas': forms.Textarea(attrs={'rows': 3}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_final': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['liga'].queryset = ligas_administradas(user)
        self.fields['nombre'].required = True
        self.fields['cupo_equipos'].required = True
