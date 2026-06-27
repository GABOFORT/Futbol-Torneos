from django.urls import path
from . import views

urlpatterns = [
    path('quienes-somos/', views.quienes_somos, name='quienes-somos'),
    path('donde-estamos/', views.donde_estamos, name='donde-estamos'),
    path('reglamento/', views.reglamento, name='reglamento'),
]
