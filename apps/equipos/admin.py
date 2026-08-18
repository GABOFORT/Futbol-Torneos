from django.contrib import admin

from .models import Equipo
from apps.jugadores.models import Jugador


class JugadorInline(admin.TabularInline):
    model = Jugador
    extra = 1
    fields = ('nombre', 'apellido', 'documento', 'posicion', 'numero', 'estado')


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'liga', 'categoria', 'entrenador', 'formacion')
    list_filter = ('liga', 'categoria', 'formacion')
    search_fields = ('nombre', 'entrenador__username', 'entrenador__first_name', 'entrenador__last_name')
    inlines = [JugadorInline]
