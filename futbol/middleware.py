from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed


class NoCacheEnDesarrolloMiddleware:
    """Evita que el navegador sirva HTML viejo mientras se desarrolla.

    Con DEBUG=False lanza MiddlewareNotUsed en el arranque y Django lo saca de
    la cadena: en produccion no corre, no cuesta nada y el cacheo queda intacto.
    """

    def __init__(self, get_response):
        if not settings.DEBUG:
            raise MiddlewareNotUsed
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.get('Content-Type', '').startswith('text/html'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        return response
