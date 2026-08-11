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

    La usan las bitacoras de este modulo y tambien django-axes, via
    AXES_CLIENT_IP_CALLABLE en settings.py. Es el unico lugar del proyecto donde
    se decide "quien es el que pide", a proposito: cuando estaba solo en la
    bitacora, axes resolvia la IP por su cuenta y le salia otra cosa.

    POR QUE NO ALCANZA REMOTE_ADDR. Con el proxy en medio vale siempre
    127.0.0.1: la conexion TCP la abre IIS, no el visitante. Eso hacia que todas
    las lineas de la bitacora dijeran lo mismo, y algo peor —el 11/08/2026 dejo
    el sitio entero sin poder entrar—: axes bloqueaba "esa IP", que era la de
    todos los usuarios a la vez.

    SE PUEDE CONFIAR EN LA CABECERA, y esto es lo que hay que entender antes de
    tocar esta funcion. Normalmente X-Forwarded-For la escribe el cliente y se
    puede inventar. Aca no: el web.config la SOBREESCRIBE con {REMOTE_ADDR} en
    cada peticion (regla ReverseProxyInboundRule1), asi que lo que mande el
    visitante se descarta. Si algun dia se quita esa linea del web.config, esto
    pasa a ser falsificable y el bloqueo de axes se esquiva cambiando la
    cabecera. Las dos piezas van juntas o no van.

    POR QUE UN NOMBRE RARO Y NO X-Forwarded-For. Porque Waitress BORRA toda
    cabecera que empiece por "X-Forwarded-" si no se le declara un proxy de
    confianza al arrancar (clear_untrusted_proxy_headers vale True de fabrica).
    Se comprobo el 11/08/2026 interceptando lo que Waitress le pasa a Django: la
    cabecera salia de IIS y no llegaba.

    Se resolvio con un nombre propio en vez de con el flag de Waitress porque
    aca el servidor se levanta a mano (iniciar_produccion.bat, sin servicio de
    Windows): un flag olvidado en el arranque romperia el bloqueo de axes sin
    que nadie se entere. Una cabecera con otro nombre funciona se arranque como
    se arranque.

    EL PRIMER VALOR, no el ultimo: cada proxy agrega el suyo al final, asi que el
    primero es el que puso IIS. ARR ademas agrega una entrada CON EL PUERTO
    pegado ("192.168.1.201:63076"); por eso se corta por los dos puntos.
    """
    if request is None:
        return '?'
    # X-Forwarded-For queda como respaldo por si algun dia se pone Waitress
    # detras de un proxy de confianza; hoy nunca llega.
    for cabecera in ('HTTP_X_IP_CLIENTE', 'HTTP_X_FORWARDED_FOR'):
        valor = request.META.get(cabecera, '')
        if valor:
            candidata = valor.split(',')[0].strip()
            break
    else:
        candidata = request.META.get('REMOTE_ADDR', '') or '?'
    # Solo en IPv4: una IPv6 lleva dos puntos de por si y cortarla la destruiria.
    if candidata.count(':') == 1:
        candidata = candidata.split(':')[0]
    return candidata
