from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.partidos import altas
from apps.partidos.models import Partido

from apps.torneos.models import Categoria, Liga
from apps.usuarios.eliminar import vista_eliminar
from apps.usuarios.filtros import buscar, campo_texto, campo_opciones, hay_filtros
from apps.usuarios.permissions import (
    admin_liga_required, ligas_administradas, ligas_visibles,
    ligas_y_torneos_administrados, ligas_y_torneos_visibles,
)

from apps.torneos import palmares

from . import perfil
from .forms import EquipoCreateForm, EquipoForm, EquipoFormacionForm
from .models import Equipo

_TEXTOS_PUBLICOS = {
    'titulo_pagina': 'Equipos',
    'seccion': 'Equipos',
    'encabezado': 'Equipos por liga y categoría',
    'descripcion': 'Explora los equipos participantes en cada liga.',
    'vacio': 'Todavía no hay equipos registrados.',
    'enlace_publico': False,
}

_TEXTOS_MIS_LIGAS = {
    'titulo_pagina': 'Equipos de mis ligas',
    'seccion': 'Tablero · Equipos',
    'encabezado': 'Equipos de mis ligas',
    'descripcion': 'Los equipos de las ligas que administras.',
    'vacio': 'Todavía no hay equipos en tus ligas. Crea el primero con el botón de arriba.',
    'enlace_publico': True,
}


def equipo_list(request):
    """El directorio publico de equipos, acotado por `ligas_visibles`.

    **A proposito muestra los equipos de todas las ligas activas**, tambien al
    admin de liga: esta es la vitrina y el que mira decide que quiere ver.

    La version acotada a lo propio es `equipos_de_mis_ligas`, que es a donde
    lleva el tablero. Son dos entradas y no un `if` por rol adentro de esta:
    acotar la vitrina por rol dejaria al admin viendo menos que un visitante sin
    cuenta, que fue el fallo corregido el 12/08/2026.
    """
    return _directorio(request, solo_propias=False)


@admin_liga_required
def equipos_de_mis_ligas(request):
    """El mismo directorio, acotado a las ligas que uno administra.

    Es la entrada desde el tablero, donde la pregunta no es "que puedo mirar"
    sino "que administro". Sin esto, un admin que lleva una sola liga abria su
    pantalla de trabajo y recibia los equipos de TODAS las ligas activas: en
    la practica, la gran mayoria de las fichas eran ajenas, y un admin de una
    liga recien creada no veia ni una sola propia.

    Reusa la vista y la plantilla: lo unico que cambia es de que conjunto de
    ligas se parte, y que los filtros se arman sobre ese mismo conjunto.
    """
    return _directorio(request, solo_propias=True)


def _directorio(request, solo_propias):
    user = request.user

    if not solo_propias and user.is_authenticated and user.role == user.ROLE_ENTRENADOR and not user.is_superuser:
        mis_equipos = list(
            Equipo.objects.filter(entrenador=user).select_related('liga', 'categoria').order_by('-fecha_creacion')
        )
        premios = palmares.trofeos_por_categoria({e.categoria_id for e in mis_equipos})
        for equipo in mis_equipos:
            equipo.trofeos = premios.get(equipo.categoria_id, {}).get('equipos', {}).get(equipo.nombre, [])
        return render(request, 'equipos/equipo_list.html', {
            'equipos': Equipo.objects.none(),
            'mis_equipos': mis_equipos,
            'puede_crear': False,
            'solo_mis_equipos': True,
            'ligas': Liga.objects.none(),
            'liga_id': None,
            **_TEXTOS_PUBLICOS,
        })

    ambito = ligas_administradas(user) if solo_propias else ligas_visibles(user)
    puede_administrar = user.is_authenticated and (user.is_superuser or user.role == user.ROLE_ADMIN_LIGA)

    termino = request.GET.get('q', '')
    liga_id = request.GET.get('liga', '')
    categoria_id = request.GET.get('categoria', '')

    directorio = Equipo.objects.filter(liga__in=ambito).select_related('liga', 'categoria', 'entrenador')
    directorio = buscar(directorio, termino, [
        'nombre', 'entrenador__first_name', 'entrenador__last_name', 'entrenador__username',
    ])
    if liga_id.isdigit():
        directorio = directorio.filter(liga_id=int(liga_id))
    if categoria_id.isdigit():
        directorio = directorio.filter(categoria_id=int(categoria_id))
    directorio = list(directorio.order_by('liga__nombre', 'categoria__nombre', 'nombre'))

    premios = palmares.trofeos_por_categoria({e.categoria_id for e in directorio})
    for equipo in directorio:
        equipo.trofeos = premios.get(equipo.categoria_id, {}).get('equipos', {}).get(equipo.nombre, [])

    categorias = Categoria.objects.filter(liga__in=ambito)
    if liga_id.isdigit():
        categorias = categorias.filter(liga_id=int(liga_id))

    filtros = [
        campo_texto('q', 'Buscar', termino, 'Nombre del equipo o del entrenador'),
        campo_opciones('liga', 'Liga', liga_id, ambito.order_by('nombre').values_list('id', 'nombre'), vacio='Todas'),
        campo_opciones('categoria', 'Categoría', categoria_id,
                       categorias.order_by('nombre').values_list('id', 'nombre'), vacio='Todas'),
    ]
    return render(request, 'equipos/equipo_list.html', {
        'equipos': directorio,
        'mis_equipos': Equipo.objects.none(),
        'puede_crear': puede_administrar,
        'solo_mis_equipos': False,
        'puede_filtrar': True,
        'filtros': filtros,
        'filtros_activos': hay_filtros(filtros),
        'total_resultados': len(directorio),
        **(_TEXTOS_MIS_LIGAS if solo_propias else _TEXTOS_PUBLICOS),
    })


@admin_liga_required
def equipo_create(request):
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = EquipoCreateForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            escudo = form.cleaned_data['escudo']
            entrenador = form.cleaned_data['entrenador']
            observaciones = form.cleaned_data['observaciones']
            categorias = form.cleaned_data['categorias']
            avisos = []
            for categoria in categorias:
                equipo = Equipo.objects.create(
                    nombre=nombre,
                    escudo=escudo,
                    liga=categoria.liga,
                    categoria=categoria,
                    entrenador=entrenador,
                    observaciones=observaciones,
                )
                if altas.hay_calendario(categoria):
                    aviso = altas.resumen(altas.agregar(categoria, equipo))
                    if aviso:
                        avisos.append(f'{categoria.nombre}: {aviso}')
            messages.success(request, f'Se creó "{nombre}" en {categorias.count()} categoría(s).')
            for aviso in avisos:
                messages.info(request, aviso)
            if modal:
                return JsonResponse({'success': True})
            return redirect('equipo-list')
    else:
        form = EquipoCreateForm(request.user)

    context = {'form': form, 'title': 'Crear equipo'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'equipos/equipo_form.html', context)


@login_required
def equipo_edit(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    user = request.user
    es_dueno = equipo.entrenador_id == user.id
    puede_administrar = user.is_superuser or (
        user.role == user.ROLE_ADMIN_LIGA and equipo.liga_id in ligas_administradas(user).values_list('id', flat=True)
    )
    if not (puede_administrar or es_dueno):
        return HttpResponseForbidden('No tienes acceso a este equipo.')

    modal = request.GET.get('modal') == '1'
    form_class = EquipoForm if puede_administrar else EquipoFormacionForm

    if request.method == 'POST':
        form = form_class(request.user, request.POST, request.FILES, instance=equipo) if puede_administrar else form_class(request.POST, request.FILES, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipo actualizado correctamente.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('equipo-list')
    else:
        form = form_class(request.user, instance=equipo) if puede_administrar else form_class(instance=equipo)

    context = {'form': form, 'title': f'Editar equipo: {equipo.nombre}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'equipos/equipo_form.html', context)


@admin_liga_required
def equipo_delete(request, pk):
    equipo = get_object_or_404(
        Equipo, pk=pk, liga__in=ligas_y_torneos_administrados(request.user))

    jugadores = equipo.jugadores.count()
    partidos = equipo.partidos_local.count() + equipo.partidos_visitante.count()
    arrastra = []
    if jugadores:
        arrastra.append(f'{jugadores} jugador(es) de la plantilla')
    if partidos:
        arrastra.append(f'{partidos} partido(s) con sus resultados')

    return vista_eliminar(
        request,
        instancia=equipo,
        etiqueta=f'Equipo: {equipo.nombre} ({equipo.categoria.nombre})',
        url_listado='equipo-list',
        mensaje_ok=f'Se eliminó el equipo "{equipo.nombre}".',
        arrastra=arrastra,
    )


def equipo_perfil(request, pk):
    """El perfil del equipo, para abrirse en el modal desde cualquier pantalla.

    De solo lectura y acotado por `ligas_visibles`, con el mismo criterio que la
    ficha de partido: el admin de liga llega a las suyas, y el entrenador y el
    publico a las ligas activas.

    A diferencia de `equipo_detail`, al entrenador no se lo limita a su propio
    equipo. Se abre pulsando un escudo en el calendario o en la tabla, casi
    siempre el de un rival, y ademas no muestra nada que la ficha de partido no
    muestre ya: dejarlo afuera lo dejaba viendo menos que un visitante sin cuenta.
    """
    equipo = get_object_or_404(
        Equipo.objects.select_related('liga', 'categoria', 'entrenador')
        .filter(liga__in=ligas_y_torneos_visibles(request.user)),
        pk=pk,
    )
    return render(request, 'equipos/_perfil_modal.html', perfil.armar(equipo))


def equipo_detail(request, pk):
    equipo = get_object_or_404(
        Equipo.objects.select_related('liga', 'categoria', 'entrenador').prefetch_related('jugadores'), pk=pk
    )
    user = request.user
    es_dueno = user.is_authenticated and equipo.entrenador_id == user.id
    puede_administrar = user.is_authenticated and (
        user.is_superuser
        or (user.role == user.ROLE_ADMIN_LIGA and equipo.liga_id in ligas_administradas(user).values_list('id', flat=True))
    )

    if user.is_authenticated and user.role == user.ROLE_ENTRENADOR and not user.is_superuser and not es_dueno:
        return HttpResponseForbidden('No puedes ver equipos de otras ligas.')

    premios = palmares.trofeos_por_categoria([equipo.categoria_id]).get(equipo.categoria_id, {})
    de_jugadores = premios.get('jugadores', {})
    jugadores = list(equipo.jugadores.all())
    for jugador in jugadores:
        jugador.trofeos = de_jugadores.get(f'{jugador.nombre} {jugador.apellido}', [])

    de_este = Partido.objects.filter(
        Q(equipo_local=equipo) | Q(equipo_visitante=equipo)
    ).select_related('categoria', 'equipo_local', 'equipo_visitante', 'sede')

    return render(request, 'equipos/equipo_detail.html', {
        'equipo': equipo,
        'proximos': de_este.filter(
            estado__in=Partido.ESTADOS_POR_JUGARSE, fecha__gte=timezone.now()
        ).order_by('fecha')[:5],
        'ultimos': de_este.filter(
            estado=Partido.ESTADO_FINALIZADO
        ).order_by('-fecha')[:5],
        'jugadores': jugadores,
        'trofeos_equipo': premios.get('equipos', {}).get(equipo.nombre, []),
        'puede_editar': es_dueno or puede_administrar,
        'puede_administrar': puede_administrar,
    })
