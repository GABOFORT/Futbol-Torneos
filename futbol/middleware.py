class CabecerasDeCacheMiddleware:
    """Impide que el navegador se quede con una version vieja del HTML.

    Django no manda ninguna cabecera de cache en las respuestas: sin
    `Cache-Control`, sin `Last-Modified` y sin `ETag`, cada navegador decide por
    su cuenta cuanto tiempo se queda con la copia guardada. Eso hacia que dos
    equipos vieran cosas distintas al mismo tiempo — el 27/08/2026 un
    patrocinador recien cargado aparecia en Edge y en Brave, y no en el Chrome
    donde se venia trabajando, que tenia la pagina en cache.

    Solo se marca el HTML. Los estaticos siguen cacheandose todo lo que quieran,
    porque su direccion lleva pegada la fecha del archivo (`static_v`, ver
    apps/usuarios/estaticos.py): cuando el archivo cambia, cambia la URL.

    Un marcador, una tabla de posiciones o una alineacion valen para el momento
    en que se piden, asi que revalidar siempre es lo correcto: no se sirve nunca
    un resultado viejo.
    """

    TIPOS = ('text/html', 'application/json')

    REGLA = 'private, no-cache, max-age=0, must-revalidate'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.get('Content-Type', '').startswith(self.TIPOS):
            response['Cache-Control'] = self.REGLA
        return response
