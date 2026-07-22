from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('usuarios/', views.usuarios_list, name='usuarios-list'),
    path('usuarios/crear/', views.usuario_create, name='usuario-create'),
    path('usuarios/<int:pk>/editar/', views.usuario_edit, name='usuario-edit'),
    path('entrenadores/', views.entrenadores_list, name='entrenadores-list'),
    path('entrenadores/crear/', views.entrenador_create, name='entrenador-create'),
    path('entrenadores/<int:pk>/editar/', views.entrenador_edit, name='entrenador-edit'),
    path('ligas/', views.ligas_list, name='ligas-list'),
    path('ligas/crear/', views.liga_create, name='liga-create'),
    path('ligas/<int:pk>/editar/', views.liga_edit, name='liga-edit'),
    path('ligas/<int:pk>/pago/', views.liga_registrar_pago, name='liga-registrar-pago'),
]
