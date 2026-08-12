from django.contrib import admin

from .models import Equipo
from apps.jugadores.models import Jugador


class JugadorInline(admin.TabularInline):
    model = Jugador
    extra = 1
    # Sin 'activo': ese campo NO existe en Jugador. Era un booleano que se
    # reemplazo por 'estado' (activo/baja/lesion/sancion) y quedo la referencia
    # colgada, asi que abrir cualquier equipo en el panel respondia 500.
    #
    # `manage.py check` NO lo detecta: el error salta recien al construir el
    # formulario del inline, o sea al abrir la pagina. Se comprobo llamando a
    # modelform_factory con esa lista de campos —FieldError: Unknown field(s)
    # (activo)—, y por eso el panel dejaba sin herramienta al superadmin justo
    # cuando hace falta entrar a corregir algo a mano.
    fields = ('nombre', 'apellido', 'documento', 'posicion', 'numero', 'estado')


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'liga', 'categoria', 'entrenador', 'formacion')
    list_filter = ('liga', 'categoria', 'formacion')
    search_fields = ('nombre', 'entrenador__username', 'entrenador__first_name', 'entrenador__last_name')
    inlines = [JugadorInline]
