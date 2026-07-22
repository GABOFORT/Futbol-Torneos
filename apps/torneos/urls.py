from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('roles/', views.roles, name='roles'),
    path('categorias/', views.categoria_list, name='categoria-list'),
    path('categorias/crear/', views.categoria_create, name='categoria-create'),
    path('categorias/<int:pk>/editar/', views.categoria_edit, name='categoria-edit'),
    path('categorias/<int:pk>/cerrar-inscripcion/', views.categoria_cerrar_inscripcion, name='categoria-cerrar-inscripcion'),
    path('categorias/<int:pk>/reabrir-inscripcion/', views.categoria_reabrir_inscripcion, name='categoria-reabrir-inscripcion'),
    path('categorias/<int:pk>/generar-partidos/', views.categoria_generar_partidos, name='categoria-generar-partidos'),
]
