from django.urls import path
from . import views

urlpatterns = [
    path('', views.jugadores_index, name='jugadores-index'),
    path('equipo/<int:equipo_id>/', views.jugador_list, name='jugador-list'),
    path('equipo/<int:equipo_id>/crear/', views.jugador_create, name='jugador-create'),
    path('equipo/<int:equipo_id>/credenciales/', views.jugador_credenciales, name='jugador-credenciales'),
    path('<int:pk>/editar/', views.jugador_edit, name='jugador-edit'),
    path('<int:pk>/credencial/', views.jugador_credencial, name='jugador-credencial'),
    path('foto/<str:archivo>/', views.jugador_foto, name='jugador-foto'),
]
