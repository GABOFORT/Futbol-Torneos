from django.contrib import admin

from .models import Partido


@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display = ('categoria', 'equipo_local', 'equipo_visitante', 'fecha', 'estado')
    list_filter = ('categoria', 'estado')
    search_fields = ('equipo_local__nombre', 'equipo_visitante__nombre')
