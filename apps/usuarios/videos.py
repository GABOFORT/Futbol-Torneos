from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

TOPE_VIDEO_MB = 25

AYUDA_VIDEO = (f'Opcional. MP4 o WebM de hasta {TOPE_VIDEO_MB} MB. '
               'Aparece como un botón dentro de su ficha.')

FIRMA_WEBM = b'\x1a\x45\xdf\xa3'


def validar_peso_de_video(archivo):
    if archivo.size > TOPE_VIDEO_MB * 1024 * 1024:
        raise ValidationError(
            f'El video pesa más de {TOPE_VIDEO_MB} MB. Recórtalo o bájale la calidad y vuelve a subirlo.')


def validar_contenido_de_video(archivo):
    archivo.seek(0)
    cabecera = archivo.read(12)
    archivo.seek(0)
    if cabecera[4:8] != b'ftyp' and not cabecera.startswith(FIRMA_WEBM):
        raise ValidationError('El archivo no es un video MP4 o WebM válido.')


class EntradaVideo(forms.ClearableFileInput):
    template_name = 'django/forms/widgets/clearable_video_input.html'

    def __init__(self, attrs=None):
        super().__init__({'accept': 'video/mp4,video/webm', **(attrs or {})})


class CampoVideo(forms.FileField):
    widget = EntradaVideo
    default_validators = [
        FileExtensionValidator(('mp4', 'webm'), 'Sube el video en formato MP4 o WebM.'),
        validar_peso_de_video,
        validar_contenido_de_video,
    ]
