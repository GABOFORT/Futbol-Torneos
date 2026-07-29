from django.contrib import admin

from .models import Jugador


@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'equipo', 'posicion', 'numero', 'estado')
    list_filter = ('equipo', 'posicion', 'estado')
    search_fields = ('nombre', 'apellido', 'equipo__nombre', 'equipo__entrenador__username')
