from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.partidos import liguilla
from apps.partidos.calendario import armar_jornadas
from apps.partidos.models import Partido
from apps.usuarios.eliminar import vista_eliminar
from apps.usuarios.filtros import buscar, campo_texto, campo_opciones, hay_filtros
from apps.usuarios.permissions import (
    admin_liga_required, ligas_administradas, ligas_visibles,
)

from . import busqueda, portada
from .forms import CategoriaForm
from .models import Categoria, Liga, Sede


def inicio(request):
    """La portada, pensada para quien entra sin cuenta.

    Un padre que quiere ver a que hora juega su hijo, como va su equipo y quien
    mete los goles. Todo lo que se muestra sale de `portada.py`, acotado a las
    ligas activas y calculado en una cantidad fija de consultas.

    Antes esta vista armaba tres listas sueltas a mano, y una de ellas ordenaba
    por fecha sin excluir los nulos: los partidos sin fecha aparecian como
    "proximos partidos".
    """
    return render(request, 'inicio.html', portada.todo())


def roles(request):
    return render(request, 'roles.html')


def buscar_vista(request):
    """El buscador del sitio. Publico, acotado por `ligas_visibles`.

    Una sola caja para jugador, equipo, torneo y cancha: quien busca no sabe en
    que tabla esta lo que quiere, escribe un nombre y espera resultados.
    """
    termino = request.GET.get('q', '')
    return render(request, 'busqueda.html', {
        'termino': termino,
        'hay_termino': busqueda.hay_termino(termino),
        'minimo': busqueda.MINIMO,
        'resultados': busqueda.buscar_todo(request.user, termino),
    })


def mis_equipos(request):
    """Los próximos partidos de los equipos que el visitante sigue.

    Devuelve **un fragmento**, no una página: lo pide `seguir.js` desde la
    portada con los ids que guardó el navegador y lo inserta arriba de todo.

    Se hace así, y no dibujando la lista con JavaScript, para que el HTML lo
    siga armando el servidor: el estilo, las fechas y los permisos quedan en un
    solo lugar y no hay que repetirlos en el navegador.

    El visitante no tiene cuenta, así que lo que sigue vive en su dispositivo.
    Acá no se guarda nada de nadie.
    """
    ids = request.GET.get('ids', '').split(',')
    return render(request, '_mis_equipos.html', {
        'bloques': portada.de_mis_equipos(ids),
    })


def sedes_vista(request):
    """El mapa de canchas de las ligas visibles.

    Las coordenadas ya estaban cargadas y el mapa construido para elegir la
    cancha de un partido, pero no habia ninguna pantalla que las mostrara todas
    juntas: quien viene a ver donde juega su hijo no tenia a donde ir.
    """
    sedes = (Sede.objects
             .filter(liga__in=ligas_visibles(request.user))
             .select_related('liga')
             .annotate(n_partidos=Count('partidos'))
             .order_by('liga__nombre', 'nombre'))
    return render(request, 'sedes.html', {
        'sedes': sedes,
        # El mapa arranca centrado en el promedio de las canchas cargadas, para
        # que no abra en medio del oceano ni haya que elegir una a dedo.
        'centro': _centro_de(sedes),
    })


def _centro_de(sedes):
    puntos = [(float(s.latitud), float(s.longitud)) for s in sedes]
    if not puntos:
        return None
    return {
        'lat': sum(p[0] for p in puntos) / len(puntos),
        'lon': sum(p[1] for p in puntos) / len(puntos),
    }


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

    # Los tres conteos van como anotacion y no consultando categoria por
    # categoria: son 13 categorias y serian 40 consultas para dibujar un boton.
    # Todos cuelgan de la misma relacion, asi que es un solo JOIN.
    categorias = categorias.select_related('liga').annotate(
        n_regulares=Count('partidos', filter=Q(partidos__fase=Partido.FASE_REGULAR)),
        n_pendientes=Count('partidos', filter=Q(partidos__fase=Partido.FASE_REGULAR) & ~Q(
            partidos__estado__in=[Partido.ESTADO_FINALIZADO, Partido.ESTADO_CANCELADO]
        )),
        n_liguilla=Count('partidos', filter=~Q(partidos__fase=Partido.FASE_REGULAR)),
    ).order_by('liga__nombre', 'nombre')

    categorias = list(categorias)
    equipos_por_categoria = dict(
        Equipo.objects.filter(categoria__in=categorias)
        .values('categoria').annotate(total=Count('id'))
        .values_list('categoria', 'total')
    )
    for categoria in categorias:
        categoria.liguilla_iniciada = categoria.n_liguilla > 0
        # La comprobacion de verdad la vuelve a hacer la vista que la inicia:
        # esto solo decide si vale la pena mostrar el boton.
        categoria.puede_iniciar_liguilla = (
            not categoria.liguilla_iniciada
            and categoria.n_regulares > 0
            and categoria.n_pendientes == 0
            and equipos_por_categoria.get(categoria.id, 0) >= 2
        )

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
        'total_resultados': len(categorias),
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
def categoria_iniciar_liguilla(request, pk):
    """Arranca el cuadro de eliminacion de la categoria.

    Solo cuando el torneo regular termino: la siembra sale de la tabla de
    posiciones, y con partidos por jugarse esa tabla todavia puede cambiar.
    """
    categoria = get_object_or_404(Categoria, pk=pk, liga__in=ligas_administradas(request.user))
    if request.method == 'POST':
        motivo = liguilla.motivo_para_no_iniciar(categoria)
        if motivo:
            messages.error(request, motivo)
        else:
            creados = liguilla.iniciar(categoria)
            fase = creados[0].get_fase_display().lower()
            messages.success(
                request,
                f'Liguilla iniciada en "{categoria.nombre}": {len(creados)} partido(s) de {fase} '
                f'con los mejores de la tabla. Ahora asígnales fecha y cancha.',
            )
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
            equipos = list(Equipo.objects.filter(categoria=categoria).order_by('nombre'))
            if len(equipos) < 2:
                messages.error(request, 'Necesitas al menos 2 equipos inscritos para generar partidos.')
            else:
                jornadas = armar_jornadas(equipos)
                partidos = [
                    Partido(categoria=categoria, jornada=numero, equipo_local=local, equipo_visitante=visitante)
                    for numero, encuentros in enumerate(jornadas, start=1)
                    for local, visitante in encuentros
                ]
                Partido.objects.bulk_create(partidos)
                aviso = f'Se generaron {len(partidos)} partidos en {len(jornadas)} jornadas.'
                if len(equipos) % 2:
                    aviso += ' Al ser una cantidad impar de equipos, uno descansa por jornada.'
                messages.success(request, aviso + ' Ahora asígnales fecha y hora.')
    return redirect('categoria-list')
