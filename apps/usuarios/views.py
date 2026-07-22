import datetime

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Usuario
from .forms import (
    UsuarioCreateForm, UsuarioUpdateForm, EntrenadorCreateForm, EntrenadorUpdateForm, LigaForm,
)
from .permissions import superadmin_required, admin_liga_required, ligas_administradas
from apps.torneos.models import Liga

MENSAJE_CUENTA_BLOQUEADA = 'Tu cuenta está bloqueada por falta de pago. Contacta al Administrador General.'


def _liga_bloqueada(user):
    if user.is_superuser or user.role != Usuario.ROLE_ADMIN_LIGA:
        return False
    return any(liga.esta_vencida for liga in user.ligas_administradas.all())


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'

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


def logout_view(request):
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
    return render(request, 'usuarios/dashboard_entrenador.html')


@superadmin_required
def usuarios_list(request):
    usuarios = Usuario.objects.order_by('username')
    return render(request, 'usuarios/usuarios_list.html', {'usuarios': usuarios})


@superadmin_required
def usuario_create(request):
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado correctamente.')
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
    entrenadores = Usuario.objects.filter(role=Usuario.ROLE_ENTRENADOR).order_by('username')
    return render(request, 'usuarios/entrenadores_list.html', {'entrenadores': entrenadores})


@admin_liga_required
def entrenador_create(request):
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = EntrenadorCreateForm(request.POST)
        if form.is_valid():
            form.save()
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
    entrenador = get_object_or_404(Usuario, pk=pk, role=Usuario.ROLE_ENTRENADOR)
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
    ligas = ligas_administradas(request.user).order_by('nombre')
    return render(request, 'usuarios/ligas_list.html', {
        'ligas': ligas,
        'es_superadmin': request.user.is_superuser,
    })


@admin_liga_required
def liga_create(request):
    user = request.user
    if not user.is_superuser and ligas_administradas(user).count() >= user.limite_ligas:
        messages.error(request, f'Alcanzaste el límite de {user.limite_ligas} liga(s) que puedes crear. Contacta al Administrador General.')
        return redirect('ligas-list')

    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = LigaForm(request.POST)
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
        form = LigaForm(request.POST, instance=liga)
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
def liga_registrar_pago(request, pk):
    liga = get_object_or_404(Liga, pk=pk)
    if request.method == 'POST':
        liga.fecha_pago = datetime.date.today()
        liga.save(update_fields=['fecha_pago'])
        messages.success(request, f'Pago registrado para "{liga.nombre}". Próximo vencimiento: {liga.fecha_vencimiento}.')
    return redirect('ligas-list')
