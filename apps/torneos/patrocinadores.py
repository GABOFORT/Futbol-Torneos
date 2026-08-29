"""Los patrocinadores de una liga o de un torneo.

Se cargan una sola vez, colgados de la liga, y de ahi salen solos en todas las
pantallas que dependen de ella. El reparto lo resuelve el template tag
`patrocinadores_de_la_pantalla`, no estas vistas: aca solo se administran.

Un torneo relampago se apoya en una Liga, asi que el mismo listado sirve para
los dos apartados y se entra por `ligas_y_torneos_administrados`.
"""
from django import forms
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.eliminar import vista_eliminar
from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.permissions import (
    admin_liga_required, ligas_y_torneos_administrados, ligas_y_torneos_visibles,
)

from .models import Patrocinador

CENTRO_POR_DEFECTO = ('17.989500', '-92.947500')


class PatrocinadorForm(StyledFormMixin, forms.ModelForm):
    CAMPOS_OBLIGATORIOS = ('nombre',)
    CAMPOS_CAPITALIZAR = ('nombre',)
    CAMPOS_SOLO_NUMEROS = ('telefono',)

    mapa = True

    class Meta:
        model = Patrocinador
        fields = [
            'nombre', 'logo', 'giro', 'direccion', 'latitud', 'longitud',
            'telefono', 'enlace', 'orden', 'activo',
        ]
        widgets = {
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
        }

    def __init__(self, liga, *args, **kwargs):
        self.liga = liga
        super().__init__(*args, **kwargs)
        marcadores = {
            'nombre': 'Taquería El Buen Pastor',
            'giro': 'Taquería y mariscos',
            'direccion': 'Se llena sola al marcar el punto',
            'enlace': 'https://www.facebook.com/…',
        }
        for campo, texto in marcadores.items():
            self.fields[campo].widget.attrs['placeholder'] = texto

        self._preparar_lugar()

    def _preparar_lugar(self):
        """`orden` decide quien va primero en la fila, y con uno solo no hace nada.

        Se ofrece ya resuelto —el siguiente numero libre— porque el admin no
        tiene por que pensarlo: cargando uno tras otro quedan en el orden en que
        los dio de alta, que es lo que espera. Solo lo toca el dia que quiera
        adelantar a alguno.
        """
        campo = self.fields['orden']
        campo.required = False
        campo.label = 'Lugar en la fila'
        campo.help_text = ('Los números más chicos salen primero en la fila. '
                           'Ya viene calculado: solo cámbialo si quieres adelantar a alguien.')
        campo.widget.attrs['min'] = 0
        if not self.instance.pk:
            ultimo = self.liga.patrocinadores.order_by('-orden').first()
            campo.initial = (ultimo.orden + 1) if ultimo else 1

    def clean_orden(self):
        return self.cleaned_data.get('orden') or 0

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        hermanos = Patrocinador.objects.filter(liga=self.liga, nombre__iexact=nombre)
        if self.instance.pk:
            hermanos = hermanos.exclude(pk=self.instance.pk)
        if hermanos.exists():
            raise forms.ValidationError(
                f'"{nombre}" ya está cargado en {self.liga.nombre}.')
        return nombre

    def save(self, commit=True):
        patrocinador = super().save(commit=False)
        patrocinador.liga = self.liga
        if commit:
            patrocinador.save()
        return patrocinador


def _centro_de(liga):
    """Donde conviene abrir el mapa para marcar un patrocinador de esta liga.

    Se busca el punto mas cercano a lo que el admin va a marcar: otro
    patrocinador ya ubicado, o una cancha de la liga. Asi el pin no arranca en
    medio del oceano y casi siempre queda a unas cuadras del lugar buscado.
    """
    ubicado = (liga.patrocinadores
               .filter(latitud__isnull=False)
               .order_by('-id')
               .first())
    if ubicado:
        return (ubicado.latitud, ubicado.longitud)
    cancha = liga.sedes.order_by('-id').first()
    if cancha:
        return (cancha.latitud, cancha.longitud)
    return CENTRO_POR_DEFECTO


@admin_liga_required
def lista(request, pk):
    liga = get_object_or_404(ligas_y_torneos_administrados(request.user), pk=pk)
    patrocinadores = list(liga.patrocinadores.all())
    return render(request, 'torneos/patrocinadores_list.html', {
        'liga': liga,
        'torneo': getattr(liga, 'torneo', None),
        'patrocinadores': patrocinadores,
        'visibles': sum(1 for uno in patrocinadores if uno.activo),
    })


@admin_liga_required
def crear(request, pk):
    liga = get_object_or_404(ligas_y_torneos_administrados(request.user), pk=pk)
    return _formulario(request, liga, None)


@admin_liga_required
def editar(request, pk, patrocinador_pk):
    liga = get_object_or_404(ligas_y_torneos_administrados(request.user), pk=pk)
    patrocinador = get_object_or_404(liga.patrocinadores, pk=patrocinador_pk)
    return _formulario(request, liga, patrocinador)


def _formulario(request, liga, instancia):
    modal = request.GET.get('modal') == '1'
    nuevo = instancia is None

    if request.method == 'POST':
        form = PatrocinadorForm(liga, request.POST, request.FILES, instance=instancia)
        if form.is_valid():
            patrocinador = form.save()
            messages.success(
                request,
                f'"{patrocinador.nombre}" {"agregado a" if nuevo else "actualizado en"} '
                f'{liga.nombre}.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('patrocinadores', pk=liga.pk)
    else:
        form = PatrocinadorForm(liga, instance=instancia)

    contexto = {
        'form': form,
        'liga': liga,
        'title': (f'Nuevo patrocinador · {liga.nombre}' if nuevo
                  else f'Editar patrocinador: {instancia.nombre}'),
        'centro_mapa': _centro_de(liga),
    }
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'torneos/patrocinador_form.html', contexto)


@admin_liga_required
def eliminar(request, pk, patrocinador_pk):
    liga = get_object_or_404(ligas_y_torneos_administrados(request.user), pk=pk)
    patrocinador = get_object_or_404(liga.patrocinadores, pk=patrocinador_pk)
    return vista_eliminar(
        request,
        instancia=patrocinador,
        etiqueta=f'Patrocinador: {patrocinador.nombre}',
        url_listado='patrocinadores',
        url_listado_args=(liga.pk,),
        mensaje_ok=f'Se eliminó a "{patrocinador.nombre}" de {liga.nombre}.',
    )


def ficha(request, pk):
    """Quien es y donde esta, al pulsar su logo. Publica, como toda la vitrina."""
    patrocinador = get_object_or_404(
        Patrocinador.objects
        .select_related('liga')
        .filter(activo=True, liga__in=ligas_y_torneos_visibles(request.user)),
        pk=pk,
    )
    modal = request.GET.get('modal') == '1'
    contexto = {'patrocinador': patrocinador, 'liga': patrocinador.liga, 'en_modal': modal}
    if modal:
        return render(request, 'torneos/_patrocinador_ficha.html', contexto)
    return render(request, 'torneos/patrocinador_detalle.html', contexto)
