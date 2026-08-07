import io
import os

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image

# Lado mayor al que se reduce toda imagen subida. En pantalla la mas grande se
# muestra a 80 px, asi que 512 deja margen de sobra incluso en pantallas retina
# y para una futura vista ampliada.
TOPE_PX = 512

# Tope aparte para las imagenes que se muestran a pantalla completa, hoy solo la
# portada de la liga. Con TOPE_PX una portada se guardaria a 512 px y al
# estirarse a todo el ancho se veria pixelada — y pareceria culpa de la imagen
# que subio el usuario, no de la reduccion. 1920 cubre un monitor Full HD; mas
# que eso solo agrega peso, porque encima lleva un velo y un desenfoque.
TOPE_PANTALLA_PX = 1920


def achicar_imagen(campo, tope=TOPE_PX):
    """Reduce y recomprime una imagen recien subida, antes de guardarla.

    Una foto sacada con el celular pesa varios MB; sin esto cada logo, escudo
    o foto de jugador entra al servidor a tamano completo y las paginas que los
    listan se vuelven lentisimas.

    Solo actua sobre subidas nuevas: si el campo ya apunta a un archivo
    guardado, no se vuelve a tocar (recomprimir en cada save degradaria la
    imagen un poco mas cada vez).
    """
    if not campo:
        return
    try:
        archivo = getattr(campo, 'file', None)
    except (FileNotFoundError, OSError):
        # El registro apunta a un archivo que ya no esta en disco: se borro a
        # mano, o cambio MEDIA_ROOT y la imagen quedo en la carpeta anterior.
        # Pedirle `.file` a un FieldFile asi lanza FileNotFoundError, y sin este
        # try eso tumbaba el guardado entero — no se podia ni editar el nombre
        # de la liga hasta volver a subir la imagen. Mismo criterio que el except
        # de mas abajo: un problema con el archivo no bloquea guardar el registro.
        return
    if not isinstance(archivo, UploadedFile):
        return

    try:
        imagen = Image.open(campo.file)
        imagen.load()
    except Exception:
        # Un archivo corrupto o un formato raro no deberia impedir guardar el
        # registro; el validador del formulario ya filtro lo que no es imagen.
        return

    transparencia = imagen.mode in ('RGBA', 'LA') or (
        imagen.mode == 'P' and 'transparency' in imagen.info
    )
    if transparencia:
        formato, extension = 'PNG', '.png'
        imagen = imagen.convert('RGBA')
    else:
        formato, extension = 'JPEG', '.jpg'
        imagen = imagen.convert('RGB')

    imagen.thumbnail((tope, tope), Image.LANCZOS)

    buffer = io.BytesIO()
    if formato == 'PNG':
        imagen.save(buffer, 'PNG', optimize=True)
    else:
        imagen.save(buffer, 'JPEG', quality=85, optimize=True, progressive=True)

    base = os.path.splitext(os.path.basename(campo.name))[0]
    campo.save(base + extension, ContentFile(buffer.getvalue()), save=False)
