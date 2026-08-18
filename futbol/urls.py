"""
URL configuration for futbol project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from decouple import config
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve as servir_estatico

RUTA_ADMIN = config('RUTA_ADMIN', default='admin').strip('/')

urlpatterns = [
    path(f'{RUTA_ADMIN}/', admin.site.urls),
    path('', include('apps.torneos.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('equipos/', include('apps.equipos.urls')),
    path('jugadores/', include('apps.jugadores.urls')),
    path('partidos/', include('apps.partidos.urls')),
    path('estadisticas/', include('apps.estadisticas.urls')),
    path('informacion/', include('apps.informacion.urls')),
    re_path(r'^static/(?P<path>.*)$', servir_estatico, {'document_root': settings.STATIC_ROOT}),
    re_path(r'^media/(?P<path>.*)$', servir_estatico, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns.insert(1, path('__reload__/', include('django_browser_reload.urls')))
