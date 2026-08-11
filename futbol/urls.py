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

# Donde vive el panel de Django. Se saca del .env porque en /admin/ lo encuentra
# cualquier escaneo automatico en el primer intento, y ahi adentro NO aplican los
# permisos de este proyecto: los filtros por `ligas_administradas()` que protegen
# las vistas no existen en el admin, asi que una sola cuenta de Administrador
# General comprometida borra la base entera desde ahi.
#
# Que quede claro: esto NO es seguridad de verdad, la ruta secreta se filtra
# sola con el tiempo. Lo que hace es sacar al panel del radar de los bots y
# quitarle ruido a la bitacora. Lo que protege sigue siendo la contrasena.
#
# Con `default` a proposito, al reves que los secretos de settings.py: si falta
# la variable el sitio tiene que arrancar igual, solo que con la ruta de fabrica.
# Una ruta de admin no es un secreto que justifique no levantar el servidor.
RUTA_ADMIN = config('RUTA_ADMIN', default='admin').strip('/')

urlpatterns = [
    path(f'{RUTA_ADMIN}/', admin.site.urls),
    path('__reload__/', include('django_browser_reload.urls')),
    path('', include('apps.torneos.urls')),         # Pagina principal
    path('usuarios/', include('apps.usuarios.urls')),
    path('equipos/', include('apps.equipos.urls')),
    path('jugadores/', include('apps.jugadores.urls')),
    path('partidos/', include('apps.partidos.urls')),
    path('estadisticas/', include('apps.estadisticas.urls')),
    path('informacion/', include('apps.informacion.urls')),
    # django.conf.urls.static.static() no sirve nada si DEBUG=False. Aqui no
    # hay nginx delante de waitress (solo IIS haciendo proxy de todo), asi que
    # Django tiene que servir /static/ y /media/ tambien en produccion.
    re_path(r'^static/(?P<path>.*)$', servir_estatico, {'document_root': settings.STATIC_ROOT}),
    re_path(r'^media/(?P<path>.*)$', servir_estatico, {'document_root': settings.MEDIA_ROOT}),
]
