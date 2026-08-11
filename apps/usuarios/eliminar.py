from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .auditoria import ip_de, registro as auditoria


def entrenadores_sin_equipo_tras_borrar(equipos):
    """Los entrenadores que se quedarian sin ningun equipo al borrar `equipos`.

    Un entrenador existe para dirigir: si se elimina la liga donde dirigia, su
    cuenta no tiene para que seguir. Antes quedaba viva y sin equipos, juntando
    cuentas fantasma en el listado (llegaron a ser 197).

    **Se borra por lo que le queda, no por lo que se va.** Un mismo entrenador
    puede dirigir en dos ligas distintas: si tiene equipos fuera de los que se
    estan borrando, la cuenta se conserva. Ademas, `Equipo.entrenador` es
    PROTECT, asi que borrarlo igual habria reventado.

    Tampoco alcanza a los recien creados: solo entran los que hoy dirigen alguno
    de los equipos que se van. Un entrenador dado de alta y todavia sin equipo
    asignado no se toca.
    """
    from .models import Usuario

    ids = list(equipos.values_list('pk', flat=True))
    if not ids:
        return Usuario.objects.none()

    candidatos = Usuario.objects.filter(
        role=Usuario.ROLE_ENTRENADOR, equipos__pk__in=ids,
    ).distinct()
    # Los que conservan algun equipo fuera de la tanda que se borra se quedan.
    sin_nada = [u.pk for u in candidatos if not u.equipos.exclude(pk__in=ids).exists()]
    return Usuario.objects.filter(pk__in=sin_nada)


def vista_eliminar(request, instancia, etiqueta, url_listado, mensaje_ok, arrastra=(), bloqueo='',
                   antes_de_borrar=None):
    """Flujo comun de borrado para liga, categoria, equipo y usuario.

    GET muestra la confirmacion con lo que se va a llevar por delante; POST
    elimina. Vive en un solo lugar para que las cuatro apps se comporten igual.

    arrastra:        lineas de texto con lo que se borra en cascada.
    bloqueo:         motivo por el que NO se puede borrar. Si viene, no hay boton.
    antes_de_borrar: callable que limpia lo que esta protegido por PROTECT.
                     Corre en la misma transaccion que el borrado.
    """
    modal = request.GET.get('modal') == '1'

    if request.method == 'POST':
        if bloqueo:
            messages.error(request, bloqueo)
        else:
            # Se guardan ANTES de borrar: despues del delete() la instancia se
            # queda sin pk y la linea de la bitacora saldria con "None".
            identificador, quien, desde = instancia.pk, request.user, ip_de(request)
            try:
                # Todo junto o nada: sin la transaccion, un error a mitad de
                # camino dejaria la liga sin parte de sus equipos.
                with transaction.atomic():
                    if antes_de_borrar:
                        antes_de_borrar()
                    instancia.delete()
                # WARNING y no INFO: un borrado es irreversible y arrastra en
                # cascada (una liga se lleva equipos, jugadores y partidos). Es
                # la linea que se va a buscar el dia que alguien pregunte "quien
                # borro esto", asi que tiene que destacar entre el resto.
                auditoria.warning(
                    'BORRADO %s (id=%s) por usuario=%s (id=%s) desde ip=%s',
                    etiqueta, identificador, quien.username, quien.pk, desde,
                )
                messages.success(request, mensaje_ok)
            except ProtectedError:
                auditoria.info(
                    'BORRADO RECHAZADO %s (id=%s) por usuario=%s desde ip=%s: registros asociados',
                    etiqueta, identificador, quien.username, desde,
                )
                # Red de seguridad: el chequeo previo ya deberia haberlo frenado,
                # pero si alguien crea un equipo justo entre el GET y el POST
                # conviene un mensaje y no la pantalla de error de Django.
                messages.error(request, f'No se pudo eliminar {etiqueta}: tiene registros asociados.')
        if modal:
            return JsonResponse({'success': True})
        return redirect(url_listado)

    contexto = {
        'objeto': etiqueta,
        'arrastra': arrastra,
        'bloqueo': bloqueo,
        'en_modal': modal,
        'cancel_url': url_listado,
    }
    plantilla = '_modal_confirmar.html' if modal else '_confirmar_pagina.html'
    return render(request, plantilla, contexto)
