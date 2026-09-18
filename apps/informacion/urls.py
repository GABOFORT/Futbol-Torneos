from django.urls import path
from . import aliados_oficiales, views

urlpatterns = [
    path('quienes-somos/', views.quienes_somos, name='quienes-somos'),
    path('donde-estamos/', views.donde_estamos, name='donde-estamos'),
    path('reglamento/', views.reglamento, name='reglamento'),
    path('aviso-privacidad/', views.aviso_privacidad, name='aviso-privacidad'),
    path('aliados-oficiales/', aliados_oficiales.lista, name='aliados-oficiales'),
    path('aliados-oficiales/crear/', aliados_oficiales.crear, name='aliado-oficial-create'),
    path('aliados-oficiales/<int:pk>/', aliados_oficiales.ficha, name='aliado-oficial-ficha'),
    path('aliados-oficiales/<int:pk>/editar/', aliados_oficiales.editar, name='aliado-oficial-edit'),
    path('aliados-oficiales/<int:pk>/eliminar/', aliados_oficiales.eliminar, name='aliado-oficial-delete'),
]
