import datetime

from django import forms

from apps.usuarios.forms import StyledFormMixin

from .models import Jugador


def _dia(fecha):
    return fecha.strftime('%d/%m/%Y')


class JugadorForm(StyledFormMixin, forms.ModelForm):
    CAMPOS_OBLIGATORIOS = ('fecha_nacimiento',)
    CAMPOS_CAPITALIZAR = ('nombre', 'apellido')

    class Meta:
        model = Jugador
        fields = ['foto', 'nombre', 'apellido', 'sexo', 'fecha_nacimiento', 'posicion', 'numero', 'estado', 'observaciones']
        labels = {
            'nombre': 'Nombre completo',
            'apellido': 'Apellido completo',
        }
        widgets = {
            'sexo': forms.RadioSelect,
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, equipo, *args, **kwargs):
        self.equipo = equipo
        super().__init__(*args, **kwargs)

        campo = self.fields['fecha_nacimiento']
        campo.widget.attrs['max'] = datetime.date.today().isoformat()

        self.fields['sexo'].widget.attrs['data-sexo'] = '1'
        self.fields['sexo'].help_text = ''

        categoria = equipo.categoria if equipo else None
        if not categoria:
            return

        self._preparar_fecha(categoria)

    def _preparar_fecha(self, categoria):
        """Acota el selector de fecha y anuncia el limite de edad que aplica."""
        if categoria.libre:
            self.fields['fecha_nacimiento'].help_text = (
                'Categoría libre: entra cualquier jugador, sin importar la edad.'
            )
        elif categoria.limite_edad:
            self._preparar_edad_maxima(categoria)
        elif categoria.edad_minima:
            self._preparar_edad_minima(categoria)

    def _preparar_edad_maxima(self, categoria):
        """Las categorias U: tope de edad, con un año de tolerancia en mujeres."""
        campo = self.fields['fecha_nacimiento']

        topes = {
            valor: categoria.nacimiento_minimo_para(valor)
            for valor, _ in Jugador.SEXO_CHOICES
        }
        for valor, minimo in topes.items():
            campo.widget.attrs[f'data-min-{valor}'] = minimo.isoformat()

        elegido = self.data.get('sexo') or self.initial.get('sexo') or self.instance.sexo
        if elegido not in topes:
            elegido = Jugador.SEXO_MASCULINO
        campo.widget.attrs['min'] = topes[elegido].isoformat()

        campo.help_text = (
            f'{categoria.nombre} es {categoria.limite_edad}: hasta '
            f'{categoria.edad_maxima} años en varones (nacidos desde el '
            f'{_dia(topes[Jugador.SEXO_MASCULINO])}) y '
            f'{categoria.edad_maxima_femenino} en mujeres (desde el '
            f'{_dia(topes[Jugador.SEXO_FEMENINO])}).'
        )

    def _preparar_edad_minima(self, categoria):
        """Las categorias de veteranos: piso de edad, igual para los dos sexos."""
        campo = self.fields['fecha_nacimiento']
        tope = categoria.nacimiento_maximo
        campo.widget.attrs['max'] = tope.isoformat()
        campo.help_text = (
            f'{categoria.nombre} admite de {categoria.edad_minima} años para arriba: '
            f'nacidos hasta el {_dia(tope)}.'
        )

    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero is None or not self.equipo:
            return numero
        ocupado = Jugador.objects.filter(equipo=self.equipo, numero=numero)
        if self.instance.pk:
            ocupado = ocupado.exclude(pk=self.instance.pk)
        duenio = ocupado.first()
        if duenio:
            raise forms.ValidationError(
                f'El número {numero} ya lo tiene {duenio.nombre} {duenio.apellido} en este equipo.'
            )
        return numero

    def clean(self):
        """Revalida en el servidor que el jugador entre en la categoria.

        El selector de fecha ya trae el tope puesto, pero esconder o ampliar un
        campo en pantalla no impide mandar otra cosa por POST, y el JS puede
        estar apagado. La regla que manda es esta.
        """
        cleaned_data = super().clean()
        categoria = self.equipo.categoria if self.equipo else None
        if not categoria:
            return cleaned_data

        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')
        sexo = cleaned_data.get('sexo') or Jugador.SEXO_MASCULINO

        rechazo = categoria.rechazo_para(fecha_nacimiento, sexo)
        if rechazo is None:
            return cleaned_data

        campo, mensaje = rechazo

        if (
            campo == 'fecha_nacimiento'
            and sexo != Jugador.SEXO_FEMENINO
            and fecha_nacimiento
            and categoria.acepta(fecha_nacimiento, Jugador.SEXO_FEMENINO)
        ):
            mensaje += ' Si es mujer, marcá Femenino: con ese límite sí entra.'

        self.add_error(campo, mensaje)
        return cleaned_data
