from django.shortcuts import get_object_or_404
from django.urls import path

from apps.torneos.models import Categoria, Liga
from apps.usuarios.rutas import canonica

from . import views

urlpatterns = [
    path('', views.estadisticas_ligas, name='estadisticas-ligas'),
    path('mis-ligas/', views.estadisticas_mis_ligas, name='estadisticas-mis-ligas'),
    path('liga/<int:liga_id>/',
         canonica(lambda liga_id: get_object_or_404(Liga, pk=liga_id)),
         name='estadisticas-liga-id'),
    path('categoria/<int:categoria_id>/',
         canonica(lambda categoria_id: get_object_or_404(
             Categoria.objects.select_related('liga'), pk=categoria_id)),
         name='estadisticas-categoria-id'),
    path('categoria/<int:categoria_id>/liguilla/', views.liguilla_categoria, name='categoria-liguilla'),
    path('liga/<slug:liga>/', views.estadisticas_liga_categorias, name='estadisticas-liga-categorias'),
    path('liga/<slug:liga>/<slug:categoria>/', views.tabla_posiciones, name='estadisticas-categoria'),
    path('vitrina/', views.vitrina, name='vitrina'),
    path('graficos/', views.pantalla_graficos, name='estadisticas-graficos'),
    path('porteros/', views.tabla_porteros, name='estadisticas-porteros'),
    path('goleo/', views.tabla_goleo, name='estadisticas-goleo'),
    path('asistencias/', views.tabla_asistencias, name='estadisticas-asistencias'),
]
