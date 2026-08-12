from django.urls import path
from . import views

urlpatterns = [
    path('', views.estadisticas_ligas, name='estadisticas-ligas'),
    # La misma pantalla acotada a lo propio, para entrar desde el tablero. Va
    # antes que 'liga/<id>/' solo por legibilidad: 'mis-ligas/' es una ruta fija
    # y no compite con las que llevan un id.
    path('mis-ligas/', views.estadisticas_mis_ligas, name='estadisticas-mis-ligas'),
    path('liga/<int:liga_id>/', views.estadisticas_liga_categorias, name='estadisticas-liga-categorias'),
    path('categoria/<int:categoria_id>/', views.tabla_posiciones, name='estadisticas-categoria'),
    path('categoria/<int:categoria_id>/liguilla/', views.liguilla_categoria, name='categoria-liguilla'),
    path('vitrina/', views.vitrina, name='vitrina'),
    path('graficos/', views.pantalla_graficos, name='estadisticas-graficos'),
    path('porteros/', views.tabla_porteros, name='estadisticas-porteros'),
    path('goleo/', views.tabla_goleo, name='estadisticas-goleo'),
    path('asistencias/', views.tabla_asistencias, name='estadisticas-asistencias'),
]
