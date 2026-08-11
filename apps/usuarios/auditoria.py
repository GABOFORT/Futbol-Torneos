"""Rastro de los hechos que importan para la seguridad.

Escribe en `logs/seguridad.log` a traves del logger `futbol.auditoria`
(configurado en LOGGING, futbol/settings.py).

Vive en un modulo propio y no suelto en cada vista para que todas las lineas
salgan con el mismo formato: sin eso, buscar "quien borro el equipo" obligaria a
recordar como se escribio en cada lugar.

Que NO va aca:
  - Los intentos fallidos de login y los bloqueos: ya los emite django-axes por
    su cuenta, y LOGGING los manda a este mismo archivo. Duplicarlos solo haria
    mas dificil de leer la bitacora.
  - Contrasenas, ni siquiera hasheadas, ni tokens de sesion. Una bitacora se
    copia, se manda por correo y se respalda; lo que no este ahi no se filtra.
"""

import logging

registro = logging.getLogger('futbol.auditoria')


def ip_de(request):
    """La IP de quien pide, contemplando que IIS esta delante.

    Con el proxy en medio, REMOTE_ADDR es siempre 127.0.0.1 —la conexion TCP la
    abre IIS, no el visitante—, asi que registrar solo eso no sirve de nada:
    todas las lineas dirian lo mismo. La de verdad viaja en X-Forwarded-For.

    Se toma el PRIMER valor de la lista: cada proxy va agregando el suyo al
    final, asi que el primero es el cliente original.

    Ojo con este dato: es una cabecera y el cliente puede escribir lo que quiera.
    Para dejar rastro en la bitacora esta bien —que es para lo unico que se usa
    aca—, pero NO sirve para tomar decisiones de permisos ni para bloquear.
    """
    if request is None:
        return '?'
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if reenviada:
        return reenviada.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '?')
