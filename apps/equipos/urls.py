from django.shortcuts import get_object_or_404
from django.urls import path

from apps.usuarios.rutas import canonica

from . import views
from .models import Equipo

urlpatterns = [
    path('', views.equipo_list, name='equipo-list'),
    path('mis-ligas/', views.equipos_de_mis_ligas, name='equipos-mis-ligas'),
    path('crear/', views.equipo_create, name='equipo-create'),
    path('<int:pk>/perfil/', views.equipo_perfil, name='equipo-perfil'),
    path('<int:pk>/editar/', views.equipo_edit, name='equipo-edit'),
    path('<int:pk>/eliminar/', views.equipo_delete, name='equipo-delete'),
    path('<int:pk>/',
         canonica(lambda pk: get_object_or_404(
             Equipo.objects.select_related('liga', 'categoria'), pk=pk)),
         name='equipo-detail-id'),
    path('<slug:liga>/<slug:categoria>/<slug:equipo>/',
         views.equipo_detail, name='equipo-detail'),
]
