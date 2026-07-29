from django.urls import path
from . import views

urlpatterns = [
    path('', views.jugadores_index, name='jugadores-index'),
    path('equipo/<int:equipo_id>/', views.jugador_list, name='jugador-list'),
    path('equipo/<int:equipo_id>/crear/', views.jugador_create, name='jugador-create'),
    path('<int:pk>/editar/', views.jugador_edit, name='jugador-edit'),
]
