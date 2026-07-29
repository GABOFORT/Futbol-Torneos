import datetime

from django import forms

from apps.usuarios.forms import StyledFormMixin

from .models import Jugador


class JugadorForm(StyledFormMixin, forms.ModelForm):
    CAMPOS_OBLIGATORIOS = ('fecha_nacimiento',)
    CAMPOS_CAPITALIZAR = ('nombre', 'apellido')

    class Meta:
        model = Jugador
        fields = ['foto', 'nombre', 'apellido', 'fecha_nacimiento', 'posicion', 'numero', 'estado', 'observaciones']
        labels = {
            'nombre': 'Nombre completo',
            'apellido': 'Apellido completo',
        }
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, equipo, *args, **kwargs):
        # El equipo no es un campo del formulario (lo fija la vista), pero hace
        # falta aca para llegar a la categoria y su limite de edad.
        self.equipo = equipo
        super().__init__(*args, **kwargs)

        campo = self.fields['fecha_nacimiento']
        # Nadie nacio manana.
        campo.widget.attrs['max'] = datetime.date.today().isoformat()

        categoria = equipo.categoria if equipo else None
        minimo = categoria.nacimiento_minimo if categoria else None
        if minimo:
            # Con min/max el propio selector de fecha deja fuera lo que no
            # corresponde, en vez de aceptarlo y recien rebotarlo al guardar.
            campo.widget.attrs['min'] = minimo.isoformat()
            campo.help_text = (
                f'{categoria.nombre} es {categoria.limite_edad}: solo entran jugadores '
                f'nacidos desde el {minimo.strftime("%d/%m/%Y")}.'
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
            # Se nombra a quien lo tiene: saber que esta ocupado no alcanza para
            # elegir otro sin ponerse a revisar la plantilla.
            raise forms.ValidationError(
                f'El número {numero} ya lo tiene {duenio.nombre} {duenio.apellido} en este equipo.'
            )
        return numero

    def clean(self):
        cleaned_data = super().clean()
        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')
        categoria = self.equipo.categoria if self.equipo else None
        if fecha_nacimiento and categoria and not categoria.acepta(fecha_nacimiento):
            self.add_error('fecha_nacimiento', (
                f'La categoría {categoria.nombre} es {categoria.limite_edad}: solo entran '
                f'jugadores de hasta {categoria.edad_maxima} años. Este cumple '
                f'{categoria.edad_en_temporada(fecha_nacimiento)} en la temporada '
                f'{categoria.anio_temporada}.'
            ))
        return cleaned_data
