from django import forms

from apps.equipos.models import Equipo
from apps.torneos.models import Sede
from apps.usuarios.forms import StyledFormMixin

from .models import Partido


class SelectDeSedes(forms.Select):
    """Desplegable de canchas que lleva las coordenadas en cada opcion.

    Asi el mapa del formulario se mueve a la cancha elegida sin volver a
    preguntarle al servidor, y el dato viaja pegado a la opcion que describe en
    vez de en un bloque JSON suelto que es facil de perder al editar la
    plantilla.
    """

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(name, value, label, selected, index, subindex, attrs)
        # La opcion vacia ('Sin definir todavía') no tiene instancia detras.
        sede = getattr(value, 'instance', None)
        if sede is not None:
            opcion['attrs'].update({
                'data-lat': str(sede.latitud),
                'data-lng': str(sede.longitud),
                'data-direccion': sede.direccion,
            })
        return opcion


class PartidoFechaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Partido
        fields = ['fecha', 'sede']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'sede': SelectDeSedes,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].required = True
        if self.instance.fue_movido:
            self.fields['fecha'].help_text = (
                f'Originalmente estaba para el {self.instance.fecha_original:%d/%m/%Y a las %H:%M}.'
            )

        # Solo las canchas de la liga de este partido: un admin no debe poder
        # mandar el id de una cancha de otra liga pasandolo a mano en el POST.
        sede = self.fields['sede']
        sede.queryset = Sede.objects.filter(liga=self.instance.categoria.liga)
        sede.required = False
        sede.label = 'Cancha'
        sede.empty_label = 'Sin definir todavía'
        sede.help_text = 'Márcala en el mapa, o elígela si ya la usaste antes.'
        if self.instance.cambio_de_cancha:
            sede.help_text = f'Al principio estaba asignada a {self.instance.sede_original.nombre}.'

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

        # La cancha se sigue igual que la fecha: se recuerda la primera para
        # poder avisar despues que el partido se mudo. Cambiar de cancha no
        # marca el partido como reprogramado: reprogramar es mover el cuando.
        if partido.sede_id and partido.sede_original_id is None:
            partido.sede_original_id = partido.sede_id

        if commit:
            partido.save()
        return partido


class SedeForm(StyledFormMixin, forms.ModelForm):
    """Alta de una cancha desde el mapa del formulario de programar.

    Las coordenadas llegan del pin y viajan en campos ocultos: el admin nunca
    escribe una latitud a mano.
    """

    CAMPOS_CAPITALIZAR = ('nombre',)

    class Meta:
        model = Sede
        fields = ['nombre', 'direccion', 'latitud', 'longitud']
        widgets = {
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
        }

    def __init__(self, liga, *args, **kwargs):
        self.liga = liga
        super().__init__(*args, **kwargs)
        self.fields['nombre'].widget.attrs['placeholder'] = 'Cancha Nido Águila'
        self.fields['direccion'].widget.attrs['placeholder'] = 'Se llena sola al marcar el punto'

    def clean_nombre(self):
        # unique_together vive en el modelo, pero el form no lo valida solo
        # porque la liga no es un campo suyo: se asigna recien en save().
        nombre = self.cleaned_data['nombre'].strip()
        if Sede.objects.filter(liga=self.liga, nombre__iexact=nombre).exists():
            raise forms.ValidationError('Ya tienes una cancha con ese nombre en esta liga.')
        return nombre

    def save(self, commit=True):
        sede = super().save(commit=False)
        sede.liga = self.liga
        if commit:
            sede.save()
        return sede


class ResultadoForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Partido
        fields = [
            'goles_local', 'goles_visitante',
            'ganador_penales', 'penales_local', 'penales_visitante',
        ]

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
        # El marcador de la tanda acompana al ganador de los penales: si se
        # patearon, se anota cuantos convirtio cada uno para poder dibujarla.
        for lado, campo in (('local', 'penales_local'), ('visitante', 'penales_visitante')):
            equipo = partido.equipo_local if lado == 'local' else partido.equipo_visitante
            self.fields[campo].required = False
            self.fields[campo].label = f'Penales de {equipo.nombre}'
            self.fields[campo].widget.attrs['data-solo-si-empate'] = '1'

        # Los penales solo aparecen en la final, que va a partido unico: es el
        # unico cruce que hay que definir si o si, porque no se puede coronar
        # campeon con una tabla que ya termino.
        define_el_titulo = partido.fase == Partido.FASE_FINAL and partido.cierra_la_llave

        if partido.es_liguilla and not define_el_titulo:
            # En el resto no se patea: el empate lo resuelve la tabla, que es la
            # ventaja ganada durante el torneo regular. Los campos de penales no
            # se ofrecen para que nadie los cargue de mas.
            mejor = min(partido.siembra_local or 99, partido.siembra_visitante or 99)
            del self.fields['ganador_penales']
            del self.fields['penales_local']
            del self.fields['penales_visitante']
            if partido.fase in Partido.FASES_PARTIDO_UNICO:
                self.sin_penales = (
                    f'Se juega a partido único. Si terminan empatados pasa el {mejor}º '
                    f'de la tabla.' if mejor != 99 else
                    'Se juega a partido único. Si terminan empatados pasa el mejor de la tabla.'
                )
            elif mejor != 99:
                self.sin_penales = (
                    f'Se define por el global de los dos partidos. Si terminan igualados '
                    f'pasa el {mejor}º de la tabla: en esta ronda no hay penales.'
                )
            else:
                self.sin_penales = 'Si el global termina igualado pasa el mejor ubicado en la tabla.'
        elif define_el_titulo:
            penales.empty_label = 'Todavía sin definir'
            penales.label = '¿Quién ganó la tanda de penales?'
            penales.help_text = (
                'Es la final: si terminó empatada, el campeón sale desde el punto penal.'
            )
        # El JS lo muestra solo cuando los goles quedan iguales.
        penales.widget.attrs['data-solo-si-empate'] = '1'

    # Se rellena en __init__ cuando la ronda no admite penales, para que la
    # plantilla lo explique en vez de mostrar un hueco donde estaba el campo.
    sin_penales = ''

    def _global_empatado(self, locales, visitantes):
        """Si la serie completa queda igualada con el resultado que se esta cargando.

        Suma el partido de ida al que se esta guardando. Se mira el global y no
        este marcador porque la liguilla es a ida y vuelta: una vuelta 1-1 con
        una ida 2-0 no define nada, y una vuelta 2-1 puede estar cerrando una
        serie empatada.
        """
        partido = self.instance
        propios, ajenos = locales, visitantes
        ida = Partido.objects.filter(
            categoria_id=partido.categoria_id, fase=partido.fase,
            orden=partido.orden, vuelta=False,
        ).exclude(pk=partido.pk).first()

        if ida and ida.jugado:
            # La localia se invierte entre la ida y la vuelta, asi que hay que
            # mirar de que lado jugo cada equipo en cada partido.
            if ida.equipo_local_id == partido.equipo_local_id:
                propios += ida.goles_local
                ajenos += ida.goles_visitante
            else:
                propios += ida.goles_visitante
                ajenos += ida.goles_local
        return propios == ajenos

    def clean(self):
        datos = super().clean()
        locales = datos.get('goles_local')
        visitantes = datos.get('goles_visitante')
        ganador = datos.get('ganador_penales')
        hay_marcador = locales is not None and visitantes is not None
        empate = hay_marcador and self._global_empatado(locales, visitantes)

        if self.instance.fase == Partido.FASE_FINAL and self.instance.cierra_la_llave and empate:
            # Alguien tiene que levantar la copa: sin ganador de la tanda el
            # torneo se quedaria sin campeon.
            if not ganador:
                self.add_error(
                    'ganador_penales',
                    'La final terminó empatada: indica quién ganó la tanda de penales.',
                )
            uno, otro = datos.get('penales_local'), datos.get('penales_visitante')
            if uno is None or otro is None:
                self.add_error(
                    'penales_local',
                    'Anota cuántos penales convirtió cada equipo en la tanda.',
                )
            elif uno == otro:
                self.add_error(
                    'penales_local',
                    'Una tanda no puede terminar igualada: se patea hasta que alguien queda arriba.',
                )
            elif ganador:
                # El que gano la tanda tiene que ser el que mas convirtio.
                arriba = self.instance.equipo_local if uno > otro else self.instance.equipo_visitante
                if ganador.id != arriba.id:
                    self.add_error(
                        'ganador_penales',
                        f'Según la tanda ({uno}-{otro}) el que ganó es {arriba.nombre}.',
                    )

        if ganador and hay_marcador and not empate:
            # Puede pasar si se eligio el ganador y despues se corrigio un gol:
            # el campo quedaria con un valor imposible.
            self.add_error(
                'ganador_penales',
                'Los penales solo se patean cuando el global de la serie termina empatado.',
            )
        return datos
