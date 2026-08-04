from django.urls import path
from . import views

urlpatterns = [
    path('', views.estadisticas_ligas, name='estadisticas-ligas'),
    path('liga/<int:liga_id>/', views.estadisticas_liga_categorias, name='estadisticas-liga-categorias'),
    path('categoria/<int:categoria_id>/', views.tabla_posiciones, name='estadisticas-categoria'),
    path('categoria/<int:categoria_id>/liguilla/', views.liguilla_categoria, name='categoria-liguilla'),
    path('vitrina/', views.vitrina, name='vitrina'),
    path('porteros/', views.tabla_porteros, name='estadisticas-porteros'),
    path('goleo/', views.tabla_goleo, name='estadisticas-goleo'),
    path('asistencias/', views.tabla_asistencias, name='estadisticas-asistencias'),
]
