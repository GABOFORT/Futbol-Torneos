"""Anchos y alturas de las barras que se dibujan en las plantillas.

En este proyecto **una barra nunca lleva su medida en un `style` inline**. Va con
una clase `.ancho-N` o `.alto-N`, que existen de 5 en 5 en `base.html` y en
`portada.css`. El motivo esta escrito en `.vscode/settings.json`: una etiqueta
de Django dentro de un atributo `style` hace tropezar al validador de CSS del
editor, y la respuesta del proyecto fue arreglar las plantillas en vez de apagar
la validacion.

Como las plantillas de Django no hacen cuentas, el redondeo al paso se resuelve
aca y viaja ya listo en el contexto.

Vive en `usuarios` junto al resto de las utilidades transversales (`estaticos`,
`imagenes`, `monograma`, `filtros`): lo usan el perfil de equipo, la portada,
el panorama de liga y los graficos.
"""

PASO = 5


def a_paso(valor):
    """Redondea al paso de las clases. 37 -> 35, 38 -> 40."""
    return round(valor / PASO) * PASO


def reparto(cantidades, total):
    """Varias barras que juntas tienen que dar 100 %.

    Redondear cada tramo por su cuenta da 95 o 105 seguido, y en una barra
    partida en tramos ese punto de mas la desborda. El sobrante se le suma al
    tramo mas grande, que es donde menos se nota.

    `cantidades` es una lista de (clave, cantidad). Devuelve {clave: ancho}.
    """
    if not total:
        return {clave: 0 for clave, _ in cantidades}

    anchos = {clave: a_paso(cantidad * 100 / total) for clave, cantidad in cantidades}
    sobrante = 100 - sum(anchos.values())
    if sobrante and anchos:
        mayor = max(anchos, key=lambda clave: anchos[clave])
        anchos[mayor] += sobrante
    return anchos
