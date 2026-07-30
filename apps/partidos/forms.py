from django import forms

from apps.equipos.models import Equipo
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
        if self.instance.fue_movido:
            self.fields['fecha'].help_text = (
                f'Originalmente estaba para el {self.instance.fecha_original:%d/%m/%Y a las %H:%M}.'
            )

    def save(self, commit=True):
        partido = super().save(commit=False)
        if partido.fecha_original is None:
            # Primera vez que se programa: queda como referencia y no se vuelve
            # a tocar, para poder mostrar despues para cuando era.
            partido.fecha_original = partido.fecha
            partido.estado = Partido.ESTADO_PROGRAMADO
        elif partido.fecha != partido.fecha_original:
            partido.estado = Partido.ESTADO_REPROGRAMADO
        else:
            # Volvio a la fecha original: deja de estar reprogramado.
            partido.estado = Partido.ESTADO_PROGRAMADO
        if commit:
            partido.save()
        return partido


class ResultadoForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Partido
        fields = ['goles_local', 'goles_visitante', 'ganador_penales']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        partido = self.instance
        # Con el nombre del equipo se sabe de quien son los goles sin tener que
        # recordar cual de los dos era el local.
        self.fields['goles_local'].label = f'Goles de {partido.equipo_local.nombre}'
        self.fields['goles_visitante'].label = f'Goles de {partido.equipo_visitante.nombre}'

        penales = self.fields['ganador_penales']
        penales.queryset = Equipo.objects.filter(
            pk__in=[partido.equipo_local_id, partido.equipo_visitante_id]
        )
        penales.empty_label = 'No se jugaron penales'
        penales.required = False
        penales.label = '¿Quién ganó los penales?'
        penales.help_text = 'Suma un punto extra al que los gane.'
        # El JS lo muestra solo cuando los goles quedan iguales.
        penales.widget.attrs['data-solo-si-empate'] = '1'

    def clean(self):
        datos = super().clean()
        locales = datos.get('goles_local')
        visitantes = datos.get('goles_visitante')
        ganador = datos.get('ganador_penales')
        if ganador and locales is not None and visitantes is not None and locales != visitantes:
            # Puede pasar si se eligio el ganador y despues se corrigio un gol:
            # el campo quedaria con un valor imposible.
            self.add_error(
                'ganador_penales',
                'Los penales solo se juegan cuando el partido termina empatado.',
            )
        return datos
