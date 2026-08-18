"""El apartado de torneos relámpago: alta, listado y cuadro.

Vive aparte de las ligas aunque se apoye en ellas: quien entra aca esta armando
un evento de un dia, no una temporada.
"""
from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.partidos import relampago
from apps.partidos.models import Partido
from apps.usuarios.eliminar import entrenadores_sin_equipo_tras_borrar, vista_eliminar
from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.models import Usuario
from apps.usuarios.permissions import (
    admin_liga_required, superadmin_required, torneos_administrados, torneos_visibles,
)

from .models import Categoria, Liga, Palmares, Torneo

CATEGORIA_UNICA = 'General'


class TorneoForm(StyledFormMixin, forms.Form):
    CAMPOS_OBLIGATORIOS = ('nombre', 'fecha', 'equipos')
    CAMPOS_CAPITALIZAR = ('nombre',)

    nombre = forms.CharField(max_length=150, label='Nombre del torneo')
    logo = forms.ImageField(
        required=False, label='Logo del torneo',
        help_text='Opcional. Si lo dejas vacío se muestran las iniciales.')
    portada = forms.ImageField(
        required=False, label='Portada del torneo',
        help_text='Opcional. Se muestra de fondo en las pantallas del torneo.')
    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), required=False, label='Descripción')
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        label='Día del torneo',
        help_text='El torneo se juega entero en esta fecha.')
    equipos = forms.TypedChoiceField(
        choices=Torneo.EQUIPOS_CHOICES, coerce=int, label='Equipos que participan',
        widget=forms.RadioSelect)

    def __init__(self, *args, instancia=None, **kwargs):
        self.instancia = instancia
        if instancia is not None and not kwargs.get('data'):
            kwargs.setdefault('initial', {
                'nombre': instancia.liga.nombre,
                'descripcion': instancia.liga.descripcion,
                'fecha': instancia.fecha,
                'equipos': instancia.equipos,
            })
        super().__init__(*args, **kwargs)
        if instancia is not None and instancia.sorteado:
            campo = self.fields['equipos']
            campo.disabled = True
            campo.help_text = 'No se puede cambiar: el cuadro ya está sorteado.'

    def clean_equipos(self):
        equipos = self.cleaned_data['equipos']
        if self.instancia is not None and self.instancia.inscritos > equipos:
            raise forms.ValidationError(
                f'Ya hay {self.instancia.inscritos} equipos inscritos: no puedes '
                f'bajar el torneo a {equipos}.')
        return equipos

    @transaction.atomic
    def guardar(self, usuario):
        datos = self.cleaned_data
        if self.instancia is None:
            liga = Liga.objects.create(
                nombre=datos['nombre'], descripcion=datos['descripcion'],
                logo=datos['logo'] or None, portada=datos['portada'] or None,
                fecha_inicio=datos['fecha'], fecha_final=datos['fecha'])
            if usuario.role == Usuario.ROLE_ADMIN_LIGA:
                liga.administradores.add(usuario)
            Categoria.objects.create(
                liga=liga, nombre=CATEGORIA_UNICA, cupo_equipos=datos['equipos'],
                libre=True, vueltas=Categoria.VUELTA_UNICA,
                empate_define_penales=True, mini_liguilla=False)
            return Torneo.objects.create(
                liga=liga, fecha=datos['fecha'], equipos=datos['equipos'],
                creado_por=usuario)

        torneo = self.instancia
        liga = torneo.liga
        liga.nombre = datos['nombre']
        liga.descripcion = datos['descripcion']
        if datos['logo']:
            liga.logo = datos['logo']
        if datos['portada']:
            liga.portada = datos['portada']
        liga.fecha_inicio = liga.fecha_final = datos['fecha']
        liga.save()

        torneo.fecha = datos['fecha']
        torneo.equipos = datos['equipos']
        torneo.save()
        categoria = torneo.categoria
        categoria.cupo_equipos = datos['equipos']
        categoria.save(update_fields=['cupo_equipos'])
        return torneo


class TorneoEquipoForm(StyledFormMixin, forms.Form):
    CAMPOS_OBLIGATORIOS = ('nombre', 'entrenador')
    CAMPOS_CAPITALIZAR = ('nombre',)

    nombre = forms.CharField(max_length=140, label='Nombre del equipo')
    escudo = forms.ImageField(required=False, label='Escudo del equipo')
    entrenador = forms.ModelChoiceField(
        queryset=Usuario.objects.none(), label='Entrenador',
        help_text='Quién va a manejar este equipo en el torneo.')

    def __init__(self, torneo, usuario, *args, **kwargs):
        self.torneo = torneo
        super().__init__(*args, **kwargs)
        self.fields['entrenador'].queryset = Usuario.objects.entrenadores(usuario).order_by(
            'first_name', 'last_name', 'username')

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        if self.torneo.categoria.equipos.filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError(f'"{nombre}" ya está inscrito en este torneo.')
        return nombre

    def clean(self):
        datos = super().clean()
        if self.torneo.sorteado:
            raise forms.ValidationError(
                'El cuadro ya está sorteado: no se pueden inscribir más equipos.')
        if self.torneo.completo:
            raise forms.ValidationError(
                f'El torneo ya tiene sus {self.torneo.equipos} equipos.')
        return datos

    def guardar(self):
        categoria = self.torneo.categoria
        return Equipo.objects.create(
            nombre=self.cleaned_data['nombre'],
            escudo=self.cleaned_data['escudo'] or None,
            liga=self.torneo.liga,
            categoria=categoria,
            entrenador=self.cleaned_data['entrenador'])


def _con_estado(torneos):
    for torneo in torneos:
        torneo.motivo_sorteo = relampago.motivo_para_no_sortear(torneo)
    return torneos


_TEXTOS_PUBLICOS = {
    'titulo_pagina': 'Torneos relámpago',
    'seccion': 'Torneos',
    'encabezado': 'Torneos relámpago',
    'descripcion': 'Un solo día, eliminación directa. El empate se define en penales.',
    'vacio': 'Todavía no hay torneos relámpago.',
    'enlace_publico': False,
}

_TEXTOS_MIS_TORNEOS = {
    'titulo_pagina': 'Mis torneos',
    'seccion': 'Tablero · Torneos',
    'encabezado': 'Mis torneos relámpago',
    'descripcion': 'Los torneos que administras. Aquí los armas, los sorteas y cargas sus resultados.',
    'vacio': 'Todavía no tienes torneos. Crea el primero con el botón de arriba.',
    'enlace_publico': True,
}


def torneo_list(request):
    """El listado público: todos los torneos visibles.

    A propósito muestra los de todos, también al admin de liga: esta es la
    vitrina. La versión acotada a lo propio es `mis_torneos`, que es a donde
    lleva el tablero. Son dos entradas y no un `if` por rol adentro de esta,
    igual que en equipos y partidos.
    """
    return _listado(request, solo_propios=False)


@admin_liga_required
def mis_torneos(request):
    """El mismo listado, acotado a los torneos que uno administra."""
    return _listado(request, solo_propios=True)


def _listado(request, solo_propios):
    usuario = request.user
    es_admin = usuario.is_authenticated and (
        usuario.es_super_admin() or usuario.es_admin_liga())

    ambito = (torneos_administrados(usuario) if solo_propios
              else torneos_visibles(usuario))
    torneos = ambito.select_related('liga')
    administrados = set(
        torneos_administrados(usuario).values_list('pk', flat=True))
    for torneo in torneos:
        torneo.puede_administrar = torneo.pk in administrados

    motivo = motivo_para_no_crear(usuario) if es_admin else ''
    return render(request, 'torneos/torneo_list.html', {
        'torneos': _con_estado(list(torneos)),
        'puede_crear': es_admin and not motivo,
        'motivo_no_crear': motivo,
        'cuota': _cuota(usuario) if es_admin else None,
        'es_superadmin': usuario.is_authenticated and usuario.es_super_admin(),
        **(_TEXTOS_MIS_TORNEOS if solo_propios else _TEXTOS_PUBLICOS),
    })


def _cuota(usuario):
    """Cuantos torneos en curso tiene y cuantos puede tener."""
    if usuario.es_super_admin():
        return None
    return {
        'en_curso': torneos_administrados(usuario).en_curso().count(),
        'limite': usuario.limite_torneos,
    }


def torneo_detalle(request, pk):
    """El cuadro del torneo, con sus equipos y el estado del sorteo."""
    torneo = get_object_or_404(
        torneos_visibles(request.user).select_related('liga'), pk=pk)
    categoria = torneo.categoria
    puede_administrar = torneos_administrados(request.user).filter(pk=pk).exists()
    partidos = (Partido.objects
                .filter(categoria=categoria)
                .exclude(fase=Partido.FASE_REGULAR)
                .select_related('equipo_local', 'equipo_visitante', 'sede', 'ganador_penales')
                .order_by('fecha', 'orden'))
    return render(request, 'torneos/torneo_detalle.html', {
        'torneo': torneo,
        'equipos': categoria.equipos.select_related('entrenador').order_by('nombre'),
        'partidos': partidos,
        'cuadro': relampago.cuadro(torneo),
        'motivo_sorteo': relampago.motivo_para_no_sortear(torneo),
        'puede_administrar': puede_administrar,
        'es_superadmin': request.user.is_authenticated and request.user.es_super_admin(),
        'liga_actual': torneo.liga,
    })


def motivo_para_no_crear(usuario):
    """Por que este usuario no puede crear un torneo mas, o '' si puede.

    Los torneos terminados no ocupan lugar: el evento se jugo y el admin tiene
    que poder armar el siguiente sin esperar a que se borre el viejo. Es el
    mismo criterio que `limite_ligas`.
    """
    if usuario.es_super_admin():
        return ''
    en_curso = torneos_administrados(usuario).en_curso().count()
    if en_curso < usuario.limite_torneos:
        return ''
    return (
        f'Alcanzaste el límite de {usuario.limite_torneos} torneo(s) en curso que '
        f'puedes tener. Termina alguno o contacta al Administrador General.'
    )


@admin_liga_required
def torneo_create(request):
    modal = request.GET.get('modal') == '1'

    motivo = motivo_para_no_crear(request.user)
    if motivo:
        messages.error(request, motivo)
        if modal:
            return JsonResponse({'success': False, 'recargar': True})
        return redirect('mis-torneos')

    if request.method == 'POST':
        form = TorneoForm(request.POST, request.FILES)
        if form.is_valid():
            torneo = form.guardar(request.user)
            messages.success(
                request,
                f'Torneo "{torneo.nombre}" creado para el {torneo.fecha:%d/%m/%Y}. '
                f'Ahora inscribe sus {torneo.equipos} equipos.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('torneo-detalle', pk=torneo.pk)
    else:
        form = TorneoForm()

    contexto = {'form': form, 'title': 'Crear torneo relámpago'}
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'torneos/torneo_form.html', contexto)


@admin_liga_required
def torneo_edit(request, pk):
    torneo = get_object_or_404(torneos_administrados(request.user), pk=pk)
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = TorneoForm(request.POST, request.FILES, instancia=torneo)
        if form.is_valid():
            form.guardar(request.user)
            messages.success(request, 'Torneo actualizado.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('torneo-detalle', pk=torneo.pk)
    else:
        form = TorneoForm(instancia=torneo)

    contexto = {'form': form, 'title': f'Editar torneo: {torneo.nombre}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'torneos/torneo_form.html', contexto)


@admin_liga_required
def torneo_equipo_create(request, pk):
    torneo = get_object_or_404(torneos_administrados(request.user), pk=pk)
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = TorneoEquipoForm(torneo, request.user, request.POST, request.FILES)
        if form.is_valid():
            equipo = form.guardar()
            messages.success(
                request,
                f'"{equipo.nombre}" inscrito. Faltan {torneo.faltan} equipo(s).')
            if modal:
                return JsonResponse({'success': True})
            return redirect('torneo-detalle', pk=torneo.pk)
    else:
        form = TorneoEquipoForm(torneo, request.user)

    contexto = {'form': form, 'title': f'Inscribir equipo en {torneo.nombre}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'torneos/torneo_form.html', contexto)


@admin_liga_required
def torneo_sortear(request, pk):
    """Arma el cuadro al azar con los equipos inscritos."""
    torneo = get_object_or_404(torneos_administrados(request.user), pk=pk)
    if request.method == 'POST':
        motivo = relampago.motivo_para_no_sortear(torneo)
        if motivo:
            messages.error(request, motivo)
        else:
            creados = relampago.sortear(torneo)
            ronda = creados[0].get_fase_display().lower()
            messages.success(
                request,
                f'Cuadro sorteado: {len(creados)} partido(s) de {ronda}, '
                f'desde las {creados[0].fecha:%H:%M}. El empate se define en penales.')
    return redirect('torneo-detalle', pk=torneo.pk)


@superadmin_required
def torneo_delete(request, pk):
    """Elimina el torneo con todo lo suyo. Solo el Administrador General.

    Se lleva equipos, jugadores, partidos, las cuentas de sus entrenadores y su
    registro del palmarés: un torneo borrado no deja rastro en la vitrina.
    """
    torneo = get_object_or_404(Torneo, pk=pk)

    if torneo.terminado and not torneo.lista_para_eliminar:
        messages.error(
            request,
            f'"{torneo.nombre}" terminó hace poco y sigue en exhibición. '
            f'Podrás eliminarlo en {torneo.dias_en_vitrina} día(s).')
        return redirect('mis-torneos')

    categoria = torneo.categoria
    equipos = Equipo.objects.filter(liga=torneo.liga)
    entrenadores = entrenadores_sin_equipo_tras_borrar(equipos)
    premios = Palmares.objects.filter(categoria__liga=torneo.liga)

    arrastra = []
    for cantidad, etiqueta in (
        (equipos.count(), 'equipo(s)'),
        (Jugador.objects.filter(equipo__liga=torneo.liga).count(), 'jugador(es)'),
        (Partido.objects.filter(categoria=categoria).count(), 'partido(s)'),
        (entrenadores.count(), 'cuenta(s) de entrenador'),
        (premios.count(), 'registro(s) del palmarés'),
    ):
        if cantidad:
            arrastra.append(f'{cantidad} {etiqueta}')

    def limpiar():
        premios.delete()
        equipos.delete()
        entrenadores.delete()

    return vista_eliminar(
        request,
        instancia=torneo.liga,
        etiqueta=f'Torneo: {torneo.nombre}',
        url_listado='mis-torneos',
        mensaje_ok=f'Se eliminó el torneo "{torneo.nombre}" con todo su contenido, '
                   f'incluido su palmarés.',
        arrastra=arrastra,
        antes_de_borrar=limpiar,
    )
