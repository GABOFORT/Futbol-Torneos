from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.equipos.models import Equipo
from apps.usuarios.permissions import ligas_administradas

from .forms import JugadorForm
from .models import Jugador


def jugadores_index(request):
    return redirect('equipo-list')


def _puede_gestionar(user, equipo):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == user.ROLE_SUPERADMIN:
        return True
    if user.role == user.ROLE_ADMIN_LIGA:
        return equipo.liga_id in ligas_administradas(user).values_list('id', flat=True)
    return equipo.entrenador_id == user.id


def jugador_list(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    user = request.user
    puede_gestionar = _puede_gestionar(user, equipo)

    if user.is_authenticated and user.role == user.ROLE_ENTRENADOR and not user.is_superuser and not puede_gestionar:
        return HttpResponseForbidden('No puedes ver la plantilla de otro equipo.')

    jugadores = equipo.jugadores.order_by('apellido', 'nombre')
    return render(request, 'jugadores/jugador_list.html', {
        'equipo': equipo,
        'jugadores': jugadores,
        'puede_gestionar': puede_gestionar,
    })


@login_required
def jugador_create(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if not _puede_gestionar(request.user, equipo):
        return HttpResponseForbidden('No tienes acceso a este equipo.')

    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES)
        if form.is_valid():
            jugador = form.save(commit=False)
            jugador.equipo = equipo
            jugador.save()
            messages.success(request, 'Jugador agregado a la plantilla.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('jugador-list', equipo_id=equipo.pk)
    else:
        form = JugadorForm()

    context = {'form': form, 'title': f'Agregar jugador: {equipo.nombre}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'jugadores/jugador_form.html', context)


@login_required
def jugador_edit(request, pk):
    jugador = get_object_or_404(Jugador.objects.select_related('equipo'), pk=pk)
    if not _puede_gestionar(request.user, jugador.equipo):
        return HttpResponseForbidden('No tienes acceso a este jugador.')

    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            form.save()
            messages.success(request, 'Jugador actualizado.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('jugador-list', equipo_id=jugador.equipo_id)
    else:
        form = JugadorForm(instance=jugador)

    context = {'form': form, 'title': f'Editar jugador: {jugador.nombre} {jugador.apellido}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'jugadores/jugador_form.html', context)


@login_required
def jugador_estado(request, pk, estado):
    jugador = get_object_or_404(Jugador.objects.select_related('equipo'), pk=pk)
    if not _puede_gestionar(request.user, jugador.equipo):
        return HttpResponseForbidden('No tienes acceso a este jugador.')
    if estado not in dict(Jugador.ESTADO_CHOICES):
        return HttpResponseForbidden('Estado inválido.')

    if request.method == 'POST':
        jugador.estado = estado
        jugador.activo = estado == Jugador.ESTADO_ACTIVO
        jugador.save(update_fields=['estado', 'activo'])
        messages.success(request, f'Estado de {jugador.nombre} actualizado a {jugador.get_estado_display()}.')
    return redirect('jugador-list', equipo_id=jugador.equipo_id)
