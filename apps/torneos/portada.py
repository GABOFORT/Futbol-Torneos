"""Todo lo que se muestra en la pagina de inicio.

Vive aparte de la vista por el mismo motivo que `tabla.py` o `resumen.py`: la
vista solo tiene que pedir los datos y entregarlos a la plantilla.

**La portada es para quien no tiene cuenta.** Un padre que entra a ver a que
hora juega su hijo, quien va ganando y quien mete los goles. Por eso todo lo que
sale de aca esta acotado a `Liga.activa=True`: lo que no es publico no aparece.

**Nada se inventa.** Cada bloque sale de datos cargados; si no hay, el bloque no
se muestra en vez de rellenarse con ceros o con texto de ejemplo.
"""
import datetime

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.equipos.models import Equipo
from apps.estadisticas import tabla
from apps.jugadores.models import Jugador
from apps.partidos.models import Actuacion, Partido
from apps.torneos.models import Categoria, Liga, Palmares
from apps.usuarios.barras import a_paso

# Los rankings de la portada muestran cinco y no diez: es un resumen que invita
# a entrar a la tabla completa, no la tabla. Con diez, las tres columnas empujan
# el resto de la pagina fuera de la pantalla.
#
# Cuantos dias hacia atras se mira para el jugador del momento y los ultimos
# resultados. Una semana es el ciclo natural de estas ligas: se juega el fin de
# semana y se comenta hasta el siguiente.
DIAS_DE_LA_SEMANA = 7


def _ligas_publicas():
    return Liga.objects.filter(activa=True)


def cifras():
    """Los cuatro numeros del encabezado.

    Se cuentan sobre las ligas publicas: una liga desactivada no tiene por que
    inflar el total de jugadores que ve un visitante.
    """
    ligas = _ligas_publicas()
    hoy = timezone.localdate()
    return {
        'partidos_hoy': Partido.objects.filter(
            categoria__liga__in=ligas, fecha__date=hoy).count(),
        'equipos': Equipo.objects.filter(liga__in=ligas).count(),
        'torneos_activos': Categoria.objects.filter(
            liga__in=ligas, activa=True, cerrada=False).count(),
        'jugadores': Jugador.objects.filter(equipo__liga__in=ligas).count(),
    }


def _con_todo(consulta):
    """Los `select_related` que necesita cualquier lista de partidos.

    Sin esto cada tarjeta del calendario dispara cuatro consultas sueltas para
    dibujar dos escudos, la categoria y la cancha.
    """
    return consulta.select_related(
        'categoria', 'categoria__liga', 'equipo_local', 'equipo_visitante', 'sede')


def partidos_de_hoy(tope=12):
    """Los que se juegan hoy, en orden de hora.

    Entran los ya jugados de hoy tambien: a media tarde lo que se quiere ver es
    tanto el que falta como el que ya termino.
    """
    hoy = timezone.localdate()
    return list(_con_todo(Partido.objects.filter(
        categoria__liga__in=_ligas_publicas(), fecha__date=hoy,
    )).order_by('fecha')[:tope])


def proximos(tope=6):
    """Los siguientes partidos con fecha puesta.

    `fecha__gte=ahora` y no `fecha__isnull=False` a secas: un partido sin fecha
    no es un proximo partido, y ordenar por fecha con nulos los traia primero.
    """
    return list(_con_todo(Partido.objects.filter(
        categoria__liga__in=_ligas_publicas(),
        estado__in=Partido.ESTADOS_POR_JUGARSE,
        fecha__gte=timezone.now(),
    )).order_by('fecha')[:tope])


def ultimos_resultados(tope=8):
    """Lo que se jugo en los ultimos dias, del mas reciente al mas viejo."""
    desde = timezone.now() - datetime.timedelta(days=DIAS_DE_LA_SEMANA)
    return list(_con_todo(Partido.objects.filter(
        categoria__liga__in=_ligas_publicas(),
        estado=Partido.ESTADO_FINALIZADO,
        fecha__gte=desde,
    )).order_by('-fecha')[:tope])


def partido_destacado():
    """El proximo partido que mas vale la pena mirar.

    Se elige por la suma de los puestos de los dos equipos en la tabla de su
    categoria: el 1o contra el 2o suma 3 y gana sobre cualquier otro cruce. Es
    la definicion mas simple de "partidazo" que se puede sostener con los datos
    que hay, y no depende de que nadie lo marque a mano.

    Se miran solo los primeros partidos por jugarse para no calcular la tabla de
    las doce categorias en cada visita a la portada.
    """
    candidatos = proximos(tope=10)
    if not candidatos:
        return None

    mejor, mejor_peso = None, None
    posiciones_cache = {}
    for partido in candidatos:
        cat = partido.categoria_id
        if cat not in posiciones_cache:
            posiciones_cache[cat] = {
                fila['equipo'].id: numero
                for numero, fila in enumerate(tabla.calcular(partido.categoria), start=1)
            }
        puestos = posiciones_cache[cat]
        local = puestos.get(partido.equipo_local_id)
        visitante = puestos.get(partido.equipo_visitante_id)
        if local is None or visitante is None:
            continue
        peso = local + visitante
        if mejor_peso is None or peso < mejor_peso:
            mejor, mejor_peso = partido, peso
            mejor.puesto_local = local
            mejor.puesto_visitante = visitante
    return mejor


def _lideres(campo, tope):
    """El ranking de goles o de asistencias, de todas las ligas publicas.

    Agrupa por jugador en una sola consulta. **No usa `_ranking` de
    estadisticas/views.py a proposito**: esa vista calcula ademas los partidos
    jugados por equipo con una consulta por fila, y en la portada eso serian
    cientos de consultas para diez renglones.
    """
    filas = (
        Actuacion.objects
        .filter(jugador__equipo__liga__in=_ligas_publicas())
        .values(
            'jugador_id', 'jugador__nombre', 'jugador__apellido', 'jugador__numero',
            'jugador__equipo_id', 'jugador__equipo__nombre',
            'jugador__equipo__categoria__nombre', 'jugador__equipo__liga__nombre',
        )
        .annotate(total=Sum(campo))
        .filter(total__gt=0)
        .order_by('-total')[:tope]
    )
    return [{
        'jugador': f"{f['jugador__nombre']} {f['jugador__apellido']}",
        'jugador_id': f['jugador_id'],
        'numero': f['jugador__numero'],
        'equipo': f['jugador__equipo__nombre'],
        'equipo_id': f['jugador__equipo_id'],
        'categoria': f['jugador__equipo__categoria__nombre'],
        'liga': f['jugador__equipo__liga__nombre'],
        'total': f['total'],
    } for f in filas]


def goleadores(tope=5):
    return _lideres('goles', tope)


def asistidores(tope=5):
    return _lideres('asistencias', tope)


# Partidos minimos para entrar al top de vallas. Sin esto lo encabeza siempre
# el equipo que menos jugo: dos partidos con tres goles en contra le ganan a
# veinte con quince, y no es lo mismo.
MINIMO_PARA_VALLAS = 4


def vallas(tope=5):
    """Las porterias menos vencidas, contando solo el torneo regular.

    Mismo criterio que `porteros.py`: es por equipo y no por portero, porque no
    se registra quien ataja cada partido. Se rehace aca en una sola consulta
    agregada en vez de reutilizar `porteros.calcular`, que devuelve la tabla
    completa agrupada por categoria y no un top corto.

    **Se ordena por promedio y no por total.** En la pantalla de porteros la
    comparacion es dentro de una categoria, donde todos jugaron mas o menos lo
    mismo; aca se mezclan doce categorias en distinto punto del torneo, y el
    total premiaria al que menos jugo.
    """
    # Se cuenta recorriendo los partidos una sola vez, como en `porteros.py`, y
    # NO con dos `Sum` anotados sobre `partidos_local` y `partidos_visitante`.
    # Ese camino parece mas corto y da numeros inflados: Django une las dos
    # relaciones en la misma consulta y cada fila de una se multiplica por las
    # de la otra. `distinct=True` salva al Count pero no al Sum.
    marcadores = (
        Partido.objects
        .filter(
            categoria__liga__in=_ligas_publicas(),
            estado=Partido.ESTADO_FINALIZADO,
            fase=Partido.FASE_REGULAR,
        )
        .values_list('equipo_local_id', 'equipo_visitante_id',
                     'goles_local', 'goles_visitante')
    )

    acumulado = {}
    for local, visitante, gl, gv in marcadores:
        for equipo_id, recibidos in ((local, gv), (visitante, gl)):
            fila = acumulado.setdefault(equipo_id, {'pj': 0, 'gc': 0, 'cero': 0})
            fila['pj'] += 1
            fila['gc'] += recibidos
            # La porteria en cero es el dato que la gente reconoce; el promedio
            # es el que ordena.
            if recibidos == 0:
                fila['cero'] += 1

    llegan = [eid for eid, f in acumulado.items() if f['pj'] >= MINIMO_PARA_VALLAS]
    equipos = {
        e.id: e for e in Equipo.objects.filter(pk__in=llegan)
        .select_related('categoria', 'liga')
    }

    filas = [{
        'equipo': equipos[eid],
        'jugados': acumulado[eid]['pj'],
        'recibidos': acumulado[eid]['gc'],
        'porterias_cero': acumulado[eid]['cero'],
        'promedio': round(acumulado[eid]['gc'] / acumulado[eid]['pj'], 2),
    } for eid in llegan if eid in equipos]
    # A igual promedio pasa adelante el que mas jugo: sostenerlo mas fechas vale.
    filas.sort(key=lambda f: (f['promedio'], -f['jugados']))
    return filas[:tope]


def jugador_del_momento():
    """El que mas aporto en la ultima semana: goles mas asistencias.

    Se suman las dos cosas porque un pase gol vale tanto como el gol para
    decidir quien fue la figura de la fecha. Devuelve None si no se jugo nada,
    que es lo correcto: mejor no mostrar la seccion que inventar una figura.

    Devuelve tambien **su mejor partido concreto** —cuantos goles, contra quien
    y cuando—. Sin ese dato la seccion mostraba un numero suelto que no contaba
    nada: 'aporte 4' no dice si metio cuatro goles o dio cuatro pases.
    """
    desde = timezone.now() - datetime.timedelta(days=DIAS_DE_LA_SEMANA)
    de_la_semana = Actuacion.objects.filter(
        jugador__equipo__liga__in=_ligas_publicas(),
        partido__estado=Partido.ESTADO_FINALIZADO,
        partido__fecha__gte=desde,
    )

    fila = (
        de_la_semana
        .values(
            'jugador_id', 'jugador__nombre', 'jugador__apellido', 'jugador__numero',
            'jugador__equipo_id', 'jugador__equipo__nombre',
            'jugador__equipo__categoria__nombre', 'jugador__equipo__liga__nombre',
        )
        # Los alias en el mismo `annotate`: encadenarlos haria que el segundo
        # intente sumar el alias del primero, que ya es un agregado. Y no se
        # pueden llamar como los campos, o el alias los tapa.
        .annotate(
            total_goles=Sum('goles'),
            total_asistencias=Sum('asistencias'),
            partidos=Count('partido_id', distinct=True),
            aporte=Sum('goles') + Sum('asistencias'),
        )
        .filter(aporte__gt=0)
        .order_by('-aporte', '-total_goles')
        .first()
    )
    if not fila:
        return None

    # El mejor de sus partidos de la semana, para poder contarlo con nombre y
    # apellido en vez de dejar un total abstracto.
    mejor = (
        de_la_semana
        .filter(jugador_id=fila['jugador_id'])
        .select_related('partido', 'partido__equipo_local', 'partido__equipo_visitante')
        .order_by('-goles', '-asistencias')
        .first()
    )
    destacado = None
    if mejor and (mejor.goles or mejor.asistencias):
        partido = mejor.partido
        propio = fila['jugador__equipo_id']
        rival = (partido.equipo_visitante if partido.equipo_local_id == propio
                 else partido.equipo_local)
        destacado = {
            'goles': mejor.goles,
            'asistencias': mejor.asistencias,
            'rival': rival.nombre,
            'partido_id': partido.id,
            'fecha': partido.fecha,
        }

    return {
        'jugador': f"{fila['jugador__nombre']} {fila['jugador__apellido']}",
        'jugador_id': fila['jugador_id'],
        'numero': fila['jugador__numero'],
        'equipo': fila['jugador__equipo__nombre'],
        'equipo_id': fila['jugador__equipo_id'],
        'categoria': fila['jugador__equipo__categoria__nombre'],
        'liga': fila['jugador__equipo__liga__nombre'],
        'goles': fila['total_goles'],
        'asistencias': fila['total_asistencias'],
        'partidos': fila['partidos'],
        'aporte': fila['aporte'],
        'destacado': destacado,
        # El equipo entero y no solo su nombre: `values()` devuelve diccionarios
        # y la plantilla necesita `escudo_url`, que es una propiedad del modelo.
        # Se pide el objeto —una consulta— en vez de rearmar el monograma aca:
        # si el club tiene escudo subido, el monograma seria el escudo equivocado.
        'club': Equipo.objects.filter(pk=fila['jugador__equipo_id']).first(),
    }


def torneos():
    """Las categorias en juego, con en que punto va cada una.

    Se agrupan en una sola pasada por partidos: llamar a una funcion de resumen
    por categoria seria una consulta por cada una.
    """
    conteos = {
        fila['categoria']: fila
        for fila in Partido.objects
        .filter(categoria__liga__in=_ligas_publicas())
        .values('categoria')
        .annotate(
            total=Count('id'),
            jugados=Count('id', filter=Q(estado=Partido.ESTADO_FINALIZADO)),
        )
    }

    salida = []
    for categoria in (Categoria.objects
                      .filter(liga__in=_ligas_publicas(), activa=True, cerrada=False)
                      .select_related('liga')
                      .annotate(n_equipos=Count('equipos'))
                      .order_by('liga__nombre', 'nombre')):
        datos = conteos.get(categoria.id, {'total': 0, 'jugados': 0})
        total, jugados = datos['total'], datos['jugados']
        salida.append({
            'categoria': categoria,
            'equipos': categoria.n_equipos,
            'jugados': jugados,
            'total': total,
            # Al paso de 5 de las clases `.ancho-N`: las barras de este
            # proyecto no llevan la medida en un `style` inline.
            'avance': a_paso(jugados * 100 / total) if total else 0,
            # Sin partidos generados el torneo todavia no arranco: se dice eso y
            # no un 0 % que se lee como si fuera a empezar hoy.
            'estado': 'Por comenzar' if not total else (
                'Terminando' if jugados >= total else 'En juego'),
        })
    return salida


def campeones(tope=4):
    """Los ultimos campeones, para la vitrina resumida de la portada."""
    return list(Palmares.objects.select_related('categoria', 'categoria__liga')
                .order_by('-fecha_cierre')[:tope])


# Cuantos equipos puede seguir alguien. Es un tope de cordura contra una lista
# armada a mano en la direccion, no una regla de negocio.
MAXIMO_SEGUIDOS = 20


def de_mis_equipos(ids, tope_por_equipo=3):
    """Los proximos partidos de los equipos que el visitante sigue.

    Los ids llegan del navegador —el visitante no tiene cuenta, asi que lo que
    sigue se guarda en su propio dispositivo—, o sea que **no son de fiar**: se
    filtran a numeros, se acotan a `MAXIMO_SEGUIDOS` y se piden acotados a las
    ligas publicas. Alguien que escriba ids a mano no llega a nada que no fuera
    ya publico.

    Devuelve una lista de {equipo, partidos}, en el orden en que se siguieron.
    """
    limpios = []
    for crudo in list(ids)[:MAXIMO_SEGUIDOS]:
        texto = str(crudo).strip()
        if texto.isdigit():
            limpios.append(int(texto))
    if not limpios:
        return []

    equipos = {
        e.id: e for e in Equipo.objects
        .filter(pk__in=limpios, liga__in=_ligas_publicas())
        .select_related('categoria', 'categoria__liga', 'liga')
    }
    if not equipos:
        return []

    # Todos los partidos de todos los equipos en una sola consulta, y se
    # reparten en Python: una consulta por equipo seria una por cada estrella.
    partidos = list(_con_todo(Partido.objects.filter(
        Q(equipo_local_id__in=equipos) | Q(equipo_visitante_id__in=equipos),
        estado__in=Partido.ESTADOS_POR_JUGARSE,
        fecha__gte=timezone.now(),
    )).order_by('fecha'))

    salida = []
    for equipo_id in limpios:
        equipo = equipos.get(equipo_id)
        if equipo is None:
            continue   # lo siguio y despues se elimino, o no es publico
        suyos = [p for p in partidos
                 if equipo_id in (p.equipo_local_id, p.equipo_visitante_id)]
        salida.append({'equipo': equipo, 'partidos': suyos[:tope_por_equipo]})
    return salida


def franja():
    """La tira de marcadores que va arriba de todo, como en un sitio deportivo.

    Es lo primero que mira cualquiera que entra: que se juega ahora y como va.
    Si hoy no hay nada, muestra lo que viene, para que la franja nunca quede
    vacia ocupando lugar.

    Devuelve (titulo, partidos) porque el encabezado cambia con el contenido:
    decir "Hoy" arriba de partidos de la semana que viene seria mentir.
    """
    de_hoy = partidos_de_hoy(tope=20)
    if de_hoy:
        return 'Hoy', de_hoy
    return 'Próximos', proximos(tope=20)


def todo():
    """Arma el contexto completo de la portada de una sola vez."""
    from apps.torneos import palmares
    from apps.usuarios.estaticos import url_estatico

    titulo_franja, partidos_franja = franja()
    return {
        # La copa de verdad, la misma que usa la vitrina, en vez del emoji: un
        # 🏆 se dibuja distinto en cada sistema y al lado del resto de la
        # pantalla se ve como un carácter suelto, no como un trofeo.
        # La ruta vive en palmares.py, que es donde se declara el arte.
        'imagen_copa': url_estatico(
            dict((clave, imagen) for clave, _, imagen in palmares.TROFEOS_EQUIPO)['campeon']),
        'franja_titulo': titulo_franja,
        'franja': partidos_franja,
        'cifras': cifras(),
        'partidos_hoy': partidos_de_hoy(),
        'proximos': proximos(),
        'destacado': partido_destacado(),
        'resultados': ultimos_resultados(),
        'goleadores': goleadores(),
        'asistidores': asistidores(),
        'vallas': vallas(),
        'figura': jugador_del_momento(),
        'torneos': torneos(),
        'campeones': campeones(),
        'dias_semana': DIAS_DE_LA_SEMANA,
    }
