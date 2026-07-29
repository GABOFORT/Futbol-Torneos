import itertools

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.partidos.models import Partido
from apps.usuarios.eliminar import vista_eliminar
from apps.usuarios.filtros import buscar, campo_texto, campo_opciones, hay_filtros
from apps.usuarios.permissions import admin_liga_required, ligas_administradas

from .forms import CategoriaForm
from .models import Categoria, Liga


def inicio(request):
    context = {
        'proximos_partidos': Partido.objects.filter(estado=Partido.ESTADO_PROGRAMADO)
            .select_related('categoria', 'categoria__liga', 'equipo_local', 'equipo_visitante').order_by('fecha')[:5],
        'ligas_activas': Liga.objects.filter(activa=True)[:6],
        # Antes se ordenaba por fecha_inicio, que era la fecha del torneo. Ese
        # campo ahora es un rango de edad, asi que se muestran las mas recientes.
        'categorias_vigentes': Categoria.objects.filter(activa=True).select_related('liga').order_by('-id')[:6],
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

    termino = request.GET.get('q', '')
    liga_id = request.GET.get('liga', '')
    edad = request.GET.get('edad', '')
    inscripcion = request.GET.get('inscripcion', '')

    categorias = buscar(categorias, termino, ['nombre', 'descripcion'])
    if liga_id.isdigit():
        categorias = categorias.filter(liga_id=int(liga_id))
    if edad:
        categorias = categorias.filter(limite_edad=edad)
    if inscripcion in ('1', '0'):
        categorias = categorias.filter(inscripcion_abierta=(inscripcion == '1'))

    categorias = categorias.select_related('liga').order_by('liga__nombre', 'nombre')

    # Solo las ligas que este usuario puede ver, para no ofrecer filtros vacios.
    ligas = ligas_administradas(user) if puede_administrar else Liga.objects.filter(activa=True)
    filtros = [
        campo_texto('q', 'Buscar', termino, 'Nombre o descripción de la categoría'),
        campo_opciones('liga', 'Liga', liga_id, ligas.order_by('nombre').values_list('id', 'nombre'), vacio='Todas'),
        campo_opciones('edad', 'Límite de edad', edad, Categoria.LIMITE_EDAD_CHOICES, vacio='Todos'),
        campo_opciones('inscripcion', 'Inscripción', inscripcion,
                       [('1', 'Abierta'), ('0', 'Cerrada')], vacio='Todas'),
    ]
    return render(request, 'torneos/categoria_list.html', {
        'categorias': categorias,
        'puede_administrar': puede_administrar,
        'filtros': filtros,
        'filtros_activos': hay_filtros(filtros),
        'total_resultados': categorias.count(),
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
def categoria_delete(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, liga__in=ligas_administradas(request.user))

    equipos = Equipo.objects.filter(categoria=categoria)
    arrastra = []
    for cantidad, etiqueta in (
        (equipos.count(), 'equipo(s)'),
        (Jugador.objects.filter(equipo__categoria=categoria).count(), 'jugador(es)'),
        (Partido.objects.filter(
            Q(categoria=categoria) | Q(equipo_local__categoria=categoria) | Q(equipo_visitante__categoria=categoria)
        ).distinct().count(), 'partido(s)'),
    ):
        if cantidad:
            arrastra.append(f'{cantidad} {etiqueta}')

    return vista_eliminar(
        request,
        instancia=categoria,
        etiqueta=f'Categoría: {categoria.nombre}',
        url_listado='categoria-list',
        mensaje_ok=f'Se eliminó la categoría "{categoria.nombre}" con todo su contenido.',
        arrastra=arrastra,
        # Igual que en liga: Equipo.categoria sigue siendo PROTECT y la cascada
        # se hace explicita solo desde esta vista.
        antes_de_borrar=equipos.delete,
    )


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
