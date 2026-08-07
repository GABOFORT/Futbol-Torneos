import datetime

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Usuario
from .forms import (
    UsuarioCreateForm, UsuarioUpdateForm, EntrenadorCreateForm, EntrenadorUpdateForm, LigaForm,
)
from django.db.models import Q

from .eliminar import entrenadores_sin_equipo_tras_borrar, vista_eliminar
from .filtros import buscar, campo_texto, campo_opciones, hay_filtros
from .permissions import superadmin_required, admin_liga_required, ligas_administradas
from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.partidos.models import Partido
from apps.torneos import palmares
from apps.torneos.models import Liga

MENSAJE_CUENTA_BLOQUEADA = 'Tu cuenta está bloqueada por falta de pago. Contacta al Administrador General.'


def _liga_bloqueada(user):
    if user.is_superuser or user.role != Usuario.ROLE_ADMIN_LIGA:
        return False
    return any(liga.esta_vencida for liga in user.ligas_administradas.all())


def _destino_seguro(request):
    """A donde mandar al usuario despues de entrar.

    El 'next' llega por la URL, asi que cualquiera puede armar un enlace con un
    dominio ajeno: sin este filtro el login terminaria redirigiendo a un sitio
    externo (por ejemplo una copia falsa que vuelve a pedir la contrasena).
    """
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return 'dashboard'


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = _destino_seguro(request)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if _liga_bloqueada(user):
                messages.error(request, MENSAJE_CUENTA_BLOQUEADA)
            else:
                login(request, user)
                return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'usuarios/login.html', {'next': next_url})


@require_POST
def logout_view(request):
    # Solo POST: por GET, cualquier sitio externo podria cerrar la sesion con
    # un <img src="...\/logout\/">, sin que el usuario haga nada.
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user
    if _liga_bloqueada(user):
        logout(request)
        messages.error(request, MENSAJE_CUENTA_BLOQUEADA)
        return redirect('login')
    if user.role == Usuario.ROLE_SUPERADMIN or user.is_superuser:
        return render(request, 'usuarios/dashboard_superadmin.html')
    if user.role == Usuario.ROLE_ADMIN_LIGA:
        ligas = user.ligas_administradas.all()
        aviso_pago = None
        for liga in ligas:
            dias = liga.dias_para_vencer
            if dias is not None and dias <= 7:
                aviso_pago = liga
                break
        return render(request, 'usuarios/dashboard_adminliga.html', {'aviso_pago': aviso_pago})

    # Si alguna de sus categorias termino y su equipo subio al podio, lo primero
    # que ve al entrar es la felicitacion con el trofeo.
    return render(request, 'usuarios/dashboard_entrenador.html', {
        'festejos': palmares.premios_del_entrenador(user),
    })


@superadmin_required
def usuarios_list(request):
    termino = request.GET.get('q', '')
    rol = request.GET.get('rol', '')

    # prefetch: sin esto la tabla dispara dos consultas por usuario para armar
    # las columnas de liga y equipo, o sea mas de 400 con la lista completa.
    usuarios = Usuario.objects.prefetch_related(
        'ligas_administradas', 'equipos__liga'
    ).order_by('username')
    usuarios = buscar(usuarios, termino, [
        'username', 'first_name', 'last_name', 'email',
        'equipos__nombre', 'equipos__liga__nombre', 'ligas_administradas__nombre',
    ])
    if rol:
        usuarios = usuarios.filter(role=rol)

    filtros = [
        campo_texto('q', 'Buscar', termino, 'Usuario, nombre, correo, equipo o liga'),
        campo_opciones('rol', 'Rol', rol, Usuario.ROLE_CHOICES, vacio='Todos los roles'),
    ]
    return render(request, 'usuarios/usuarios_list.html', {
        'usuarios': usuarios,
        'filtros': filtros,
        'filtros_activos': hay_filtros(filtros),
        'total_resultados': usuarios.count(),
    })


@superadmin_required
def usuario_create(request):
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            # Queda el rastro de quien dio de alta la cuenta, igual que con los
            # entrenadores. Sin esto los usuarios creados desde aca quedaban
            # huerfanos y no se sabia quien los habia agregado.
            usuario.creado_por = request.user
            usuario.save()
            messages.success(request, f'{usuario.get_role_display()} creado correctamente.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('usuarios-list')
    else:
        form = UsuarioCreateForm()

    if modal:
        return render(request, 'usuarios/modal_form.html', {'form': form, 'title': 'Crear usuario'})

    return render(request, 'usuarios/usuario_form.html', {'form': form, 'title': 'Crear usuario'})


@superadmin_required
def usuario_edit(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = UsuarioUpdateForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario actualizado correctamente.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('usuarios-list')
    else:
        form = UsuarioUpdateForm(instance=usuario)

    if modal:
        return render(request, 'usuarios/modal_form.html', {'form': form, 'title': f'Editar usuario: {usuario.username}'})

    return render(request, 'usuarios/usuario_form.html', {'form': form, 'title': f'Editar usuario: {usuario.username}'})


@admin_liga_required
def entrenadores_list(request):
    termino = request.GET.get('q', '')
    liga_id = request.GET.get('liga', '')

    # prefetch: la tabla muestra liga y equipo de cada uno, y sin esto seria
    # una consulta por fila.
    entrenadores = Usuario.objects.entrenadores(request.user).prefetch_related(
        'equipos__liga'
    ).order_by('first_name', 'last_name', 'username')
    entrenadores = buscar(entrenadores, termino, [
        'username', 'first_name', 'last_name', 'phone', 'email',
        'equipos__nombre', 'equipos__liga__nombre',
    ])
    if liga_id.isdigit():
        # Un entrenador no cuelga de una liga: se llega a ella por sus equipos.
        entrenadores = entrenadores.filter(equipos__liga_id=int(liga_id)).distinct()

    ligas = ligas_administradas(request.user)
    filtros = [
        campo_texto('q', 'Buscar', termino, 'Nombre, usuario, teléfono, equipo o liga'),
        campo_opciones('liga', 'Liga', liga_id, ligas.order_by('nombre').values_list('id', 'nombre'), vacio='Todas'),
    ]
    return render(request, 'usuarios/entrenadores_list.html', {
        'entrenadores': entrenadores,
        'filtros': filtros,
        'filtros_activos': hay_filtros(filtros),
        'total_resultados': entrenadores.count(),
    })


@admin_liga_required
def entrenador_create(request):
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = EntrenadorCreateForm(request.POST)
        if form.is_valid():
            entrenador = form.save(commit=False)
            # Queda registrado quien lo dio de alta: es lo que despues permite
            # que cada admin de liga vea unicamente a los suyos.
            entrenador.creado_por = request.user
            entrenador.save()
            messages.success(request, 'Entrenador creado correctamente.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('entrenadores-list')
    else:
        form = EntrenadorCreateForm()

    if modal:
        return render(request, 'usuarios/modal_form.html', {'form': form, 'title': 'Crear entrenador'})

    return render(request, 'usuarios/usuario_form.html', {'form': form, 'title': 'Crear entrenador'})


@admin_liga_required
def entrenador_edit(request, pk):
    # El manager acota a los entrenadores que este usuario puede administrar,
    # asi que un admin de liga no llega a los de otro ni forzando la URL.
    entrenador = get_object_or_404(Usuario.objects.entrenadores(request.user), pk=pk)
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = EntrenadorUpdateForm(request.POST, instance=entrenador)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entrenador actualizado correctamente.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('entrenadores-list')
    else:
        form = EntrenadorUpdateForm(instance=entrenador)

    context = {'form': form, 'title': f'Editar entrenador: {entrenador.username}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'usuarios/usuario_form.html', context)


@admin_liga_required
def ligas_list(request):
    termino = request.GET.get('q', '')
    activa = request.GET.get('activa', '')

    ligas = ligas_administradas(request.user).order_by('cerrada', 'nombre')
    ligas = buscar(ligas, termino, ['nombre', 'descripcion'])
    if activa in ('1', '0'):
        ligas = ligas.filter(activa=(activa == '1'))

    filtros = [
        campo_texto('q', 'Buscar', termino, 'Nombre o descripción de la liga'),
        campo_opciones('activa', 'Estado', activa, [('1', 'Activa'), ('0', 'Inactiva')], vacio='Todos'),
    ]
    return render(request, 'usuarios/ligas_list.html', {
        'ligas': ligas,
        # es_super_admin() y no is_superuser: contempla tambien al usuario con
        # role='superadmin' que no tiene marcada la casilla de superusuario.
        'es_superadmin': request.user.es_super_admin(),
        'filtros': filtros,
        'filtros_activos': hay_filtros(filtros),
        'total_resultados': ligas.count(),
    })


@admin_liga_required
def liga_create(request):
    user = request.user
    modal = request.GET.get('modal') == '1'
    # Las ligas concluidas no ocupan lugar: la temporada termino y el admin
    # tiene que poder arrancar la siguiente sin esperar a que se borre la vieja.
    en_curso = ligas_administradas(user).filter(cerrada=False).count()
    if not user.is_superuser and en_curso >= user.limite_ligas:
        messages.error(request, f'Alcanzaste el límite de {user.limite_ligas} liga(s) en curso que puedes tener. Contacta al Administrador General.')
        if modal:
            # Un redirect aca devolveria la pagina entera y el modal la inyectaria
            # sobre si misma. Se le pide recargar para que solo salga el mensaje.
            return JsonResponse({'success': False, 'recargar': True})
        return redirect('ligas-list')

    if request.method == 'POST':
        form = LigaForm(request.POST, request.FILES)
        if form.is_valid():
            liga = form.save()
            if not user.is_superuser and user.role == Usuario.ROLE_ADMIN_LIGA:
                liga.administradores.add(user)
            messages.success(request, 'Liga creada correctamente.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('ligas-list')
    else:
        form = LigaForm()

    if modal:
        return render(request, 'usuarios/modal_form.html', {'form': form, 'title': 'Crear liga'})

    return render(request, 'usuarios/liga_form.html', {'form': form, 'title': 'Crear liga'})


@admin_liga_required
def liga_edit(request, pk):
    liga = get_object_or_404(ligas_administradas(request.user), pk=pk)
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = LigaForm(request.POST, request.FILES, instance=liga)
        if form.is_valid():
            form.save()
            messages.success(request, 'Liga actualizada correctamente.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('ligas-list')
    else:
        form = LigaForm(instance=liga)

    if modal:
        return render(request, 'usuarios/modal_form.html', {'form': form, 'title': f'Editar liga: {liga.nombre}'})

    return render(request, 'usuarios/liga_form.html', {'form': form, 'title': f'Editar liga: {liga.nombre}'})


@superadmin_required
def usuario_delete(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)

    bloqueo = ''
    arrastra = []
    equipos = usuario.equipos.count()
    if usuario.pk == request.user.pk:
        bloqueo = 'No puedes eliminar tu propia cuenta mientras la estás usando.'
    elif equipos:
        # Equipo.entrenador es PROTECT: sin este aviso reventaria el borrado.
        bloqueo = (
            f'Este usuario es entrenador de {equipos} equipo(s). Asigna esos equipos a otro '
            f'entrenador o eliminalos antes de borrar la cuenta.'
        )
    else:
        ligas = usuario.ligas_administradas.count()
        if ligas:
            # Es M2M: se desvincula, las ligas siguen existiendo.
            arrastra.append(f'Dejará de administrar {ligas} liga(s), que no se eliminan')

    return vista_eliminar(
        request,
        instancia=usuario,
        etiqueta=f'Usuario: {usuario.nombre_visible} ({usuario.rol_visible})',
        url_listado='usuarios-list',
        mensaje_ok=f'Se eliminó el usuario "{usuario.username}".',
        arrastra=arrastra,
        bloqueo=bloqueo,
    )


@superadmin_required
def liga_delete(request, pk):
    # Eliminar ligas es solo del superadmin. El admin de liga administra la suya
    # y puede borrar sus categorias y equipos, pero no la liga en si.
    liga = get_object_or_404(Liga, pk=pk)

    # Una liga concluida se exhibe un mes antes de poder borrarse: es el tiempo
    # que la gente tiene para ver como termino. El palmares no se va con ella,
    # asi que el campeon queda registrado igual.
    if liga.cerrada and not liga.lista_para_eliminar:
        messages.error(
            request,
            f'"{liga.nombre}" concluyó hace poco y sigue en exhibición. '
            f'Podrás eliminarla en {liga.dias_en_vitrina} día(s).',
        )
        return redirect('ligas-list')

    equipos = Equipo.objects.filter(liga=liga)
    # Los entrenadores se van con la liga: dirigian ahi y no les queda nada que
    # dirigir. Se calcula antes de borrar nada, porque despues ya no se sabe
    # quienes eran. Los que ademas dirigen en otra liga se conservan.
    entrenadores = entrenadores_sin_equipo_tras_borrar(equipos)

    arrastra = []
    for cantidad, etiqueta in (
        (liga.categorias.count(), 'categoría(s)'),
        (equipos.count(), 'equipo(s)'),
        (Jugador.objects.filter(equipo__liga=liga).count(), 'jugador(es)'),
        (Partido.objects.filter(
            Q(categoria__liga=liga) | Q(equipo_local__liga=liga) | Q(equipo_visitante__liga=liga)
        ).distinct().count(), 'partido(s)'),
        (entrenadores.count(), 'cuenta(s) de entrenador'),
    ):
        if cantidad:
            arrastra.append(f'{cantidad} {etiqueta}')

    def limpiar():
        # El orden importa: Equipo.entrenador es PROTECT, asi que los equipos
        # tienen que irse antes que las cuentas.
        equipos.delete()
        entrenadores.delete()

    return vista_eliminar(
        request,
        instancia=liga,
        etiqueta=f'Liga: {liga.nombre}',
        url_listado='ligas-list',
        mensaje_ok=f'Se eliminó la liga "{liga.nombre}" con todo su contenido.',
        arrastra=arrastra,
        # Equipo.liga es PROTECT y se deja asi a proposito: protege contra
        # borrados accidentales desde el admin o un script. La cascada se hace
        # explicita solo aca, borrando los equipos antes que la liga.
        antes_de_borrar=limpiar,
    )


@superadmin_required
def liga_registrar_pago(request, pk):
    liga = get_object_or_404(Liga, pk=pk)
    if request.method == 'POST':
        liga.fecha_pago = datetime.date.today()
        liga.save(update_fields=['fecha_pago'])
        messages.success(request, f'Pago registrado para "{liga.nombre}". Próximo vencimiento: {liga.fecha_vencimiento}.')
    return redirect('ligas-list')
