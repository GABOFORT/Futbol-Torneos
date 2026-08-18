from django.urls import path
from . import torneos, views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('torneos/', torneos.torneo_list, name='torneo-list'),
    path('torneos/mis-torneos/', torneos.mis_torneos, name='mis-torneos'),
    path('torneos/crear/', torneos.torneo_create, name='torneo-create'),
    path('torneos/<int:pk>/', torneos.torneo_detalle, name='torneo-detalle'),
    path('torneos/<int:pk>/editar/', torneos.torneo_edit, name='torneo-edit'),
    path('torneos/<int:pk>/eliminar/', torneos.torneo_delete, name='torneo-delete'),
    path('torneos/<int:pk>/equipos/crear/', torneos.torneo_equipo_create, name='torneo-equipo-create'),
    path('torneos/<int:pk>/sortear/', torneos.torneo_sortear, name='torneo-sortear'),
    path('roles/', views.roles, name='roles'),
    path('buscar/', views.buscar_vista, name='buscar'),
    path('sedes/', views.sedes_vista, name='sedes'),
    path('mis-equipos/', views.mis_equipos, name='mis-equipos'),
    path('categorias/', views.categoria_list, name='categoria-list'),
    path('categorias/crear/', views.categoria_create, name='categoria-create'),
    path('categorias/<int:pk>/editar/', views.categoria_edit, name='categoria-edit'),
    path('categorias/<int:pk>/eliminar/', views.categoria_delete, name='categoria-delete'),
    path('categorias/<int:pk>/cerrar-inscripcion/', views.categoria_cerrar_inscripcion, name='categoria-cerrar-inscripcion'),
    path('categorias/<int:pk>/reabrir-inscripcion/', views.categoria_reabrir_inscripcion, name='categoria-reabrir-inscripcion'),
    path('categorias/<int:pk>/generar-partidos/', views.categoria_generar_partidos, name='categoria-generar-partidos'),
    path('categorias/<int:pk>/iniciar-liguilla/', views.categoria_iniciar_liguilla, name='categoria-iniciar-liguilla'),
]
