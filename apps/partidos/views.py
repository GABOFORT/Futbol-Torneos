from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.permissions import admin_liga_required, ligas_administradas

from .forms import PartidoFechaForm, ResultadoForm
from .models import Partido


def partido_list(request):
    partidos = Partido.objects.select_related('categoria', 'categoria__liga', 'equipo_local', 'equipo_visitante').order_by('fecha')
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        partidos = partidos.filter(categoria_id=categoria_id)

    puede_gestionar = request.user.is_authenticated and (
        request.user.is_superuser or request.user.role == request.user.ROLE_ADMIN_LIGA
    )
    return render(request, 'partidos/partido_list.html', {
        'partidos': partidos,
        'puede_gestionar': puede_gestionar,
        'categoria_id': categoria_id,
    })


@admin_liga_required
def partido_edit(request, pk):
    partido = get_object_or_404(Partido, pk=pk, categoria__liga__in=ligas_administradas(request.user))
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = PartidoFechaForm(request.POST, instance=partido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fecha y hora del partido actualizadas.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('partido-list')
    else:
        form = PartidoFechaForm(instance=partido)

    context = {'form': form, 'title': f'Fecha y hora: {partido}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'partidos/partido_form.html', context)


@admin_liga_required
def partido_resultado(request, pk):
    partido = get_object_or_404(Partido, pk=pk, categoria__liga__in=ligas_administradas(request.user))
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = ResultadoForm(request.POST, instance=partido)
        if form.is_valid():
            resultado = form.save(commit=False)
            resultado.estado = Partido.ESTADO_FINALIZADO
            resultado.save()
            messages.success(request, 'Resultado registrado.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('partido-list')
    else:
        form = ResultadoForm(instance=partido)

    context = {'form': form, 'title': f'Resultado: {partido}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'partidos/resultado_form.html', context)
