from django.contrib import messages
from django.db.models import Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.torneos.models import Categoria, Sede
from apps.usuarios.filtros import buscar, campo_texto, campo_opciones, campo_oculto
from apps.usuarios.permissions import admin_liga_required, ligas_administradas, ligas_visibles

from . import actuaciones, ficha, liguilla
from .calendario import equipo_que_descansa
from .forms import PartidoFechaForm, ResultadoForm, SedeForm
from .models import Partido

# Donde abre el mapa cuando la liga todavia no tiene ninguna cancha marcada.
# Villahermosa, que es donde juega la liga real del sistema.
CENTRO_POR_DEFECTO = ('17.989500', '-92.947500')

# El valor de la pastilla que muestra la liguilla. No es un numero porque la
# liguilla no es una jornada mas: son los cruces de eliminacion.
VALOR_LIGUILLA = 'liguilla'


def partido_list(request):
    user = request.user
    puede_gestionar = user.is_authenticated and (user.is_superuser or user.role == user.ROLE_ADMIN_LIGA)
    es_entrenador = user.is_authenticated and user.role == user.ROLE_ENTRENADOR and not user.is_superuser

    # Mismo criterio que en equipos: el admin de liga solo ve sus ligas y el
    # entrenador unicamente los partidos de los equipos que dirige.
    partidos = Partido.objects.filter(categoria__liga__in=ligas_visibles(user))
    if es_entrenador:
        partidos = partidos.filter(Q(equipo_local__entrenador=user) | Q(equipo_visitante__entrenador=user))

    termino = request.GET.get('q', '')
    # Por defecto se abre en la primera jornada: el torneo completo son cientos
    # de partidos de una vez y no se entiende nada.
    jornada = request.GET.get('jornada', '1')

    seleccion, opciones = _cascada(user, request.GET)

    partidos = buscar(partidos, termino, [
        'equipo_local__nombre', 'equipo_visitante__nombre',
        'categoria__nombre', 'categoria__liga__nombre',
    ])
    if seleccion['liga']:
        partidos = partidos.filter(categoria__liga_id=seleccion['liga'])
    if seleccion['categoria']:
        partidos = partidos.filter(categoria_id=seleccion['categoria'])
    if seleccion['equipo']:
        partidos = partidos.filter(
            Q(equipo_local_id=seleccion['equipo']) | Q(equipo_visitante_id=seleccion['equipo'])
        )
    if jornada == VALOR_LIGUILLA:
        partidos = partidos.exclude(fase=Partido.FASE_REGULAR)
    elif jornada.isdigit():
        # La liguilla no es una jornada del calendario: tiene su propia pastilla
        # y no debe colarse entre los partidos del torneo regular.
        partidos = partidos.filter(jornada=int(jornada), fase=Partido.FASE_REGULAR)

    partidos = partidos.select_related(
        'categoria', 'categoria__liga', 'equipo_local', 'equipo_visitante', 'ganador_penales',
        'sede', 'sede_original',
    ).order_by('categoria__liga__nombre', 'categoria__nombre', 'fecha', 'id')

    filtros = []
    if puede_gestionar:
        filtros = [
            campo_texto('q', 'Buscar', termino, 'Equipo, categoría o liga'),
            campo_opciones('liga', 'Liga', seleccion['liga'],
                           opciones['ligas'].values_list('id', 'nombre'), vacio='Todas las ligas'),
            campo_opciones('categoria', 'Categoría', seleccion['categoria'],
                           opciones['categorias'].values_list('id', 'nombre'), vacio='Todas'),
            campo_opciones('equipo', 'Equipo', seleccion['equipo'],
                           opciones['equipos'].values_list('id', 'nombre'), vacio='Todos'),
        ]
    # La jornada se elige con las pastillas, pero tiene que viajar con el resto.
    filtros.append(campo_oculto('jornada', jornada))

    grupos = _agrupar_por_jornada(partidos)
    if not grupos and jornada.isdigit():
        # El equipo no juega esa jornada: descansa. Sin esto la pantalla diria
        # "no hay partidos", que al entrenador no le explica nada.
        if seleccion['equipo']:
            en_descanso, propio = Equipo.objects.filter(pk=seleccion['equipo']), es_entrenador
        elif es_entrenador:
            en_descanso, propio = Equipo.objects.filter(entrenador=user), True
        else:
            en_descanso, propio = Equipo.objects.none(), False
        grupos = _bloques_de_descanso(en_descanso, int(jornada), propio)

    return render(request, 'partidos/partido_list.html', {
        'grupos': grupos,
        'puede_gestionar': puede_gestionar,
        'es_superadmin': user.is_authenticated and user.es_super_admin(),
        'jornadas': _pastillas_jornada(
            request, jornada, opciones['total_jornadas'], opciones['hay_liguilla']
        ),
        'filtros': filtros,
        'filtros_activos': bool(termino or seleccion['liga'] or seleccion['categoria'] or seleccion['equipo']),
        'total_resultados': partidos.count(),
    })


def _cascada(user, parametros):
    """Resuelve Liga -> Categoria -> Equipo, acotando cada nivel al de arriba.

    Si un nivel no pertenece al que lo contiene se descarta: asi cambiar de liga
    limpia sola la categoria vieja, y nadie llega a datos de otra liga pasando
    ids a mano en la URL.
    """
    ligas = ligas_visibles(user).order_by('nombre')
    categorias = Categoria.objects.filter(liga__in=ligas).order_by('liga__nombre', 'nombre')
    equipos = Equipo.objects.filter(liga__in=ligas).order_by('nombre')

    def elegido(nombre, disponibles):
        valor = parametros.get(nombre, '')
        if valor.isdigit() and disponibles.filter(pk=int(valor)).exists():
            return int(valor)
        return None

    liga = elegido('liga', ligas)
    if liga:
        categorias = categorias.filter(liga_id=liga)
        equipos = equipos.filter(liga_id=liga)

    categoria = elegido('categoria', categorias)
    if categoria:
        equipos = equipos.filter(categoria_id=categoria)

    equipo = elegido('equipo', equipos)

    # Las jornadas disponibles dependen de lo elegido: si se acota a una
    # categoria, no tiene sentido ofrecer jornadas que ahi no existen.
    alcance = Partido.objects.filter(categoria__liga__in=ligas)
    if liga:
        alcance = alcance.filter(categoria__liga_id=liga)
    if categoria:
        alcance = alcance.filter(categoria_id=categoria)
    if equipo:
        alcance = alcance.filter(Q(equipo_local_id=equipo) | Q(equipo_visitante_id=equipo))
    # Solo las jornadas del torneo regular: la liguilla tiene jornada 0 y su
    # propia pastilla, no seria la jornada siguiente a la ultima.
    total = alcance.filter(fase=Partido.FASE_REGULAR).aggregate(
        maximo=Max('jornada')
    )['maximo'] or 0
    hay_liguilla = alcance.exclude(fase=Partido.FASE_REGULAR).exists()

    seleccion = {'liga': liga, 'categoria': categoria, 'equipo': equipo}
    disponibles = {
        'ligas': ligas, 'categorias': categorias, 'equipos': equipos,
        'total_jornadas': total, 'hay_liguilla': hay_liguilla,
    }
    return seleccion, disponibles


def _pastillas_jornada(request, actual, total, hay_liguilla=False):
    """Una pastilla por jornada, conservando los demas filtros en el enlace.

    La liguilla va como una pastilla mas al final, pero solo cuando existe:
    hasta que no arranca no hay nada que mostrar ahi.
    """
    valores = [''] + list(range(1, total + 1))
    if hay_liguilla:
        valores.append(VALOR_LIGUILLA)

    pastillas = []
    for numero in valores:
        parametros = request.GET.copy()
        if numero == '':
            parametros['jornada'] = ''
        else:
            parametros['jornada'] = str(numero)
        pastillas.append({
            'etiqueta': 'Todas' if numero == '' else ('Liguilla' if numero == VALOR_LIGUILLA else numero),
            'valor': str(numero),
            'activa': str(numero) == (actual or ''),
            'url': f'{request.path}?{parametros.urlencode()}',
        })
    return pastillas


def _bloques_de_descanso(equipos, jornada, propio=False):
    """Un bloque por equipo que descansa en esa jornada.

    Se exige que la jornada exista en su categoria: si no existe no hay nada que
    informar, es simplemente una jornada que todavia no se juega.

    `propio` cambia el texto a segunda persona cuando el equipo es de quien esta
    mirando: al entrenador se le dice que le toca descansar, no que un equipo
    cualquiera descansa.
    """
    bloques = []
    for equipo in equipos.select_related('categoria', 'categoria__liga'):
        if Partido.objects.filter(categoria=equipo.categoria, jornada=jornada).exists():
            bloques.append({
                'categoria': equipo.categoria,
                'jornada': jornada,
                'partidos': [],
                'descansa': equipo,
                'descanso_propio': propio,
            })
    return bloques


def _agrupar_por_jornada(partidos):
    """Arma un bloque por categoria y jornada, con el equipo que descansa.

    Los partidos de liguilla se agrupan por fase y no por jornada: todos tienen
    jornada 0, y el bloque tiene que decir 'Semifinal', no 'Jornada 0'. Ahi
    tampoco hay equipo que descanse, porque no juegan todos.
    """
    bloques = {}
    for partido in partidos:
        clave = (partido.categoria_id, partido.fase, partido.jornada)
        bloques.setdefault(clave, {
            'categoria': partido.categoria,
            'jornada': partido.jornada,
            'es_liguilla': partido.es_liguilla,
            'etiqueta': partido.get_fase_display() if partido.es_liguilla else f'Jornada {partido.jornada}',
            'partidos': [],
        })
        bloques[clave]['partidos'].append(partido)

    for bloque in bloques.values():
        if bloque['es_liguilla']:
            bloque['descansa'] = None
            continue
        equipos = Equipo.objects.filter(categoria=bloque['categoria'])
        bloque['descansa'] = equipo_que_descansa(equipos, bloque['partidos'])
    return list(bloques.values())



def partido_detalle(request, pk):
    """La ficha completa del partido: previa si no se jugo, cronica si ya se jugo.

    De solo lectura y acotada por `ligas_visibles`: el admin de liga llega a las
    suyas, y el entrenador y el publico a las ligas activas.

    A diferencia del calendario, al entrenador no se lo limita a sus propios
    partidos. El calendario es su agenda y ahi tiene sentido ver solo lo suyo,
    pero la ficha es informacion publica: un visitante sin cuenta la abre, y
    dejar al entrenador afuera lo dejaba viendo menos que cualquiera. Ademas los
    ultimos cinco del rival se pueden pulsar, y sin esto le fallarian todos.
    """
    partido = get_object_or_404(
        Partido.objects.filter(categoria__liga__in=ligas_visibles(request.user)).select_related(
            'categoria', 'categoria__liga', 'equipo_local', 'equipo_visitante',
            'ganador_penales', 'sede', 'sede_original',
        ),
        pk=pk,
    )
    return render(request, 'partidos/partido_detalle.html', {
        'partido': partido,
        **ficha.armar(partido),
    })


@admin_liga_required
def partido_edit(request, pk):
    partido = get_object_or_404(Partido, pk=pk, categoria__liga__in=ligas_administradas(request.user))
    # Una vez cargado el resultado el partido queda cerrado: no se le cambia la
    # fecha a algo que ya se jugo. La validacion esta aca y no solo en el
    # boton, para que tampoco se llegue escribiendo la URL.
    if partido.jugado:
        raise Http404('Este partido ya tiene resultado y no se puede reprogramar.')

    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = PartidoFechaForm(request.POST, instance=partido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fecha y hora del partido actualizadas.')
            if modal:
                return JsonResponse({'success': True})
            return redirect('partido-list')
    else:
        form = PartidoFechaForm(instance=partido)

    titulo = 'Reprogramar' if partido.ya_empezo else 'Fecha, hora y lugar'
    context = {
        'form': form,
        'title': f'{titulo}: {partido.equipo_local} vs {partido.equipo_visitante}',
        'partido': partido,
        'centro_mapa': _centro_del_mapa(partido),
    }
    if modal:
        return render(request, 'usuarios/modal_form.html', context)
    return render(request, 'partidos/partido_form.html', context)


def _centro_del_mapa(partido):
    """Donde conviene abrir el mapa para marcar la cancha de este partido.

    Se busca el punto mas cercano a lo que el admin quiere marcar: la cancha que
    el partido ya tiene, o la ultima que se marco en esa liga. Asi no arranca en
    medio del oceano y casi siempre queda a unas cuadras del lugar buscado.
    """
    if partido.sede_id:
        return (partido.sede.latitud, partido.sede.longitud)
    ultima = Sede.objects.filter(liga=partido.categoria.liga).order_by('-id').first()
    if ultima:
        return (ultima.latitud, ultima.longitud)
    return CENTRO_POR_DEFECTO


@admin_liga_required
@require_POST
def sede_create(request, pk):
    """Da de alta la cancha marcada en el mapa, sin salir del formulario.

    Cuelga del partido a proposito: de ahi sale la liga a la que pertenece la
    cancha, y de paso se valida con el mismo criterio que el resto: si el admin
    no administra esa liga, no llega ni a crearla.
    """
    partido = get_object_or_404(Partido, pk=pk, categoria__liga__in=ligas_administradas(request.user))
    form = SedeForm(partido.categoria.liga, request.POST)
    if form.is_valid():
        sede = form.save()
        return JsonResponse({'success': True, 'id': sede.pk, 'nombre': sede.nombre})

    # Al JS le alcanza con el primer problema: el formulario del mapa tiene tres
    # campos y mostrar la lista entera no ayuda a corregirlo.
    primero = next(iter(form.errors.values()))[0]
    return JsonResponse({'success': False, 'error': primero}, status=400)


@admin_liga_required
def partido_resultado(request, pk):
    partido = get_object_or_404(Partido, pk=pk, categoria__liga__in=ligas_administradas(request.user))
    # No se carga el resultado de un partido que todavia no se jugo.
    if not partido.ya_empezo:
        raise Http404('Este partido todavía no empezó.')
    # Corregir un resultado ya cargado queda reservado al superadmin: asi un
    # error de tipeo no es definitivo, pero el partido queda cerrado en el uso
    # diario.
    if partido.jugado and not request.user.es_super_admin():
        raise Http404('Este partido ya tiene resultado. Solo el Administrador General puede corregirlo.')

    modal = request.GET.get('modal') == '1'
    plantel = Jugador.objects.filter(
        equipo_id__in=[partido.equipo_local_id, partido.equipo_visitante_id]
    ).select_related('equipo').order_by('equipo__nombre', 'nombre', 'apellido')

    problemas = []
    if request.method == 'POST':
        form = ResultadoForm(request.POST, instance=partido)
        filas = actuaciones.leer(request.POST, plantel)
        if form.is_valid():
            problemas = actuaciones.errores(
                filas, partido,
                form.cleaned_data['goles_local'], form.cleaned_data['goles_visitante'],
            )
            if not problemas:
                resultado = form.save(commit=False)
                resultado.estado = Partido.ESTADO_FINALIZADO
                resultado.save()
                actuaciones.guardar(resultado, filas)
                messages.success(request, 'Resultado y goleadores registrados.')
                # Si este resultado cerro una ronda de liguilla, la siguiente
                # queda armada sola con los ganadores.
                creados = liguilla.avanzar(resultado)
                if creados:
                    nombres = ', '.join(sorted({p.get_fase_display() for p in creados}))
                    messages.success(
                        request,
                        f'Se cerró {resultado.get_fase_display().lower()}: ya quedaron los cruces de '
                        f'{nombres.lower()}. Solo falta ponerles fecha y cancha.',
                    )
                if modal:
                    return JsonResponse({'success': True})
                return redirect('partido-list')
    else:
        form = ResultadoForm(instance=partido)
        filas = {}

    context = {
        'form': form,
        'partido': partido,
        'title': ('Corregir resultado' if partido.jugado else 'Resultado') +
                 f': {partido.equipo_local} vs {partido.equipo_visitante}',
        'plantel_local': [j for j in plantel if j.equipo_id == partido.equipo_local_id],
        'plantel_visitante': [j for j in plantel if j.equipo_id == partido.equipo_visitante_id],
        'goleadores': _cargados(partido, filas, 'goles', 'goles_en_contra'),
        'asistentes': _cargados(partido, filas, 'asistencias'),
        'problemas': problemas,
    }
    return render(request, 'partidos/resultado_form.html', context)


def _cargados(partido, filas, *campos):
    """Las filas que hay que volver a dibujar en el formulario.

    Si el POST fallo se reponen las que mando el usuario, para que no pierda lo
    que habia escrito; si no, las que ya estaban guardadas.
    """
    if filas:
        origen = [
            {'jugador_id': jid, **valores}
            for jid, valores in filas.items()
            if any(valores.get(c) for c in campos)
        ]
    else:
        origen = [
            {'jugador_id': a.jugador_id, 'goles': a.goles,
             'goles_en_contra': a.goles_en_contra, 'asistencias': a.asistencias}
            for a in partido.actuaciones.all()
            if any(getattr(a, c) for c in campos)
        ]
    salida = []
    for fila in origen:
        if 'goles' in campos:
            # Un gol normal y uno en contra son dos renglones distintos aunque
            # sean del mismo jugador: se marcan con casillas diferentes.
            if fila.get('goles'):
                salida.append({'jugador_id': fila['jugador_id'], 'cantidad': fila['goles'], 'en_contra': False})
            if fila.get('goles_en_contra'):
                salida.append({'jugador_id': fila['jugador_id'], 'cantidad': fila['goles_en_contra'], 'en_contra': True})
        else:
            salida.append({'jugador_id': fila['jugador_id'], 'cantidad': fila['asistencias'], 'en_contra': False})
    return salida
