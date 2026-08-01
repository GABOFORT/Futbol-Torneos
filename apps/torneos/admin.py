from django.contrib import admin

from .models import Categoria, Liga, Sede


@admin.register(Liga)
class LigaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa', 'fecha_inicio', 'fecha_final', 'fecha_pago')
    search_fields = ('nombre',)
    filter_horizontal = ('administradores',)


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    # Las canchas se dan de alta desde el mapa al programar un partido. Esto es
    # la puerta de atras del superadmin para corregir un nombre o un pin sin
    # tener que abrir el formulario de un partido.
    list_display = ('nombre', 'liga', 'direccion', 'latitud', 'longitud')
    list_filter = ('liga',)
    search_fields = ('nombre', 'direccion', 'liga__nombre')


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'liga', 'limite_edad', 'cupo_equipos', 'inscripcion_abierta', 'activa')
    list_filter = ('liga', 'limite_edad', 'activa', 'inscripcion_abierta')
    search_fields = ('nombre', 'liga__nombre')
