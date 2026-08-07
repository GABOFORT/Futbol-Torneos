"""La grilla del calendario mensual.

Separado de la vista porque es calculo puro sobre fechas: recibe los partidos y
devuelve las semanas del mes ya armadas, con los dias de relleno que hacen falta
para que el mes empiece en su dia de la semana correcto.

La semana arranca en **lunes**, como se usa en Mexico y en el resto de los
paises de habla hispana. `calendar` de Python arranca en lunes por defecto, asi
que no hay que configurarlo, pero conviene dejarlo dicho.
"""
import calendar
import datetime

# Cuantos meses se puede ir hacia atras y hacia adelante desde el actual. Es
# para no ofrecer flechas que llevan a meses vacios para siempre.
MESES_ALREDEDOR = 24

MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]

DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def limites(anio, mes):
    """El primer y el ultimo dia del mes, para acotar la consulta."""
    primero = datetime.date(anio, mes, 1)
    ultimo = datetime.date(anio, mes, calendar.monthrange(anio, mes)[1])
    return primero, ultimo


def leer_mes(texto, hoy):
    """Interpreta el 'AAAA-MM' que llega por la URL. Sin nada valido, el mes actual.

    No se confia en el parametro: llega de la barra de direcciones y un mes 13 o
    un año 99999 harian reventar `datetime`.
    """
    try:
        anio, mes = texto.split('-')
        fecha = datetime.date(int(anio), int(mes), 1)
    except (AttributeError, ValueError):
        return hoy.year, hoy.month

    # Un rango razonable alrededor de hoy: mas lejos no hay datos y solo sirve
    # para que alguien se pierda navegando meses vacios.
    if abs((fecha.year - hoy.year) * 12 + fecha.month - hoy.month) > MESES_ALREDEDOR:
        return hoy.year, hoy.month
    return fecha.year, fecha.month


def vecino(anio, mes, salto):
    """El mes anterior o el siguiente, como 'AAAA-MM'."""
    indice = (anio * 12 + mes - 1) + salto
    return f'{indice // 12}-{indice % 12 + 1:02d}'


def armar(anio, mes, partidos, hoy):
    """Las semanas del mes, cada una con sus siete dias.

    Cada dia es {fecha, dia, del_mes, es_hoy, partidos}. Los dias de relleno
    —los del mes anterior y el siguiente que completan la primera y la ultima
    semana— vienen con `del_mes=False` para poder atenuarlos.
    """
    por_dia = {}
    for partido in partidos:
        if partido.fecha:
            por_dia.setdefault(partido.fecha.date(), []).append(partido)

    semanas = []
    for semana in calendar.Calendar().monthdatescalendar(anio, mes):
        semanas.append([{
            'fecha': dia,
            'dia': dia.day,
            'del_mes': dia.month == mes,
            'es_hoy': dia == hoy,
            'partidos': por_dia.get(dia, []),
        } for dia in semana])
    return semanas


def nombre(anio, mes):
    return f'{MESES[mes - 1].capitalize()} {anio}'
