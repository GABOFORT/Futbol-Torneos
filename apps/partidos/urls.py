from django.shortcuts import get_object_or_404
from django.urls import path

from apps.usuarios.rutas import canonica

from . import views
from .models import Partido

urlpatterns = [
    path('', views.partido_list, name='partido-list'),
    path('mis-ligas/', views.partidos_de_mis_ligas, name='partidos-mis-ligas'),
    path('calendario/', views.calendario_mes, name='partido-calendario'),
    path('<int:pk>/editar/', views.partido_edit, name='partido-edit'),
    path('<int:pk>/resultado/', views.partido_resultado, name='partido-resultado'),
    path('<int:pk>/sede/', views.sede_create, name='partido-sede-crear'),
    path('<int:pk>/',
         canonica(lambda pk: get_object_or_404(
             Partido.objects.select_related(
                 'categoria__liga', 'equipo_local', 'equipo_visitante'), pk=pk)),
         name='partido-detalle-id'),
    path('<slug:liga>/<slug:categoria>/<slug:partido>/',
         views.partido_detalle, name='partido-detalle'),
]
