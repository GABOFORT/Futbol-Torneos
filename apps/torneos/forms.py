from django import forms

from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.permissions import ligas_administradas

from .models import Categoria


class CategoriaForm(StyledFormMixin, forms.ModelForm):
    CAMPOS_OBLIGATORIOS = ('liga', 'nombre', 'cupo_equipos', 'limite_edad')
    CAMPOS_CAPITALIZAR = ('nombre',)

    class Meta:
        model = Categoria
        fields = [
            'liga', 'nombre', 'cupo_equipos', 'limite_edad',
            'descripcion', 'reglas', 'activa',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'reglas': forms.Textarea(attrs={'rows': 3}),
            'limite_edad': forms.RadioSelect,
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['liga'].queryset = ligas_administradas(user)
        # El campo permite vacio en el modelo, asi que Django agrega una opcion
        # en blanco: con radios seria un boton mas, sin etiqueta y elegible.
        self.fields['limite_edad'].choices = Categoria.LIMITE_EDAD_CHOICES
        # La tolerancia femenina se anuncia al crear la categoria y no recien al
        # cargar un jugador: quien define el limite tiene que saber que en la
        # practica la categoria admite dos edades, no una.
        self.fields['limite_edad'].help_text = (
            'Se cuenta por año de nacimiento. Las mujeres entran con un año más: '
            'en U17 juega una jugadora de 18.'
        )
