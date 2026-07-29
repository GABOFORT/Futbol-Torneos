from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import redirect, render


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
            try:
                # Todo junto o nada: sin la transaccion, un error a mitad de
                # camino dejaria la liga sin parte de sus equipos.
                with transaction.atomic():
                    if antes_de_borrar:
                        antes_de_borrar()
                    instancia.delete()
                messages.success(request, mensaje_ok)
            except ProtectedError:
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
