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


class UsuarioCreateForm(StyledFormMixin, forms.ModelForm):
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
        self.fields['limite_ligas'].help_text = 'Solo aplica para Administrador de Liga: cuántas ligas puede crear.'

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password'])
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


class UsuarioUpdateForm(StyledFormMixin, forms.ModelForm):
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
        self.fields['limite_ligas'].help_text = 'Solo aplica para Administrador de Liga: cuántas ligas puede crear.'

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('password'):
            usuario.set_password(self.cleaned_data['password'])
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
        fields = ['nombre', 'logo', 'descripcion', 'fecha_inicio', 'fecha_final', 'activa']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_final': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'activa': forms.CheckboxInput(),
        }
