import itertools

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.equipos.models import Equipo
from apps.partidos.models import Partido
from apps.usuarios.permissions import admin_liga_required, ligas_administradas

from .forms import CategoriaForm
from .models import Categoria, Liga


def inicio(request):
    context = {
        'proximos_partidos': Partido.objects.filter(estado=Partido.ESTADO_PROGRAMADO)
            .select_related('categoria', 'categoria__liga', 'equipo_local', 'equipo_visitante').order_by('fecha')[:5],
        'ligas_activas': Liga.objects.filter(activa=True)[:6],
        'categorias_vigentes': Categoria.objects.filter(activa=True).select_related('liga').order_by('-fecha_inicio')[:6],
    }
    return render(request, 'inicio.html', context)


def roles(request):
    return render(request, 'roles.html')


def categoria_list(request):
    user = request.user
    puede_administrar = user.is_authenticated and (user.is_superuser or user.role == user.ROLE_ADMIN_LIGA)
    if puede_administrar:
        categorias = Categoria.objects.filter(liga__in=ligas_administradas(user))
    else:
        categorias = Categoria.objects.filter(activa=True)
    categorias = categorias.select_related('liga').order_by('liga__nombre', 'nombre')
    return render(request, 'torneos/categoria_list.html', {
        'categorias': categorias,
        'puede_administrar': puede_administrar,
    })


@admin_liga_required
def categoria_create(request):
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = CategoriaForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada correctamente.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('categoria-list')
    else:
        form = CategoriaForm(request.user)

    context = {'form': form, 'title': 'Crear categoría'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'torneos/categoria_form.html', context)


@admin_liga_required
def categoria_edit(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, liga__in=ligas_administradas(request.user))
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = CategoriaForm(request.user, request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('categoria-list')
    else:
        form = CategoriaForm(request.user, instance=categoria)

    context = {'form': form, 'title': f'Editar categoría: {categoria.nombre}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'torneos/categoria_form.html', context)


@admin_liga_required
def categoria_cerrar_inscripcion(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, liga__in=ligas_administradas(request.user))
    if request.method == 'POST':
        categoria.inscripcion_abierta = False
        categoria.save(update_fields=['inscripcion_abierta'])
        messages.success(request, f'Inscripción cerrada para "{categoria.nombre}". Ya puedes generar los partidos.')
    return redirect('categoria-list')


@admin_liga_required
def categoria_reabrir_inscripcion(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, liga__in=ligas_administradas(request.user))
    if request.method == 'POST':
        categoria.inscripcion_abierta = True
        categoria.save(update_fields=['inscripcion_abierta'])
        messages.success(request, f'Inscripción reabierta para "{categoria.nombre}".')
    return redirect('categoria-list')


@admin_liga_required
def categoria_generar_partidos(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, liga__in=ligas_administradas(request.user))
    if request.method == 'POST':
        if categoria.inscripcion_abierta:
            messages.error(request, 'Primero cierra la inscripción de equipos para poder generar los partidos.')
        elif Partido.objects.filter(categoria=categoria).exists():
            messages.error(request, 'Ya se generaron los partidos de esta categoría.')
        else:
            equipos = list(Equipo.objects.filter(categoria=categoria))
            if len(equipos) < 2:
                messages.error(request, 'Necesitas al menos 2 equipos inscritos para generar partidos.')
            else:
                for local, visitante in itertools.combinations(equipos, 2):
                    Partido.objects.create(categoria=categoria, equipo_local=local, equipo_visitante=visitante)
                messages.success(request, f'Se generaron {len(equipos) * (len(equipos) - 1) // 2} partidos. Ahora asígnales fecha y hora.')
    return redirect('categoria-list')
