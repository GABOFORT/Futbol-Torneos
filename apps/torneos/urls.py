from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
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
