from django import forms
from .models import Usuario
from apps.torneos.models import Liga


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            classes = 'mt-2 w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm focus:border-green-600 focus:ring-2 focus:ring-green-200'
            if getattr(field.widget, 'input_type', None) == 'checkbox' or isinstance(field.widget, forms.CheckboxSelectMultiple):
                classes = 'h-4 w-4 rounded border-gray-300 text-green-700 focus:ring-green-500'
            field.widget.attrs.update({'class': classes})
            if field.required:
                label = field.label or field_name.replace('_', ' ').capitalize()
                field.label = f'{label} *'


class UsuarioCreateForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password', 'role', 'first_name', 'last_name', 'phone', 'organization', 'limite_ligas']
        widgets = {
            'role': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['limite_ligas'].help_text = 'Solo aplica para Administrador de Liga: cuántas ligas puede crear.'

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password'])
        if commit:
            usuario.save()
        return usuario


class EntrenadorCreateForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['phone'].required = True
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

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['phone'].required = True
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

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'role', 'first_name', 'last_name', 'phone', 'organization', 'limite_ligas']
        widgets = {
            'role': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['limite_ligas'].help_text = 'Solo aplica para Administrador de Liga: cuántas ligas puede crear.'

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('password'):
            usuario.set_password(self.cleaned_data['password'])
        if commit:
            usuario.save()
        return usuario


class LigaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Liga
        fields = ['nombre', 'descripcion', 'fecha_inicio', 'fecha_final', 'activa']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_final': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'activa': forms.CheckboxInput(),
        }
