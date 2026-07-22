from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.torneos.models import Liga
from apps.usuarios.permissions import admin_liga_required, ligas_administradas

from .forms import EquipoCreateForm, EquipoForm, EquipoFormacionForm
from .models import Equipo


def equipo_list(request):
    user = request.user

    if user.is_authenticated and user.role == user.ROLE_ENTRENADOR and not user.is_superuser:
        mis_equipos = Equipo.objects.filter(entrenador=user).select_related('liga', 'categoria').order_by('-fecha_creacion')
        return render(request, 'equipos/equipo_list.html', {
            'equipos': Equipo.objects.none(),
            'mis_equipos': mis_equipos,
            'puede_crear': False,
            'solo_mis_equipos': True,
            'ligas': Liga.objects.none(),
            'liga_id': None,
        })

    liga_id = request.GET.get('liga') or None
    directorio = Equipo.objects.select_related('liga', 'categoria', 'entrenador')
    if liga_id:
        directorio = directorio.filter(liga_id=liga_id)
    directorio = directorio.order_by('liga__nombre', 'categoria__nombre', 'nombre')

    return render(request, 'equipos/equipo_list.html', {
        'equipos': directorio,
        'mis_equipos': Equipo.objects.none(),
        'puede_crear': user.is_authenticated and (user.is_superuser or user.role == user.ROLE_ADMIN_LIGA),
        'solo_mis_equipos': False,
        'ligas': Liga.objects.filter(activa=True).order_by('nombre'),
        'liga_id': int(liga_id) if liga_id else None,
    })


@admin_liga_required
def equipo_create(request):
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = EquipoCreateForm(request.user, request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            entrenador = form.cleaned_data['entrenador']
            observaciones = form.cleaned_data['observaciones']
            categorias = form.cleaned_data['categorias']
            for categoria in categorias:
                Equipo.objects.create(
                    nombre=nombre,
                    liga=categoria.liga,
                    categoria=categoria,
                    entrenador=entrenador,
                    observaciones=observaciones,
                )
            messages.success(request, f'Se creó "{nombre}" en {categorias.count()} categoría(s).')
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
        form = form_class(request.user, request.POST, instance=equipo) if puede_administrar else form_class(request.POST, instance=equipo)
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

    return render(request, 'equipos/equipo_detail.html', {
        'equipo': equipo,
        'puede_editar': es_dueno or puede_administrar,
    })
