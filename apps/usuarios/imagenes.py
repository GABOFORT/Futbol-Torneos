import io
import os

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image

TOPE_PX = 512

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
        return
    if not isinstance(archivo, UploadedFile):
        return

    try:
        imagen = Image.open(campo.file)
        imagen.load()
    except Exception:
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
