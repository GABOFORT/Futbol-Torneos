from django.contrib import admin

from .models import Categoria, Liga


@admin.register(Liga)
class LigaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa', 'fecha_inicio', 'fecha_final', 'fecha_pago')
    search_fields = ('nombre',)
    filter_horizontal = ('administradores',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'liga', 'limite_edad', 'cupo_equipos', 'inscripcion_abierta', 'activa')
    list_filter = ('liga', 'limite_edad', 'activa', 'inscripcion_abierta')
    search_fields = ('nombre', 'liga__nombre')
