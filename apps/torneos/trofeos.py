from django.db import transaction

from .models import Trofeo

TOPE = Trofeo.TOPE_POR_LIGA

LARGO_TITULO = Trofeo._meta.get_field('titulo').max_length

LARGO_DESCRIPCION = Trofeo._meta.get_field('descripcion').max_length


def de(liga):
    if liga is None or not liga.pk:
        return []
    return list(liga.trofeos.all())


def filas_guardadas(liga):
    return [
        {'id': trofeo.pk, 'indice': indice, 'titulo': trofeo.titulo,
         'descripcion': trofeo.descripcion, 'imagen': None, 'quitar_imagen': False,
         'vista_previa': trofeo.imagen_url if trofeo.propia else '',
         'nombre_archivo': ''}
        for indice, trofeo in enumerate(de(liga))
    ]


def leer(datos, archivos):
    indices = datos.getlist('trofeo_indice')
    identificadores = datos.getlist('trofeo_id')
    titulos = datos.getlist('trofeo_titulo')
    descripciones = datos.getlist('trofeo_descripcion')

    filas = []
    for posicion, indice in enumerate(indices):
        titulo = _texto(titulos, posicion, LARGO_TITULO)
        descripcion = _texto(descripciones, posicion, LARGO_DESCRIPCION)
        imagen = archivos.get(f'trofeo_imagen_{indice}') if archivos else None
        quitar = datos.get(f'trofeo_sin_imagen_{indice}') == '1'
        identificador = _entero(identificadores, posicion)

        if not (titulo or descripcion or imagen or identificador):
            continue

        filas.append({
            'id': identificador,
            'indice': indice,
            'titulo': titulo,
            'descripcion': descripcion,
            'imagen': imagen,
            'quitar_imagen': quitar,
            'vista_previa': '',
            'nombre_archivo': imagen.name if imagen else '',
        })
    return filas


def _texto(valores, posicion, largo):
    if posicion >= len(valores):
        return ''
    return ' '.join(valores[posicion].split())[:largo]


def _entero(valores, posicion):
    if posicion >= len(valores):
        return None
    valor = valores[posicion].strip()
    return int(valor) if valor.isdigit() else None


def revisar(filas):
    problemas = []
    if len(filas) > TOPE:
        problemas.append(
            f'Puedes cargar hasta {TOPE} trofeos y estás mandando {len(filas)}.')

    vistos = set()
    for fila in filas:
        fila['error'] = ''
        if not fila['titulo']:
            fila['error'] = 'Ponle un nombre a este trofeo o quita la fila con la ✕.'
            continue
        clave = fila['titulo'].lower()
        if clave in vistos:
            fila['error'] = 'Ya cargaste otro trofeo con este mismo nombre.'
        vistos.add(clave)

    marcadas = sum(1 for fila in filas if fila['error'])
    if marcadas:
        problemas.append(
            'Revisa el trofeo marcado en rojo más abajo.' if marcadas == 1 else
            f'Revisa los {marcadas} trofeos marcados en rojo más abajo.')
    return problemas


@transaction.atomic
def guardar(liga, filas):
    conservados = {fila['id'] for fila in filas if fila['id']}
    liga.trofeos.exclude(pk__in=conservados).delete()

    existentes = {t.pk: t for t in liga.trofeos.filter(pk__in=conservados)}

    for orden, fila in enumerate(filas, start=1):
        trofeo = existentes.get(fila['id']) or Trofeo(liga=liga)
        trofeo.titulo = fila['titulo']
        trofeo.descripcion = fila['descripcion']
        trofeo.orden = orden
        if fila['imagen']:
            trofeo.imagen = fila['imagen']
        elif fila['quitar_imagen']:
            trofeo.imagen = None
        trofeo.save()


class TrofeosMixin:
    trofeos_activos = True

    trofeos_tope = TOPE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trofeos = (leer(self.data, self.files) if self.is_bound
                        else filas_guardadas(self.liga_de_trofeos))

    @property
    def liga_de_trofeos(self):
        return None

    def clean(self):
        datos = super().clean()
        for problema in revisar(self.trofeos):
            self.add_error(None, problema)
        return datos

    def guardar_trofeos(self, liga):
        guardar(liga, self.trofeos)
