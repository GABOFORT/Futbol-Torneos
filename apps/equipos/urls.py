from django.urls import path
from . import views

urlpatterns = [
    path('', views.equipo_list, name='equipo-list'),
    path('crear/', views.equipo_create, name='equipo-create'),
    path('<int:pk>/', views.equipo_detail, name='equipo-detail'),
    path('<int:pk>/perfil/', views.equipo_perfil, name='equipo-perfil'),
    path('<int:pk>/editar/', views.equipo_edit, name='equipo-edit'),
    path('<int:pk>/eliminar/', views.equipo_delete, name='equipo-delete'),
]
