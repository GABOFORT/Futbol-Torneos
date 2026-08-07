from django import forms
from .models import Usuario
from apps.torneos.models import Liga


def a_titulo(texto):
    """Primera letra de cada palabra en mayuscula y el resto en minuscula."""
    return ' '.join(palabra[:1].upper() + palabra[1:].lower() for palabra in texto.split(' '))


class StyledFormMixin:
    # Campos que el formulario fuerza como obligatorios aunque el modelo los
    # permita vacios. Se declaran aca y no en el __init__ del form para que ya
    # esten marcados cuando se arman los labels y reciban el asterisco.
    CAMPOS_OBLIGATORIOS = ()

    # Campos que se capitalizan solos. Cada formulario puede pisar la lista.
    CAMPOS_CAPITALIZAR = ('first_name', 'last_name', 'organization')

    # Campos que solo aceptan digitos. El largo permitido no se repite aca:
    # sale del maxlength que el widget hereda del max_length del modelo.
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
                # El input de archivo se estiliza en base.html junto con su
                # miniatura; los estilos de caja de texto le quedan pesimo.
                classes = ''
            field.widget.attrs.update({'class': classes})
            if field_name in self.CAMPOS_CAPITALIZAR:
                # El JS de static/js/forms.js usa esta marca para capitalizar mientras se escribe.
                field.widget.attrs['data-capitalizar'] = '1'
            if field_name in self.CAMPOS_SOLO_NUMEROS:
                field.widget.attrs['data-solo-numeros'] = '1'
                field.widget.attrs['inputmode'] = 'numeric'
            if field.required:
                label = field.label or field_name.replace('_', ' ').capitalize()
                field.label = f'{label} *'

    def clean(self):
        # Se repite en servidor lo que hace el JS: si pegan texto, si el JS esta
        # apagado o si mandan el POST directo, igual se guarda capitalizado.
        cleaned_data = super().clean()
        for field_name, field in self.fields.items():
            valor = cleaned_data.get(field_name)
            if field.widget.attrs.get('data-capitalizar') and isinstance(valor, str):
                cleaned_data[field_name] = a_titulo(valor)
        return cleaned_data


class CuotaSegunRolMixin:
    """El límite de ligas solo existe para el Administrador de Liga.

    Un Administrador General no tiene cuota (crea las que quiera) y un Entrenador
    no crea ligas, así que el campo se esconde para esos dos roles y su valor se
    descarta al guardar. El JS lo muestra y lo oculta al vuelo; el `clean` repite
    la regla en el servidor, porque esconder un campo no impide mandarlo en el POST.
    """

    def _preparar_cuota(self):
        cuota = self.fields['limite_ligas']
        cuota.required = False
        cuota.help_text = 'Cuántas ligas en curso puede tener a la vez.'
        # static/js/roles.js usa estas marcas para mostrar u ocultar el campo.
        cuota.widget.attrs['data-solo-rol'] = Usuario.ROLE_ADMIN_LIGA
        self.fields['role'].widget.attrs['data-rol'] = '1'

    def clean(self):
        datos = super().clean()
        if datos.get('role') != Usuario.ROLE_ADMIN_LIGA:
            # Se guarda en cero en vez de dejar el default 1: así no queda una
            # cuota fantasma en cuentas a las que no les aplica.
            datos['limite_ligas'] = 0
            self.errors.pop('limite_ligas', None)
        elif not datos.get('limite_ligas'):
            self.add_error('limite_ligas', 'Indica cuántas ligas puede crear este administrador.')
        return datos


class UsuarioCreateForm(CuotaSegunRolMixin, StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    CAMPOS_OBLIGATORIOS = ('first_name', 'last_name', 'phone')

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password', 'role', 'first_name', 'last_name', 'phone', 'organization', 'limite_ligas']
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
        usuario.set_password(self.cleaned_data['password'])
        # is_superuser / is_staff los resuelve Usuario.save() segun el rol.
        if commit:
            usuario.save()
        return usuario


class EntrenadorCreateForm(StyledFormMixin, forms.ModelForm):
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


class EntrenadorUpdateForm(StyledFormMixin, forms.ModelForm):
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


class UsuarioUpdateForm(CuotaSegunRolMixin, StyledFormMixin, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, label='Nueva contraseña', required=False,
        help_text='Déjalo vacío para no cambiar la contraseña actual.',
    )
    CAMPOS_OBLIGATORIOS = ('first_name', 'last_name', 'phone')

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'role', 'first_name', 'last_name', 'phone', 'organization', 'limite_ligas']
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
        if self.cleaned_data.get('password'):
            usuario.set_password(self.cleaned_data['password'])
        # Cambiar el rol a Administrador General tambien enciende is_superuser:
        # lo resuelve Usuario.save(), asi vale igual al crear que al editar.
        if commit:
            usuario.save()
        return usuario


class LigaForm(StyledFormMixin, forms.ModelForm):
    CAMPOS_OBLIGATORIOS = ('nombre', 'fecha_inicio', 'fecha_final')
    # Sin capitalizacion automatica: el nombre de una liga es una marca y hay que
    # respetarlo tal cual lo escriben. La regla convertia "Liga MX" en "Liga Mx".
    CAMPOS_CAPITALIZAR = ()

    class Meta:
        model = Liga
        # `portada` va pegada a `logo`: son las dos imagenes de identidad de la
        # liga y conviene que se carguen juntas, no en extremos del formulario.
        fields = ['nombre', 'logo', 'portada', 'descripcion', 'fecha_inicio', 'fecha_final', 'activa']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_final': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'activa': forms.CheckboxInput(),
        }
