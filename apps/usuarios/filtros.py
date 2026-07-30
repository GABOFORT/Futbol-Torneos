from django.db.models import Q


def buscar(queryset, termino, campos):
    """Filtra por texto libre sobre varios campos a la vez.

    Cada palabra tiene que aparecer en algun campo, pero no necesariamente en
    el mismo: buscar 'rocio gallardo' encuentra a quien tiene 'Rocio' de nombre
    y 'Gallardo' de apellido. Si se buscara la frase entera en cada campo por
    separado no la encontraria, porque ninguno la contiene completa.

    Usa unaccent para que 'Garduno' encuentre a 'Garduño' y 'Lopez' a 'López':
    de otro modo Postgres ignora mayusculas pero no acentos, y con nombres en
    espanol eso falla seguido.
    """
    palabras = (termino or '').split()
    if not palabras:
        return queryset
    for palabra in palabras:
        condicion = Q()
        for campo in campos:
            condicion |= Q(**{f'{campo}__unaccent__icontains': palabra})
        queryset = queryset.filter(condicion)
    # Buscar sobre un campo de otra tabla arma un JOIN, y con varias filas
    # relacionadas el mismo registro aparece repetido.
    if any('__' in campo for campo in campos):
        queryset = queryset.distinct()
    return queryset


def campo_texto(nombre, etiqueta, valor, ayuda=''):
    return {'tipo': 'texto', 'nombre': nombre, 'etiqueta': etiqueta, 'valor': valor or '', 'ayuda': ayuda}


def campo_opciones(nombre, etiqueta, valor, opciones, vacio='Todas'):
    """opciones: iterable de (valor, etiqueta)."""
    return {
        'tipo': 'opciones',
        'nombre': nombre,
        'etiqueta': etiqueta,
        'valor': str(valor or ''),
        'vacio': vacio,
        'opciones': [(str(v), str(e)) for v, e in opciones],
    }


def campo_oculto(nombre, valor):
    """Viaja con el formulario sin dibujarse.

    Sirve para lo que se elige por fuera de la barra, como la jornada, que se
    selecciona con las pastillas y no con un desplegable.
    """
    return {'tipo': 'oculto', 'nombre': nombre, 'valor': str(valor or ''), 'etiqueta': '', 'ayuda': ''}


def hay_filtros(campos):
    """Si el usuario aplico alguno, para decidir si mostrar el boton Limpiar."""
    return any(c['valor'] for c in campos)
