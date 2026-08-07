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
        # El sexo va antes de la fecha de nacimiento a proposito: es lo que
        # define el limite de edad, asi que primero se dice quien es y recien
        # despues se elige la fecha, ya con el rango que le corresponde.
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
        # El equipo no es un campo del formulario (lo fija la vista), pero hace
        # falta aca para llegar a la categoria y su limite de edad.
        self.equipo = equipo
        super().__init__(*args, **kwargs)

        campo = self.fields['fecha_nacimiento']
        # Nadie nacio manana.
        campo.widget.attrs['max'] = datetime.date.today().isoformat()

        # El desplegable de sexo se marca para que el JS lo encuentre: al
        # cambiarlo tiene que correr el tope del selector de fecha.
        self.fields['sexo'].widget.attrs['data-sexo'] = '1'
        self.fields['sexo'].help_text = ''   # la explicacion va en la fecha, que es donde se nota

        categoria = equipo.categoria if equipo else None
        if not categoria or not categoria.limite_edad:
            return

        # Los dos topes viajan con el campo. El limite depende del sexo, que se
        # elige en este mismo formulario, asi que ya no alcanza con calcular uno
        # solo al abrir: el JS alterna entre estos dos sin volver al servidor.
        topes = {
            valor: categoria.nacimiento_minimo_para(valor)
            for valor, _ in Jugador.SEXO_CHOICES
        }
        for valor, minimo in topes.items():
            campo.widget.attrs[f'data-min-{valor}'] = minimo.isoformat()

        # Con min/max el propio selector de fecha deja fuera lo que no
        # corresponde, en vez de aceptarlo y recien rebotarlo al guardar.
        elegido = self.data.get('sexo') or self.initial.get('sexo') or self.instance.sexo
        if elegido not in topes:
            elegido = Jugador.SEXO_MASCULINO
        campo.widget.attrs['min'] = topes[elegido].isoformat()

        # El texto nombra los dos limites siempre, aunque el JS resalte el que
        # aplica: quien carga la plantilla tiene que saber que la tolerancia
        # existe antes de toparse con el error.
        campo.help_text = (
            f'{categoria.nombre} es {categoria.limite_edad}: hasta '
            f'{categoria.edad_maxima} años en varones (nacidos desde el '
            f'{_dia(topes[Jugador.SEXO_MASCULINO])}) y '
            f'{categoria.edad_maxima_femenino} en mujeres (desde el '
            f'{_dia(topes[Jugador.SEXO_FEMENINO])}).'
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
        """Revalida la edad en el servidor.

        El selector de fecha ya trae el tope puesto, pero esconder o ampliar un
        campo en pantalla no impide mandar otra cosa por POST, y el JS puede
        estar apagado. La regla que manda es esta.
        """
        cleaned_data = super().clean()
        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')
        sexo = cleaned_data.get('sexo') or Jugador.SEXO_MASCULINO
        categoria = self.equipo.categoria if self.equipo else None

        if not fecha_nacimiento or not categoria or categoria.acepta(fecha_nacimiento, sexo):
            return cleaned_data

        cumple = categoria.edad_en_temporada(fecha_nacimiento)
        etiqueta = dict(Jugador.SEXO_CHOICES)[sexo]
        mensaje = (
            f'La categoría {categoria.nombre} es {categoria.limite_edad}: admite hasta '
            f'{categoria.edad_maxima} años en varones y {categoria.edad_maxima_femenino} '
            f'en mujeres. Marcaste {etiqueta} y cumple {cumple} '
            f'en la temporada {categoria.anio_temporada}.'
        )

        # El caso que de otro modo se lee como una falla del sistema: la fecha
        # entraria si estuviera bien marcado el sexo. Pasa al cargar una
        # jugadora sin cambiar el sexo, y tambien al corregirle el sexo a una
        # que ya estaba cargada. Sin esta linea el mensaje habla de la fecha y
        # el problema esta en el campo de al lado.
        if categoria.acepta(fecha_nacimiento, Jugador.SEXO_FEMENINO):
            mensaje += ' Si es mujer, marcá Femenino: con ese límite sí entra.'

        self.add_error('fecha_nacimiento', mensaje)
        return cleaned_data
