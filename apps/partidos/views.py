from django.contrib import messages
from django.db.models import Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.torneos import palmares
from apps.torneos.models import Categoria, Sede
from apps.usuarios.filtros import buscar, campo_texto, campo_opciones, campo_oculto
from apps.usuarios.permissions import (
    admin_liga_required, ligas_administradas, ligas_visibles,
    ligas_y_torneos_administrados, ligas_y_torneos_visibles,
)

from . import actuaciones, ficha, liguilla, mes, relampago
from .calendario import equipo_que_descansa
from .forms import PartidoFechaForm, ResultadoForm, SedeForm
from .models import Partido

CENTRO_POR_DEFECTO = ('17.989500', '-92.947500')

VALOR_LIGUILLA = 'liguilla'
VALOR_PENDIENTES = 'pendientes'

_TEXTOS_PUBLICOS = {
    'titulo_pagina': 'Partidos',
    'seccion': 'Partidos',
    'encabezado': 'Calendario de partidos',
    'descripcion': 'Cada jornada enfrenta a todos los equipos una vez. '
                   'Elige la jornada para ver sus partidos.',
    'enlace_publico': False,
}

_TEXTOS_MIS_LIGAS = {
    'titulo_pagina': 'Calendario de mis ligas',
    'seccion': 'Tablero · Partidos',
    'encabezado': 'Calendario de mis ligas',
    'descripcion': 'Los partidos de las ligas que administras. '
                   'Elige la jornada para programar o cargar resultados.',
    'enlace_publico': True,
}


def calendario_mes(request):
    """El calendario en vista mensual, publico.

    El listado por jornadas sirve para seguir una categoria; este sirve para la
    otra pregunta, la que hace quien no administra nada: **que se juega este
    sabado**. Por eso mezcla todas las categorias visibles y ordena por fecha.
    """
    hoy = timezone.localdate()
    anio, numero = mes.leer_mes(request.GET.get('mes'), hoy)
    desde, hasta = mes.limites(anio, numero)

    partidos = (
        Partido.objects
        .filter(
            categoria__liga__in=ligas_y_torneos_visibles(request.user),
            fecha__date__gte=desde,
            fecha__date__lte=hasta,
        )
        .select_related('categoria', 'categoria__liga',
                        'equipo_local', 'equipo_visitante', 'sede')
        .order_by('fecha')
    )

    return render(request, 'partidos/calendario_mes.html', {
        'titulo_mes': mes.nombre(anio, numero),
        'semanas': mes.armar(anio, numero, partidos, hoy),
        'dias': mes.DIAS,
        'mes_anterior': mes.vecino(anio, numero, -1),
        'mes_siguiente': mes.vecino(anio, numero, 1),
        'total': len(partidos),
        'es_mes_actual': (anio, numero) == (hoy.year, hoy.month),
    })


def partido_list(request):
    """El calendario publico, acotado por `ligas_visibles`.

    **A proposito trae los partidos de todas las ligas activas**, tambien para
    el admin de liga: esta es la pantalla que responde "que se juega", y la hace
    sobre todo quien no administra nada. La version acotada a lo propio es
    `partidos_de_mis_ligas`, que es a donde lleva el tablero.
    """
    return _calendario(request, solo_propias=False)


@admin_liga_required
def partidos_de_mis_ligas(request):
    """El mismo calendario, acotado a las ligas que uno administra.

    Es la entrada desde el tablero: ahi no se viene a mirar que se juega el
    sabado, se viene a programar y a cargar resultados. Sin acotar, un admin
    tenia que atravesar el calendario completo de todas las ligas activas para
    llegar a los partidos que si puede tocar.

    Reusa la vista y la plantilla; lo unico distinto es de que ligas se parte,
    incluida la cascada Liga -> Categoria -> Equipo de los filtros.
    """
    return _calendario(request, solo_propias=True)


def _calendario(request, solo_propias):
    user = request.user
    puede_gestionar = user.is_authenticated and (user.is_superuser or user.role == user.ROLE_ADMIN_LIGA)
    es_entrenador = (
        not solo_propias
        and user.is_authenticated and user.role == user.ROLE_ENTRENADOR and not user.is_superuser
    )

    ambito = (ligas_y_torneos_administrados(user) if solo_propias
              else ligas_y_torneos_visibles(user))
    partidos = Partido.objects.filter(categoria__liga__in=ambito)
    if es_entrenador:
        partidos = partidos.filter(Q(equipo_local__entrenador=user) | Q(equipo_visitante__entrenador=user))

    termino = request.GET.get('q', '')
    jornada = request.GET.get('jornada', '1')

    seleccion, opciones = _cascada(request.GET, ambito)

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
    elif jornada == VALOR_PENDIENTES:
        partidos = partidos.filter(fase=Partido.FASE_REGULAR, fuera_de_jornada=True)
    elif jornada.isdigit():
        partidos = partidos.filter(
            jornada=int(jornada), fase=Partido.FASE_REGULAR, fuera_de_jornada=False)

    partidos = partidos.select_related(
        'categoria', 'categoria__liga', 'equipo_local', 'equipo_visitante', 'ganador_penales',
        'sede', 'sede_original',
    ).order_by('categoria__liga__nombre', 'categoria__nombre', 'fecha', 'id')

    partidos = list(partidos)
    ids_propias = (
        set(ligas_y_torneos_administrados(user).values_list('id', flat=True))
        if puede_gestionar else set()
    )
    for partido in partidos:
        partido.se_puede_gestionar = puede_gestionar and partido.categoria.liga_id in ids_propias

    filtros = [
        campo_texto('q', 'Buscar', termino, 'Equipo, categoría o liga'),
        campo_opciones('liga', 'Liga o torneo', seleccion['liga'],
                       _rotulos_de_ambito(opciones['ligas']), vacio='Todos'),
        campo_opciones('categoria', 'Categoría', seleccion['categoria'],
                       opciones['categorias'].values_list('id', 'nombre'), vacio='Todas'),
        campo_opciones('equipo', 'Equipo', seleccion['equipo'],
                       opciones['equipos'].values_list('id', 'nombre'), vacio='Todos'),
    ]
    filtros.append(campo_oculto('jornada', jornada))

    grupos = _agrupar_por_jornada(
        partidos, set(ambito.filter(torneo__isnull=False).values_list('id', flat=True)))
    if not grupos and jornada.isdigit():
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
            request, jornada, opciones['total_jornadas'], opciones['hay_liguilla'],
            opciones['hay_pendientes'],
        ),
        'filtros': filtros,
        'filtros_activos': bool(termino or seleccion['liga'] or seleccion['categoria'] or seleccion['equipo']),
        'total_resultados': len(partidos),
        **(_TEXTOS_MIS_LIGAS if solo_propias else _TEXTOS_PUBLICOS),
    })


def _rotulos_de_ambito(ligas):
    """Los nombres del desplegable, marcando cuales son torneos.

    El calendario si mezcla los dos mundos —la pregunta que responde es "que se
    juega", y un torneo se juega igual—, pero el desplegable tiene que decir de
    cual viene cada nombre: sin la marca, un torneo llamado "Copa Verano" se lee
    como una liga mas.
    """
    de_torneo = set(ligas.filter(torneo__isnull=False).values_list('id', flat=True))
    return [(pk, f'{nombre} · Torneo' if pk in de_torneo else nombre)
            for pk, nombre in ligas.values_list('id', 'nombre')]


def _cascada(parametros, ambito):
    """Resuelve Liga -> Categoria -> Equipo, acotando cada nivel al de arriba.

    Si un nivel no pertenece al que lo contiene se descarta: asi cambiar de liga
    limpia sola la categoria vieja, y nadie llega a datos de otra liga pasando
    ids a mano en la URL.

    `ambito` es el conjunto de ligas del que parte la pantalla y lo decide quien
    llama: la publica pasa `ligas_visibles` y la del tablero
    `ligas_administradas`. Recibirlo en vez de calcularlo aca es lo que hace que
    los desplegables no ofrezcan ligas que la pantalla no va a mostrar.
    """
    ligas = ambito.order_by('nombre')
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

    alcance = Partido.objects.filter(categoria__liga__in=ligas)
    if liga:
        alcance = alcance.filter(categoria__liga_id=liga)
    if categoria:
        alcance = alcance.filter(categoria_id=categoria)
    if equipo:
        alcance = alcance.filter(Q(equipo_local_id=equipo) | Q(equipo_visitante_id=equipo))
    total = alcance.filter(fase=Partido.FASE_REGULAR, fuera_de_jornada=False).aggregate(
        maximo=Max('jornada')
    )['maximo'] or 0
    hay_liguilla = alcance.exclude(fase=Partido.FASE_REGULAR).exists()
    hay_pendientes = alcance.filter(
        fase=Partido.FASE_REGULAR, fuera_de_jornada=True).exists()

    seleccion = {'liga': liga, 'categoria': categoria, 'equipo': equipo}
    disponibles = {
        'ligas': ligas, 'categorias': categorias, 'equipos': equipos,
        'total_jornadas': total, 'hay_liguilla': hay_liguilla,
        'hay_pendientes': hay_pendientes,
    }
    return seleccion, disponibles


def _rotulo_pastilla(numero):
    if numero == '':
        return 'Todas'
    if numero == VALOR_LIGUILLA:
        return 'Liguilla'
    if numero == VALOR_PENDIENTES:
        return 'Pendientes'
    return numero


def _pastillas_jornada(request, actual, total, hay_liguilla=False, hay_pendientes=False):
    """Una pastilla por jornada, conservando los demas filtros en el enlace.

    La liguilla va como una pastilla mas al final, pero solo cuando existe:
    hasta que no arranca no hay nada que mostrar ahi.
    """
    valores = [''] + list(range(1, total + 1))
    if hay_pendientes:
        valores.append(VALOR_PENDIENTES)
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
            'etiqueta': _rotulo_pastilla(numero),
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
        if Partido.objects.filter(
                categoria=equipo.categoria, jornada=jornada, fuera_de_jornada=False).exists():
            bloques.append({
                'categoria': equipo.categoria,
                'jornada': jornada,
                'partidos': [],
                'descansa': equipo,
                'descanso_propio': propio,
            })
    return bloques


def _agrupar_por_jornada(partidos, ids_de_torneo=frozenset()):
    """Arma un bloque por categoria y jornada, con el equipo que descansa.

    Los partidos de liguilla se agrupan por fase y no por jornada: todos tienen
    jornada 0, y el bloque tiene que decir 'Semifinal', no 'Jornada 0'. Ahi
    tampoco hay equipo que descanse, porque no juegan todos.

    `ids_de_torneo` llega resuelto de una sola consulta: preguntarle a cada
    bloque `partido.es_de_torneo` costaria una consulta por bloque, porque el
    torneo cuelga de la liga por el lado inverso y no entra en select_related.
    """
    bloques = {}
    for partido in partidos:
        clave = (partido.categoria_id, partido.fase, partido.jornada,
                 partido.vuelta, partido.fuera_de_jornada)
        bloques.setdefault(clave, {
            'categoria': partido.categoria,
            'jornada': partido.jornada,
            'es_liguilla': partido.es_liguilla,
            'es_de_torneo': partido.categoria.liga_id in ids_de_torneo,
            'fuera_de_jornada': partido.fuera_de_jornada,
            'etiqueta': partido.etiqueta,
            'partidos': [],
        })
        bloques[clave]['partidos'].append(partido)

    for bloque in bloques.values():
        if bloque['es_liguilla'] or bloque['fuera_de_jornada']:
            bloque['descansa'] = None
            continue
        equipos = Equipo.objects.filter(categoria=bloque['categoria'])
        bloque['descansa'] = equipo_que_descansa(equipos, bloque['partidos'])
    return list(bloques.values())


def partido_detalle(request, liga, categoria, partido):
    """La ficha completa del partido: previa si no se jugo, cronica si ya se jugo.

    De solo lectura y acotada por `ligas_visibles`: el admin de liga llega a las
    suyas, y el entrenador y el publico a las ligas activas.

    A diferencia del calendario, al entrenador no se lo limita a sus propios
    partidos. El calendario es su agenda y ahi tiene sentido ver solo lo suyo,
    pero la ficha es informacion publica: un visitante sin cuenta la abre, y
    dejar al entrenador afuera lo dejaba viendo menos que cualquiera. Ademas los
    ultimos cinco del rival se pueden pulsar, y sin esto le fallarian todos.
    """
    candidatos = Partido.objects.filter(
        categoria__liga__in=ligas_y_torneos_visibles(request.user),
        categoria__liga__slug=liga, categoria__slug=categoria,
    ).select_related(
        'categoria', 'categoria__liga', 'equipo_local', 'equipo_visitante',
        'ganador_penales', 'sede', 'sede_original', 'no_se_presento',
    )
    partido = next((uno for uno in candidatos if uno.slug == partido), None)
    if partido is None:
        raise Http404('No existe ese partido.')
    modal = request.GET.get('modal') == '1'
    contexto = {'partido': partido, 'en_modal': modal, **ficha.armar(partido)}
    if modal:
        return render(request, 'partidos/_ficha_partido.html', contexto)
    return render(request, 'partidos/partido_detalle.html', contexto)


@admin_liga_required
def partido_edit(request, pk):
    partido = get_object_or_404(
        Partido, pk=pk,
        categoria__liga__in=ligas_y_torneos_administrados(request.user))
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
    partido = get_object_or_404(
        Partido, pk=pk,
        categoria__liga__in=ligas_y_torneos_administrados(request.user))
    form = SedeForm(partido.categoria.liga, request.POST)
    if form.is_valid():
        sede = form.save()
        return JsonResponse({'success': True, 'id': sede.pk, 'nombre': sede.nombre})

    primero = next(iter(form.errors.values()))[0]
    return JsonResponse({'success': False, 'error': primero}, status=400)


@admin_liga_required
def partido_resultado(request, pk):
    partido = get_object_or_404(
        Partido, pk=pk,
        categoria__liga__in=ligas_y_torneos_administrados(request.user))
    if not partido.ya_empezo:
        raise Http404('Este partido todavía no empezó.')
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
            por_default = form.cleaned_data.get('no_se_presento') is not None
            if por_default:
                filas = {}
                problemas = []
            else:
                problemas = actuaciones.errores(
                    filas, partido,
                    form.cleaned_data['goles_local'], form.cleaned_data['goles_visitante'],
                )
            if not problemas:
                resultado = form.save(commit=False)
                resultado.estado = Partido.ESTADO_FINALIZADO
                resultado.save()
                actuaciones.guardar(resultado, filas)
                if por_default:
                    messages.success(
                        request,
                        f'{resultado.equipo_presentado} ganó por default '
                        f'{Partido.MARCADOR_DEFAULT}-0: {resultado.no_se_presento} no se presentó.',
                    )
                else:
                    messages.success(request, 'Resultado y goleadores registrados.')
                motor = relampago if resultado.es_de_torneo else liguilla
                avance = motor.avanzar(resultado)

                if avance['rehechas']:
                    palmares.reabrir(resultado.categoria)
                    messages.warning(
                        request,
                        f'Cambió quién avanza, así que se rehízo: '
                        f'{", ".join(avance["rehechas"]).lower()}. Esos partidos perdieron su '
                        f'fecha, cancha y resultado, y hay que cargarlos de nuevo.',
                    )

                if avance['creados']:
                    nombres = ', '.join(sorted({p.get_fase_display() for p in avance['creados']}))
                    messages.success(
                        request,
                        f'Se cerró {resultado.get_fase_display().lower()}: ya quedaron los cruces de '
                        f'{nombres.lower()}. Solo falta ponerles fecha y cancha.',
                    )

                premios = (palmares.cerrar_torneo_si_termino(resultado)
                           if resultado.es_de_torneo
                           else palmares.cerrar_si_termino(resultado))
                if premios:
                    messages.success(
                        request,
                        f'¡Terminó {premios.categoria_nombre}! Campeón: {premios.campeon}. '
                        f'La categoría queda concluida y su palmarés ya está guardado.',
                    )
                if modal:
                    return JsonResponse({'success': True})
                return redirect(resultado)
    else:
        form = ResultadoForm(instance=partido)
        filas = {}

    context = {
        'form': form,
        'partido': partido,
        'title': ('Corregir resultado' if partido.jugado else 'Resultado') +
                 f' · {partido.etiqueta}: {partido.equipo_local} vs {partido.equipo_visitante}',
        'plantel_local': [j for j in plantel if j.equipo_id == partido.equipo_local_id],
        'plantel_visitante': [j for j in plantel if j.equipo_id == partido.equipo_visitante_id],
        'goleadores': _cargados(partido, filas, 'goles', 'goles_en_contra'),
        'asistentes': _cargados(partido, filas, 'asistencias'),
        'problemas': problemas,
        'en_modal': modal,
    }
    if modal:
        return render(request, 'partidos/_resultado_form.html', context)
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
             'goles_en_contra': a.goles_en_contra, 'goles_de_penal': a.goles_de_penal,
             'asistencias': a.asistencias}
            for a in partido.actuaciones.all()
            if any(getattr(a, c) for c in campos)
        ]
    salida = []
    for fila in origen:
        if 'goles' in campos:
            if fila.get('goles'):
                salida.append({
                    'jugador_id': fila['jugador_id'], 'cantidad': fila['goles'],
                    'en_contra': False, 'de_penal': fila.get('goles_de_penal', 0),
                })
            if fila.get('goles_en_contra'):
                salida.append({
                    'jugador_id': fila['jugador_id'], 'cantidad': fila['goles_en_contra'],
                    'en_contra': True, 'de_penal': 0,
                })
        else:
            salida.append({
                'jugador_id': fila['jugador_id'], 'cantidad': fila['asistencias'],
                'en_contra': False, 'de_penal': 0,
            })
    return salida
