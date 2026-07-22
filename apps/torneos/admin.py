from django.contrib import admin

from .models import Categoria, Liga


@admin.register(Liga)
class LigaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa', 'fecha_inicio', 'fecha_final', 'fecha_pago')
    search_fields = ('nombre',)
    filter_horizontal = ('administradores',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'liga', 'cupo_equipos', 'inscripcion_abierta', 'activa', 'fecha_inicio', 'fecha_final')
    list_filter = ('liga', 'activa', 'inscripcion_abierta')
    search_fields = ('nombre', 'liga__nombre')
