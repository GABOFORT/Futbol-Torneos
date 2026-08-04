from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.equipos.models import Equipo
from apps.torneos import palmares
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

    jugadores = list(equipo.jugadores.order_by('apellido', 'nombre'))

    # Los premios de la temporada, si la categoria ya termino: los del club van
    # en el encabezado y los individuales al lado de quien los gano. Una sola
    # consulta para toda la plantilla.
    premios = palmares.trofeos_por_categoria([equipo.categoria_id]).get(equipo.categoria_id, {})
    de_jugadores = premios.get('jugadores', {})
    for jugador in jugadores:
        jugador.trofeos = de_jugadores.get(f'{jugador.nombre} {jugador.apellido}', [])

    return render(request, 'jugadores/jugador_list.html', {
        'equipo': equipo,
        'jugadores': jugadores,
        'puede_gestionar': puede_gestionar,
        'trofeos_equipo': premios.get('equipos', {}).get(equipo.nombre, []),
    })


@login_required
def jugador_create(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if not _puede_gestionar(request.user, equipo):
        return HttpResponseForbidden('No tienes acceso a este equipo.')

    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = JugadorForm(equipo, request.POST, request.FILES)
        if form.is_valid():
            jugador = form.save(commit=False)
            jugador.equipo = equipo
            jugador.save()
            messages.success(request, 'Jugador agregado a la plantilla.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('jugador-list', equipo_id=equipo.pk)
    else:
        form = JugadorForm(equipo)

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
        form = JugadorForm(jugador.equipo, request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            form.save()
            messages.success(request, 'Jugador actualizado.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('jugador-list', equipo_id=jugador.equipo_id)
    else:
        form = JugadorForm(jugador.equipo, instance=jugador)

    context = {'form': form, 'title': f'Editar jugador: {jugador.nombre} {jugador.apellido}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'jugadores/jugador_form.html', context)


