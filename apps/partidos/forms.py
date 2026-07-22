from django import forms

from apps.usuarios.forms import StyledFormMixin

from .models import Partido


class PartidoFechaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Partido
        fields = ['fecha']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].required = True


class ResultadoForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Partido
        fields = ['goles_local', 'goles_visitante']
