from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Usuario
from apps.torneos.models import Liga


def a_titulo(texto):
    """Primera letra de cada palabra en mayuscula y el resto en minuscula."""
    return ' '.join(palabra[:1].upper() + palabra[1:].lower() for palabra in texto.split(' '))


class StyledFormMixin:
    CAMPOS_OBLIGATORIOS = ()

    CAMPOS_CAPITALIZAR = ('first_name', 'last_name', 'organization')

    CAMPOS_SOLO_NUMEROS = ('phone',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.CAMPOS_OBLIGATORIOS:
            self.fields[field_name].required = True
        for field_name, field in self.fields.items():
            classes = 'mt-2 w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm focus:border-green-600 focus:ring-2 focus:ring-green-200'
            if getattr(field.widget, 'input_type', None) == 'checkbox' or isinstance(field.widget, forms.CheckboxSelectMultiple):
                classes = 'h-4 w-4 rounded border-gray-300 text-green-700 focus:ring-green-500'
            elif isinstance(field.widget, forms.RadioSelect):
                classes = 'h-4 w-4 rounded-full border-gray-300 text-green-700 focus:ring-green-500'
            elif getattr(field.widget, 'input_type', None) == 'file':
                classes = ''
            field.widget.attrs.update({'class': classes})
            if field_name in self.CAMPOS_CAPITALIZAR:
                field.widget.attrs['data-capitalizar'] = '1'
            if field_name in self.CAMPOS_SOLO_NUMEROS:
                field.widget.attrs['data-solo-numeros'] = '1'
                field.widget.attrs['inputmode'] = 'numeric'
            if field.required:
                label = field.label or field_name.replace('_', ' ').capitalize()
                field.label = f'{label} *'

    def clean(self):
        cleaned_data = super().clean()
        for field_name, field in self.fields.items():
            valor = cleaned_data.get(field_name)
            if field.widget.attrs.get('data-capitalizar') and isinstance(valor, str):
                cleaned_data[field_name] = a_titulo(valor)
        return cleaned_data


class PasswordValidadoMixin:
    """Pasa la contrasena por AUTH_PASSWORD_VALIDATORS antes de aceptarla.

    Los validadores estan declarados en settings desde el principio, pero Django
    **no los aplica solo**: solo corren si alguien llama a `validate_password`.
    Eso lo hace `UserCreationForm`, y estos formularios no lo son —son ModelForm
    con el campo puesto a mano para poder ordenar y estilar el resto—, asi que la
    configuracion estaba ahi sin efecto: se aceptaba '123' como contrasena.

    `set_password()` hashea, no valida. Son dos pasos distintos, y el que faltaba
    era este.

    Vive en un mixin y no repetido en cada form para que valga igual en el alta y
    en la edicion, de usuarios y de entrenadores.
    """

    def _post_clean(self):
        """Valida la contrasena recien poblada la instancia.

        Va aca y no en `clean_password` porque uno de los validadores
        —UserAttributeSimilarityValidator— compara la contrasena contra el
        usuario, el nombre y el correo, y para eso necesita la instancia ya
        cargada con lo que se acaba de escribir. Durante `clean_password` todavia
        esta vacia: Django la llena en `_post_clean`, que corre despues. Poniendolo
        antes, una cuenta 'jperez' aceptaba 'jperez' como contrasena.

        Es el mismo punto donde lo hace el `UserCreationForm` de Django.
        """
        super()._post_clean()
        password = self.cleaned_data.get('password')
        if not password:
            return
        try:
            validate_password(password, self.instance)
        except forms.ValidationError as error:
            self.add_error('password', error)


class CuotaSegunRolMixin:
    """Las cuotas solo existen para el Administrador de Liga.

    Un Administrador General no tiene cuota (crea las que quiera) y un Entrenador
    no crea nada, así que los campos se esconden para esos dos roles y su valor se
    descarta al guardar. El JS los muestra y los oculta al vuelo; el `clean` repite
    la regla en el servidor, porque esconder un campo no impide mandarlo en el POST.
    """

    CAMPOS_DE_CUOTA = {
        'limite_ligas': (
            'Cuántas ligas en curso puede tener a la vez.',
            'Indica cuántas ligas puede crear este administrador.',
        ),
        'limite_torneos': (
            'Cuántos torneos relámpago en curso puede tener a la vez.',
            'Indica cuántos torneos puede crear este administrador.',
        ),
    }

    def _preparar_cuota(self):
        for nombre, (ayuda, _) in self.CAMPOS_DE_CUOTA.items():
            cuota = self.fields[nombre]
            cuota.required = False
            cuota.help_text = ayuda
            cuota.widget.attrs['data-solo-rol'] = Usuario.ROLE_ADMIN_LIGA
        self.fields['role'].widget.attrs['data-rol'] = '1'

    def clean(self):
        datos = super().clean()
        for nombre, (_, falta) in self.CAMPOS_DE_CUOTA.items():
            if datos.get('role') != Usuario.ROLE_ADMIN_LIGA:
                datos[nombre] = 0
                self.errors.pop(nombre, None)
            elif not datos.get(nombre):
                self.add_error(nombre, falta)
        return datos


class UsuarioCreateForm(PasswordValidadoMixin, CuotaSegunRolMixin, StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    CAMPOS_OBLIGATORIOS = ('first_name', 'last_name', 'phone')

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password', 'role', 'first_name', 'last_name', 'phone', 'organization', 'limite_ligas', 'limite_torneos']
        labels = {
            'role': 'Rol',
            'first_name': 'Nombre completo',
            'last_name': 'Apellido completo',
        }
        widgets = {
            'role': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._preparar_cuota()

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.limite_ligas = self.cleaned_data.get('limite_ligas') or 0
        usuario.limite_torneos = self.cleaned_data.get('limite_torneos') or 0
        usuario.set_password(self.cleaned_data['password'])
        if commit:
            usuario.save()
        return usuario


class EntrenadorCreateForm(PasswordValidadoMixin, StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    CAMPOS_OBLIGATORIOS = ('first_name', 'last_name', 'phone')

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone']
        labels = {
            'first_name': 'Nombre completo',
            'last_name': 'Apellido completo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.role = Usuario.ROLE_ENTRENADOR
        usuario.set_password(self.cleaned_data['password'])
        if commit:
            usuario.save()
        return usuario


class EntrenadorUpdateForm(PasswordValidadoMixin, StyledFormMixin, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, label='Nueva contraseña', required=False,
        help_text='Déjalo vacío para no cambiar la contraseña actual.',
    )
    CAMPOS_OBLIGATORIOS = ('first_name', 'last_name', 'phone')

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'phone']
        labels = {
            'first_name': 'Nombre completo',
            'last_name': 'Apellido completo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('password'):
            usuario.set_password(self.cleaned_data['password'])
        if commit:
            usuario.save()
        return usuario


class UsuarioUpdateForm(PasswordValidadoMixin, CuotaSegunRolMixin, StyledFormMixin, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, label='Nueva contraseña', required=False,
        help_text='Déjalo vacío para no cambiar la contraseña actual.',
    )
    CAMPOS_OBLIGATORIOS = ('first_name', 'last_name', 'phone')

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'role', 'first_name', 'last_name', 'phone', 'organization', 'limite_ligas', 'limite_torneos']
        labels = {
            'role': 'Rol',
            'first_name': 'Nombre completo',
            'last_name': 'Apellido completo',
        }
        widgets = {
            'role': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._preparar_cuota()

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.limite_ligas = self.cleaned_data.get('limite_ligas') or 0
        usuario.limite_torneos = self.cleaned_data.get('limite_torneos') or 0
        if self.cleaned_data.get('password'):
            usuario.set_password(self.cleaned_data['password'])
        if commit:
            usuario.save()
        return usuario


class LigaForm(StyledFormMixin, forms.ModelForm):
    CAMPOS_OBLIGATORIOS = ('nombre', 'fecha_inicio', 'fecha_final')
    CAMPOS_CAPITALIZAR = ()

    class Meta:
        model = Liga
        fields = ['nombre', 'logo', 'portada', 'descripcion', 'fecha_inicio', 'fecha_final', 'activa']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_final': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'activa': forms.CheckboxInput(),
        }
