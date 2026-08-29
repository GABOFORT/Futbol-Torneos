from django.shortcuts import get_object_or_404
from django.urls import path

from apps.usuarios.rutas import canonica

from . import patrocinadores, torneos, views
from .models import Categoria, Torneo

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('torneos/', torneos.torneo_list, name='torneo-list'),
    path('torneos/mis-torneos/', torneos.mis_torneos, name='mis-torneos'),
    path('torneos/crear/', torneos.torneo_create, name='torneo-create'),
    path('torneos/<int:pk>/',
         canonica(lambda pk: get_object_or_404(
             Torneo.objects.select_related('liga'), pk=pk)),
         name='torneo-detalle-id'),
    path('torneos/<int:pk>/editar/', torneos.torneo_edit, name='torneo-edit'),
    path('torneos/<int:pk>/eliminar/', torneos.torneo_delete, name='torneo-delete'),
    path('torneos/<int:pk>/equipos/crear/', torneos.torneo_equipo_create, name='torneo-equipo-create'),
    path('torneos/<int:pk>/sortear/', torneos.torneo_sortear, name='torneo-sortear'),
    path('torneos/<int:pk>/categorias/crear/', torneos.torneo_categoria_create, name='torneo-categoria-create'),
    path('torneos/<int:pk>/categorias/<int:categoria_pk>/',
         canonica(lambda pk, categoria_pk: get_object_or_404(
             Categoria.objects.select_related('liga'),
             pk=categoria_pk, liga__torneo__pk=pk)),
         name='torneo-categoria-id'),
    path('torneos/<int:pk>/categorias/<int:categoria_pk>/editar/', torneos.torneo_categoria_edit, name='torneo-categoria-edit'),
    path('torneos/<int:pk>/categorias/<int:categoria_pk>/eliminar/', torneos.torneo_categoria_delete, name='torneo-categoria-delete'),
    path('torneos/<int:pk>/categorias/<int:categoria_pk>/generar/', torneos.torneo_categoria_generar, name='torneo-categoria-generar'),
    path('torneos/<int:pk>/categorias/<int:categoria_pk>/liguilla/', torneos.torneo_categoria_sembrar, name='torneo-categoria-sembrar'),
    path('torneos/<int:pk>/categorias/<int:categoria_pk>/equipos/crear/', torneos.torneo_equipo_create, name='torneo-categoria-equipo-create'),
    path('torneos/<int:pk>/categorias/<int:categoria_pk>/equipos/<int:equipo_pk>/editar/', torneos.torneo_equipo_edit, name='torneo-equipo-edit'),
    path('torneos/<slug:torneo>/', torneos.torneo_detalle, name='torneo-detalle'),
    path('torneos/<slug:torneo>/<slug:categoria>/', torneos.torneo_categoria, name='torneo-categoria'),
    path('aliados/<int:pk>/', patrocinadores.ficha, name='patrocinador-ficha'),
    path('ligas/<int:pk>/aliados/', patrocinadores.lista, name='patrocinadores'),
    path('ligas/<int:pk>/aliados/crear/', patrocinadores.crear, name='patrocinador-create'),
    path('ligas/<int:pk>/aliados/<int:patrocinador_pk>/editar/', patrocinadores.editar, name='patrocinador-edit'),
    path('ligas/<int:pk>/aliados/<int:patrocinador_pk>/eliminar/', patrocinadores.eliminar, name='patrocinador-delete'),
    path('roles/', views.roles, name='roles'),
    path('buscar/', views.buscar_vista, name='buscar'),
    path('sedes/', views.sedes_vista, name='sedes'),
    path('mis-equipos/', views.mis_equipos, name='mis-equipos'),
    path('categorias/', views.categoria_list, name='categoria-list'),
    path('categorias/crear/', views.categoria_create, name='categoria-create'),
    path('categorias/<int:pk>/editar/', views.categoria_edit, name='categoria-edit'),
    path('categorias/<int:pk>/eliminar/', views.categoria_delete, name='categoria-delete'),
    path('categorias/<int:pk>/cerrar-inscripcion/', views.categoria_cerrar_inscripcion, name='categoria-cerrar-inscripcion'),
    path('categorias/<int:pk>/reabrir-inscripcion/', views.categoria_reabrir_inscripcion, name='categoria-reabrir-inscripcion'),
    path('categorias/<int:pk>/generar-partidos/', views.categoria_generar_partidos, name='categoria-generar-partidos'),
    path('categorias/<int:pk>/iniciar-liguilla/', views.categoria_iniciar_liguilla, name='categoria-iniciar-liguilla'),
]
