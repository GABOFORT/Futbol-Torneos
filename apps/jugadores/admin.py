from django.contrib import admin

from .models import Jugador


@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'equipo', 'sexo', 'posicion', 'numero', 'estado')
    list_filter = ('equipo', 'sexo', 'posicion', 'estado')
    search_fields = ('nombre', 'apellido', 'equipo__nombre', 'equipo__entrenador__username')
