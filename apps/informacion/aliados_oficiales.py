from django import forms
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.torneos.patrocinadores import CENTRO_POR_DEFECTO
from apps.usuarios.eliminar import vista_eliminar
from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.permissions import superadmin_required

from .models import PatrocinadorOficial


class PatrocinadorOficialForm(StyledFormMixin, forms.ModelForm):
    CAMPOS_OBLIGATORIOS = ('nombre',)
    CAMPOS_CAPITALIZAR = ('nombre',)
    CAMPOS_SOLO_NUMEROS = ('telefono',)

    mapa = True

    class Meta:
        model = PatrocinadorOficial
        fields = [
            'nombre', 'logo', 'giro', 'direccion', 'latitud', 'longitud',
            'telefono', 'enlace', 'orden', 'activo',
        ]
        widgets = {
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        marcadores = {
            'nombre': 'Refaccionaria El Búho',
            'giro': 'Refacciones y accesorios',
            'direccion': 'Se llena sola al marcar el punto',
            'enlace': 'https://www.facebook.com/…',
        }
        for campo, texto in marcadores.items():
            self.fields[campo].widget.attrs['placeholder'] = texto
        self._preparar_lugar()

    def _preparar_lugar(self):
        campo = self.fields['orden']
        campo.required = False
        campo.label = 'Lugar en la fila'
        campo.help_text = ('Los números más chicos salen primero en la fila. '
                           'Ya viene calculado: solo cámbialo si quieres adelantar a alguien.')
        campo.widget.attrs['min'] = 0
        if not self.instance.pk:
            ultimo = PatrocinadorOficial.objects.order_by('-orden').first()
            campo.initial = (ultimo.orden + 1) if ultimo else 1

    def clean_orden(self):
        return self.cleaned_data.get('orden') or 0

    def clean_nombre(self):
        return self.cleaned_data['nombre'].strip()


def _centro_del_mapa():
    ubicado = (PatrocinadorOficial.objects
               .filter(latitud__isnull=False)
               .order_by('-id')
               .first())
    if ubicado:
        return (ubicado.latitud, ubicado.longitud)
    return CENTRO_POR_DEFECTO


@superadmin_required
def lista(request):
    patrocinadores = list(PatrocinadorOficial.objects.all())
    return render(request, 'informacion/aliados_oficiales.html', {
        'patrocinadores': patrocinadores,
        'visibles': sum(1 for uno in patrocinadores if uno.activo),
    })


@superadmin_required
def crear(request):
    return _formulario(request, None)


@superadmin_required
def editar(request, pk):
    return _formulario(request, get_object_or_404(PatrocinadorOficial, pk=pk))


def _formulario(request, instancia):
    modal = request.GET.get('modal') == '1'
    nuevo = instancia is None

    if request.method == 'POST':
        form = PatrocinadorOficialForm(request.POST, request.FILES, instance=instancia)
        if form.is_valid():
            patrocinador = form.save()
            messages.success(
                request,
                f'"{patrocinador.nombre}" {"agregado a" if nuevo else "actualizado en"} '
                f'los patrocinadores oficiales.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('aliados-oficiales')
    else:
        form = PatrocinadorOficialForm(instance=instancia)

    contexto = {
        'form': form,
        'title': ('Nuevo patrocinador oficial' if nuevo
                  else f'Editar patrocinador oficial: {instancia.nombre}'),
        'centro_mapa': _centro_del_mapa(),
    }
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'informacion/aliado_oficial_form.html', contexto)


@superadmin_required
def eliminar(request, pk):
    patrocinador = get_object_or_404(PatrocinadorOficial, pk=pk)
    return vista_eliminar(
        request,
        instancia=patrocinador,
        etiqueta=f'Patrocinador oficial: {patrocinador.nombre}',
        url_listado='aliados-oficiales',
        mensaje_ok=f'Se eliminó a "{patrocinador.nombre}" de los patrocinadores oficiales.',
    )


def ficha(request, pk):
    patrocinador = get_object_or_404(PatrocinadorOficial.objects.visibles(), pk=pk)
    modal = request.GET.get('modal') == '1'
    contexto = {'patrocinador': patrocinador, 'en_modal': modal}
    if modal:
        return render(request, 'informacion/_aliado_oficial_ficha.html', contexto)
    return render(request, 'informacion/aliado_oficial_detalle.html', contexto)
