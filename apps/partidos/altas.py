"""Alta de un equipo con el calendario ya generado.

Ventana fija para todo el sistema: de la jornada 2 a la 4. Se cierra en cuanto
se juega el primer partido de la jornada 4.

Los partidos que ya existen no se tocan. Al equipo nuevo se le arman los suyos:
primero en los descansos que ya hay, y lo que sobre en jornadas nuevas al final.
"""
from django.db.models import Max

from .models import Partido

PRIMERA_JORNADA = 2
ULTIMA_JORNADA = 4


def hay_calendario(categoria):
    return _regulares(categoria).exists()


def _regulares(categoria):
    return Partido.objects.filter(categoria=categoria, fase=Partido.FASE_REGULAR)


def jornadas_tomadas(categoria):
    """Las jornadas que ya no admiten cambios porque se jugo algo en ellas."""
    return set(
        _regulares(categoria)
        .filter(estado=Partido.ESTADO_FINALIZADO)
        .values_list('jornada', flat=True)
    )


def jornada_de_ingreso(categoria):
    """En que jornada entraria un equipo nuevo, o None si no hay calendario."""
    if not hay_calendario(categoria):
        return None
    tomadas = jornadas_tomadas(categoria)
    siguiente = max(tomadas) + 1 if tomadas else PRIMERA_JORNADA
    return max(PRIMERA_JORNADA, siguiente)


def motivo_para_no_agregar(categoria):
    """Por que esta categoria ya no admite equipos nuevos, o '' si si admite.

    Solo habla de la ventana. El cupo y la inscripcion los sigue resolviendo
    `Categoria.motivo_para_no_recibir_equipos()`.
    """
    if not hay_calendario(categoria):
        return ''
    jornada = jornada_de_ingreso(categoria)
    if jornada > ULTIMA_JORNADA:
        return (
            f'Ya se jugó la jornada {ULTIMA_JORNADA}. Un equipo nuevo entraría en la '
            f'jornada {jornada} y las altas se cierran en la {ULTIMA_JORNADA}.'
        )
    return ''


def puede_agregar(categoria):
    return not motivo_para_no_agregar(categoria)


def _rivales(categoria, equipo):
    return list(categoria.equipos.exclude(pk=equipo.pk).order_by('nombre'))


def _ocupados_por_jornada(categoria):
    ocupados = {}
    for local, visitante, jornada in _regulares(categoria).values_list(
            'equipo_local_id', 'equipo_visitante_id', 'jornada'):
        libres = ocupados.setdefault(jornada, set())
        libres.add(local)
        libres.add(visitante)
    return ocupados


def plan(categoria, equipo):
    """Que partidos se le crearian al equipo, sin crear nada.

    Devuelve el reparto entre jornadas que ya existen y jornadas nuevas.
    """
    jornada = jornada_de_ingreso(categoria)
    if jornada is None:
        return None

    rivales = _rivales(categoria, equipo)
    encuentros = [rival for rival in rivales for _ in range(categoria.vueltas)]
    ocupados = _ocupados_por_jornada(categoria)
    ultima = _regulares(categoria).aggregate(tope=Max('jornada'))['tope'] or 0

    en_huecos, pendientes = [], list(encuentros)
    for numero in range(jornada, ultima + 1):
        if not pendientes:
            break
        libres = [r for r in pendientes if r.id not in ocupados.get(numero, set())]
        if not libres:
            continue
        rival = libres[0]
        pendientes.remove(rival)
        en_huecos.append((numero, rival))

    return {
        'jornada_ingreso': jornada,
        'en_huecos': en_huecos,
        'pendientes': pendientes,
        'total': len(encuentros),
        'ultima_jornada': ultima,
    }


def agregar(categoria, equipo):
    """Crea los partidos del equipo nuevo. Devuelve el plan que se aplico.

    Los que no entran en ningun descanso quedan como partidos pendientes: no se
    inventan jornadas nuevas para uno o dos encuentros. Se juegan aparte, que es
    lo que pasa de verdad cuando un equipo se suma tarde.
    """
    reparto = plan(categoria, equipo)
    if reparto is None:
        return None

    encuentros = (
        [(jornada, rival, False) for jornada, rival in reparto['en_huecos']]
        + [(reparto['ultima_jornada'], rival, True) for rival in reparto['pendientes']]
    )

    partidos = []
    for indice, (jornada, rival, pendiente) in enumerate(encuentros):
        de_local = indice % 2 == 0
        partidos.append(Partido(
            categoria=categoria,
            jornada=jornada,
            fuera_de_jornada=pendiente,
            equipo_local=equipo if de_local else rival,
            equipo_visitante=rival if de_local else equipo,
        ))
    Partido.objects.bulk_create(partidos)

    equipo.jornada_ingreso = reparto['jornada_ingreso']
    equipo.save(update_fields=['jornada_ingreso'])
    return reparto


def resumen(reparto):
    """El aviso que se le muestra al admin, ya redactado."""
    if reparto is None:
        return ''
    partes = [
        f'Entra en la jornada {reparto["jornada_ingreso"]} con '
        f'{reparto["total"]} partido(s).'
    ]
    if reparto['en_huecos']:
        partes.append(
            f'{len(reparto["en_huecos"])} aprovechan jornadas que ya existen.')
    if reparto['pendientes']:
        partes.append(
            f'{len(reparto["pendientes"])} quedan como partidos pendientes, sin jornada: '
            f'se programan aparte.')
    partes.append('No se movió ningún partido ya programado.')
    return ' '.join(partes)
