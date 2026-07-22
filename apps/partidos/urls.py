from django.urls import path
from . import views

urlpatterns = [
    path('', views.partido_list, name='partido-list'),
    path('<int:pk>/editar/', views.partido_edit, name='partido-edit'),
    path('<int:pk>/resultado/', views.partido_resultado, name='partido-resultado'),
]
