from django.contrib import admin

from .models import Jugador


@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'equipo', 'posicion', 'estado', 'activo')
    list_filter = ('equipo', 'posicion', 'estado', 'activo')
    search_fields = ('nombre', 'apellido', 'equipo__nombre', 'equipo__entrenador__username')
