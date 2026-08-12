from django.urls import path
from . import views

urlpatterns = [
    path('', views.partido_list, name='partido-list'),
    # El mismo calendario acotado a lo propio, para entrar desde el tablero.
    path('mis-ligas/', views.partidos_de_mis_ligas, name='partidos-mis-ligas'),
    path('calendario/', views.calendario_mes, name='partido-calendario'),
    path('<int:pk>/', views.partido_detalle, name='partido-detalle'),
    path('<int:pk>/editar/', views.partido_edit, name='partido-edit'),
    path('<int:pk>/resultado/', views.partido_resultado, name='partido-resultado'),
    path('<int:pk>/sede/', views.sede_create, name='partido-sede-crear'),
]
