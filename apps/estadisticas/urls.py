from django.urls import path
from . import views

urlpatterns = [
    path('', views.estadisticas_ligas, name='estadisticas-ligas'),
    path('liga/<int:liga_id>/', views.estadisticas_liga_categorias, name='estadisticas-liga-categorias'),
    path('categoria/<int:categoria_id>/', views.tabla_posiciones, name='estadisticas-categoria'),
]
