from django import forms

from apps.usuarios.forms import StyledFormMixin

from .models import Jugador


class JugadorForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ['foto', 'nombre', 'apellido', 'fecha_nacimiento', 'posicion', 'numero', 'estado', 'observaciones']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }
