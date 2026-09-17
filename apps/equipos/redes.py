"""Las redes sociales de un equipo o de una liga, y la regla que protege sus enlaces.

Cada red acepta solamente direcciones de su propio dominio. No es una cuestion
de prolijidad: el icono de Facebook le promete al visitante que va a abrir
Facebook, y si el campo aceptara cualquier direccion, alguien podria poner detras
de ese icono una pagina falsa que pida la contrasena. Un padre que confia en el
sitio de la liga le daria clic sin dudar.

Se exige `https` por el mismo motivo, y se mira el host real de la direccion —el
que resuelve el navegador— y no el texto: `https://instagram.com@sitio-falso.com`
empieza con "instagram.com" pero lleva a `sitio-falso.com`.
"""
from collections import namedtuple
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.deconstruct import deconstructible

RedSocial = namedtuple('RedSocial', 'campo etiqueta icono dominios ejemplo')

REDES = (
    RedSocial('red_instagram', 'Instagram', 'instagram',
              ('instagram.com',), 'https://instagram.com/tu_equipo'),
    RedSocial('red_facebook', 'Facebook', 'facebook',
              ('facebook.com', 'fb.com'), 'https://facebook.com/tu_equipo'),
    RedSocial('red_twitter', 'X (antes Twitter)', 'x',
              ('x.com', 'twitter.com'), 'https://x.com/tu_equipo'),
    RedSocial('red_tiktok', 'TikTok', 'tiktok',
              ('tiktok.com',), 'https://tiktok.com/@tu_equipo'),
)

CAMPOS = tuple(red.campo for red in REDES)

POR_CAMPO = {red.campo: red for red in REDES}

LARGO_MAXIMO = 300


@deconstructible
class EnlaceDeRed:
    """Valida que la direccion sea `https` y pertenezca a los dominios de la red."""

    def __init__(self, etiqueta, dominios):
        self.etiqueta = etiqueta
        self.dominios = tuple(dominios)

    def __call__(self, valor):
        partes = urlsplit(valor)
        host = (partes.hostname or '').lower()
        if partes.scheme != 'https' or not self._es_de_la_red(host):
            raise ValidationError(
                f'Pega el enlace de {self.etiqueta}: tiene que empezar con '
                f'https:// y ser de {" o ".join(self.dominios)}.',
                code='enlace_de_otra_red',
            )

    def _es_de_la_red(self, host):
        return any(host == dominio or host.endswith(f'.{dominio}')
                   for dominio in self.dominios)

    def __eq__(self, otro):
        return (isinstance(otro, EnlaceDeRed)
                and self.etiqueta == otro.etiqueta
                and self.dominios == otro.dominios)


def url_de_red(campo):
    """El campo del modelo para una red, con su validacion de dominio puesta."""
    red = POR_CAMPO[campo]
    return models.URLField(
        red.etiqueta,
        max_length=LARGO_MAXIMO,
        blank=True,
        validators=[EnlaceDeRed(red.etiqueta, red.dominios)],
    )


class ConRedesSociales:
    """Le da a un modelo con campos `red_*` la lista de las que tiene cargadas.

    La comparten el equipo y la liga —y un torneo por la liga que lleva
    detras—, asi que la regla de "cuales se muestran y en que orden" se escribe
    una sola vez.
    """

    @property
    def redes_sociales(self):
        """Las redes cargadas, en el orden fijo de `REDES`.

        Solo las que tienen enlace: quien no cargo ninguna no muestra nada, ni
        siquiera un hueco. Se resuelve como propiedad para que cualquier
        pantalla que ya tenga el objeto las pinte sin que su vista las prepare.
        """
        return [{'url': enlace, 'etiqueta': red.etiqueta, 'icono': red.icono}
                for red in REDES if (enlace := getattr(self, red.campo))]


def campo_de_red(modelo, campo):
    """El campo de formulario de una red, con su validacion de dominio puesta.

    `formfield()` no copia los validadores del modelo al formulario: en un
    `ModelForm` igual corren, porque Django valida la instancia antes de
    guardar, pero el alta de equipos y los formularios del torneo son `Form`
    normales y guardan con `objects.create()`, que no valida nada. Sin pasarlo
    aca, el candado de dominio quedaba solo en la edicion.
    """
    del_modelo = modelo._meta.get_field(campo)
    de_dominio = [v for v in del_modelo.validators if isinstance(v, EnlaceDeRed)]
    return del_modelo.formfield(validators=de_dominio)


class RedesSocialesMixin:
    """Las redes en un formulario, compartidas por el equipo, la liga y el torneo.

    Los campos salen del modelo: los `Form` normales los toman con
    `campo_de_red`, que les pone el validador de dominio, y el `ModelForm` los
    recibe por `Meta.fields` y los valida al limpiar la instancia. Llevan el
    prefijo `red_` para que el formulario generico los salte y se pinten juntos
    en su propia seccion, igual que los titulos.
    """

    CAMPOS_DE_REDES = CAMPOS

    def _preparar_redes(self):
        for red in REDES:
            campo = self.fields.get(red.campo)
            if campo is None:
                continue
            campo.required = False
            campo.widget.attrs.update({
                'placeholder': red.ejemplo,
                'inputmode': 'url',
                'autocomplete': 'url',
                'spellcheck': 'false',
            })

    @property
    def campos_de_redes(self):
        return [{'campo': self[red.campo], 'etiqueta': red.etiqueta, 'icono': red.icono}
                for red in REDES if red.campo in self.fields]

    def redes_limpias(self):
        return {red.campo: self.cleaned_data.get(red.campo) or ''
                for red in REDES if red.campo in self.fields}
