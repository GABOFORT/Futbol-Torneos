"""El apartado de torneos: alta, listado, categorías, grupos y cuadro.

Vive aparte de las ligas aunque se apoye en ellas: quien entra aca esta armando
un evento, no una temporada.

Hay dos formatos. En `directa` el torneo lleva una sola categoria y el cuadro
sale de un sorteo. En `grupos` lleva las categorias que el administrador cree
—una por edad o division—, cada una con sus grupos, su tabla y su liguilla, sin
cruzarse entre ellas.
"""
from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.equipos.models import Equipo
from apps.estadisticas import tabla
from apps.jugadores.models import Jugador
from apps.partidos import grupos, relampago
from apps.partidos.models import Partido
from apps.usuarios.eliminar import entrenadores_sin_equipo_tras_borrar, vista_eliminar
from apps.usuarios.forms import StyledFormMixin
from apps.usuarios.models import Usuario
from apps.usuarios.permissions import (
    admin_liga_required, superadmin_required, torneos_administrados, torneos_visibles,
)

from .models import Categoria, Liga, Palmares, Torneo

CATEGORIA_UNICA = 'General'


CLAVES_POR_GRUPOS = ','.join(
    clave for clave, _, formato, _ in Torneo.MODALIDADES
    if formato == Torneo.FORMATO_GRUPOS)


def aplicar_imagen(objeto, campo, valor):
    """Guarda lo que el usuario hizo con una imagen que ya existía.

    Un campo de archivo con `initial` puesto devuelve tres cosas distintas:
    `False` cuando se palomeó "Eliminar", el archivo nuevo cuando se subió uno,
    y el que ya estaba cuando no se tocó nada. Sin distinguir el `False`, el
    botón de eliminar no borra.
    """
    if valor is False:
        setattr(objeto, campo, None)
    elif valor:
        setattr(objeto, campo, valor)


class TorneoForm(StyledFormMixin, forms.Form):
    CAMPOS_OBLIGATORIOS = ('nombre', 'fecha', 'modalidad')
    CAMPOS_CAPITALIZAR = ('nombre',)

    nombre = forms.CharField(max_length=150, label='Nombre del torneo')
    logo = forms.ImageField(
        required=False, label='Logo del torneo',
        help_text='Opcional. Si lo dejas vacío se muestran las iniciales.')
    portada = forms.ImageField(
        required=False, label='Portada del torneo',
        help_text='Opcional. Se muestra de fondo en las pantallas del torneo.')
    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), required=False, label='Descripción')
    modalidad = forms.ChoiceField(
        choices=Torneo.MODALIDAD_CHOICES, label='Cómo se juega',
        widget=forms.RadioSelect)
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        label='Día del torneo',
        help_text='En eliminación directa el torneo se juega entero en esta fecha.')
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        label='Termina el',
        help_text='Último día del torneo. Cada partido lleva su propia fecha y cancha.')
    empate_define_penales = forms.BooleanField(
        required=False, initial=True,
        label='El empate se define en penales',
        help_text='En la fase de grupos suma un punto extra al que gane la tanda. '
                  'Si lo desmarcas, el empate vale un punto para cada uno.')

    def __init__(self, *args, instancia=None, **kwargs):
        self.instancia = instancia
        if instancia is not None and not kwargs.get('data'):
            primera = instancia.categoria
            kwargs.setdefault('initial', {
                'nombre': instancia.liga.nombre,
                'descripcion': instancia.liga.descripcion,
                'modalidad': instancia.modalidad,
                'fecha': instancia.fecha_inicio,
                'fecha_fin': instancia.fecha_fin,
                'logo': instancia.liga.logo or None,
                'portada': instancia.liga.portada or None,
                'empate_define_penales': (primera.empate_define_penales
                                          if primera else True),
            })
        super().__init__(*args, **kwargs)

        self.fields['modalidad'].widget.attrs['data-modalidad'] = '1'
        for nombre in ('fecha_fin', 'empate_define_penales'):
            self.fields[nombre].widget.attrs['data-solo-grupos'] = CLAVES_POR_GRUPOS
        self.fields['fecha'].widget.attrs['data-fecha-inicio'] = '1'

        if instancia is not None and instancia.sorteado:
            for nombre in ('modalidad', 'empate_define_penales'):
                self.fields[nombre].disabled = True
                self.fields[nombre].help_text = (
                    'No se puede cambiar: el torneo ya tiene partidos.')

    def clean_modalidad(self):
        clave = self.cleaned_data['modalidad']
        equipos, formato = Torneo.desde_modalidad(clave)

        if self.instancia is None:
            return clave

        inscritos = self.instancia.inscritos
        if inscritos and formato != self.instancia.formato:
            raise forms.ValidationError(
                f'Ya hay {inscritos} equipo(s) inscrito(s): para cambiar el formato '
                f'tienes que darlos de baja primero.')
        if equipos is not None and inscritos > equipos:
            raise forms.ValidationError(
                f'Ya hay {inscritos} equipos inscritos: no puedes bajar el torneo '
                f'a {equipos}.')
        return clave

    def clean(self):
        datos = super().clean()
        clave = datos.get('modalidad')
        if not clave:
            return datos

        _, formato = Torneo.desde_modalidad(clave)
        inicio, fin = datos.get('fecha'), datos.get('fecha_fin')

        if formato != Torneo.FORMATO_GRUPOS:
            datos['fecha_fin'] = inicio
            return datos

        if fin is None:
            datos['fecha_fin'] = inicio
        elif inicio and fin < inicio:
            self.add_error(
                'fecha_fin',
                'El torneo no puede terminar antes de empezar.')
        return datos

    @transaction.atomic
    def guardar(self, usuario):
        datos = self.cleaned_data
        equipos, formato = Torneo.desde_modalidad(datos['modalidad'])
        con_grupos = formato == Torneo.FORMATO_GRUPOS
        penales = bool(datos['empate_define_penales']) if con_grupos else True
        inicio, fin = datos['fecha'], datos['fecha_fin']

        if self.instancia is None:
            liga = Liga.objects.create(
                nombre=datos['nombre'], descripcion=datos['descripcion'],
                logo=datos['logo'] or None, portada=datos['portada'] or None,
                fecha_inicio=inicio, fecha_final=fin)
            if usuario.role == Usuario.ROLE_ADMIN_LIGA:
                liga.administradores.add(usuario)
            if not con_grupos:
                Categoria.objects.create(
                    liga=liga, nombre=CATEGORIA_UNICA, cupo_equipos=equipos,
                    libre=True, vueltas=Categoria.VUELTA_UNICA,
                    empate_define_penales=penales, mini_liguilla=False)
            return Torneo.objects.create(
                liga=liga, fecha=inicio,
                equipos=equipos if equipos is not None else Torneo.EQUIPOS_OCHO,
                formato=formato, creado_por=usuario)

        torneo = self.instancia
        liga = torneo.liga
        liga.nombre = datos['nombre']
        liga.descripcion = datos['descripcion']
        aplicar_imagen(liga, 'logo', datos['logo'])
        aplicar_imagen(liga, 'portada', datos['portada'])
        liga.fecha_inicio, liga.fecha_final = inicio, fin
        liga.save()

        torneo.fecha = inicio
        if equipos is not None:
            torneo.equipos = equipos
        torneo.formato = formato
        torneo.save()

        if con_grupos:
            torneo.categorias.update(empate_define_penales=penales)
        else:
            categoria = torneo.categoria
            if categoria is not None:
                categoria.cupo_equipos = equipos
                categoria.empate_define_penales = penales
                categoria.save(update_fields=['cupo_equipos', 'empate_define_penales'])
        return torneo


class TorneoCategoriaForm(StyledFormMixin, forms.Form):
    CAMPOS_OBLIGATORIOS = ('nombre', 'grupos')
    CAMPOS_CAPITALIZAR = ('nombre',)

    CUPO_ABIERTO = 999

    nombre = forms.CharField(
        max_length=120, label='Nombre de la categoría',
        help_text='Como le llamas a esta división: Infantil Prima, Juvenil Mayor…')
    grupos = forms.TypedChoiceField(
        coerce=int, label='¿En cuántos grupos se reparten?',
        help_text='Cada grupo juega su propio todos contra todos y lleva su tabla.')
    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}), required=False, label='Notas')

    def __init__(self, torneo, *args, instancia=None, **kwargs):
        self.torneo = torneo
        self.instancia = instancia
        if instancia is not None and not kwargs.get('data'):
            kwargs.setdefault('initial', {
                'nombre': instancia.nombre,
                'grupos': instancia.grupos,
                'descripcion': instancia.descripcion,
            })
        super().__init__(*args, **kwargs)

        self.fields['grupos'].choices = [
            (cuantos, f'{cuantos} grupo(s) · {", ".join(Equipo.LETRAS_GRUPO[:cuantos])}')
            for cuantos in range(1, 9)
        ]

        if instancia is not None and instancia.partidos.exists():
            campo = self.fields['grupos']
            campo.disabled = True
            campo.help_text = ('No se puede cambiar: esta categoría ya tiene '
                               'partidos generados.')

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        hermanas = self.torneo.categorias.filter(nombre__iexact=nombre)
        if self.instancia is not None:
            hermanas = hermanas.exclude(pk=self.instancia.pk)
        if hermanas.exists():
            raise forms.ValidationError(
                f'Este torneo ya tiene una categoría llamada "{nombre}".')
        return nombre

    def clean_grupos(self):
        cuantos = self.cleaned_data['grupos']
        if self.instancia is None:
            return cuantos

        letras = set(Equipo.LETRAS_GRUPO[:cuantos])
        huerfanos = (self.instancia.equipos
                     .exclude(grupo__in=letras)
                     .exclude(grupo='')
                     .count())
        if huerfanos:
            raise forms.ValidationError(
                f'{huerfanos} equipo(s) quedarían en un grupo que dejaría de '
                f'existir. Muévelos antes de bajar la cantidad de grupos.')
        return cuantos

    def guardar(self):
        datos = self.cleaned_data
        primera = self.torneo.categorias.first()
        penales = primera.empate_define_penales if primera else True

        if self.instancia is not None:
            categoria = self.instancia
            categoria.nombre = datos['nombre']
            categoria.grupos = datos['grupos']
            categoria.descripcion = datos['descripcion']
            categoria.save(update_fields=['nombre', 'grupos', 'descripcion'])
            return categoria

        return Categoria.objects.create(
            liga=self.torneo.liga,
            nombre=datos['nombre'],
            descripcion=datos['descripcion'],
            grupos=datos['grupos'],
            cupo_equipos=self.CUPO_ABIERTO,
            libre=True,
            vueltas=Categoria.VUELTA_UNICA,
            empate_define_penales=penales,
            mini_liguilla=False,
        )


class TorneoEquipoForm(StyledFormMixin, forms.Form):
    CAMPOS_OBLIGATORIOS = ('nombre', 'entrenador')
    CAMPOS_CAPITALIZAR = ('nombre',)

    nombre = forms.CharField(max_length=140, label='Nombre del equipo')
    escudo = forms.ImageField(required=False, label='Escudo del equipo')
    entrenador = forms.ModelChoiceField(
        queryset=Usuario.objects.none(), label='Entrenador',
        help_text='Quién va a manejar este equipo en el torneo.')
    grupo = forms.ChoiceField(
        choices=Equipo.GRUPO_CHOICES, label='Grupo', widget=forms.RadioSelect,
        required=False)

    def __init__(self, torneo, categoria, usuario, *args, instancia=None, **kwargs):
        self.torneo = torneo
        self.categoria = categoria
        self.instancia = instancia
        if instancia is not None:
            kwargs.setdefault('initial', {
                'nombre': instancia.nombre,
                'entrenador': instancia.entrenador_id,
                'grupo': instancia.grupo,
                'escudo': instancia.escudo or None,
            })
        super().__init__(*args, **kwargs)
        self.fields['entrenador'].queryset = Usuario.objects.entrenadores(usuario).order_by(
            'first_name', 'last_name', 'username')

        if not categoria.juega_por_grupos:
            del self.fields['grupo']
            return

        reparto = categoria.reparto
        campo = self.fields['grupo']
        campo.required = True
        campo.label = 'Grupo *'
        campo.choices = [
            (letra, f'Grupo {letra} · {reparto[letra]} equipo(s)')
            for letra in categoria.letras_de_grupo
        ]
        campo.help_text = 'Cada grupo juega su propio todos contra todos.'

        if instancia is not None and categoria.partidos.exists():
            campo.disabled = True
            campo.initial = instancia.grupo
            campo.help_text = ('El calendario ya está generado: moverlo de grupo '
                               'dejaría sus partidos sin rival.')

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        hermanos = self.categoria.equipos.filter(nombre__iexact=nombre)
        if self.instancia is not None:
            hermanos = hermanos.exclude(pk=self.instancia.pk)
        if hermanos.exists():
            raise forms.ValidationError(
                f'"{nombre}" ya está inscrito en {self.categoria.nombre}.')
        return nombre

    def clean(self):
        """Los cupos cierran el alta, nunca la edicion.

        Un equipo ya inscrito se sigue corrigiendo con el calendario generado:
        el nombre, el escudo y el entrenador no mueven un solo cruce, porque el
        partido apunta al equipo por su id. Lo unico que si lo moveria es el
        grupo, y ese viaja `disabled` desde __init__.

        Cuando estos dos cortes valian tambien al editar, cambiarle el nombre a
        un equipo era imposible desde el torneo, y el admin terminaba en
        `/equipos/<pk>/editar/`, que es la pantalla que no comprueba nombres
        repetidos.
        """
        datos = super().clean()
        if self.instancia is not None:
            return datos

        if self.categoria.partidos.exists():
            raise forms.ValidationError(
                f'{self.categoria.nombre} ya tiene partidos generados: no se '
                f'pueden inscribir más equipos.')
        if not self.torneo.es_por_grupos and self.torneo.completo:
            raise forms.ValidationError(
                f'El torneo ya tiene sus {self.torneo.equipos} equipos.')
        return datos

    def guardar(self):
        datos = self.cleaned_data
        grupo = datos.get('grupo', '')

        if self.instancia is not None:
            equipo = self.instancia
            equipo.nombre = datos['nombre']
            equipo.entrenador = datos['entrenador']
            equipo.grupo = grupo
            aplicar_imagen(equipo, 'escudo', datos['escudo'])
            equipo.save()
            return equipo

        return Equipo.objects.create(
            nombre=datos['nombre'],
            escudo=datos['escudo'] or None,
            liga=self.torneo.liga,
            categoria=self.categoria,
            grupo=grupo,
            entrenador=datos['entrenador'])


class SiembraForm(forms.Form):
    """Los cruces de la primera ronda de liguilla, elegidos a mano."""

    def __init__(self, categoria, *args, **kwargs):
        self.categoria = categoria
        super().__init__(*args, **kwargs)

        opciones = [('', '— elegir equipo —')] + [
            (equipo.pk, f'{equipo.nombre}' + (f'  ({equipo.grupo})' if equipo.grupo else ''))
            for equipo in categoria.equipos.order_by('grupo', 'nombre')
        ]
        posibles = grupos.rondas_posibles(categoria)
        etiquetas = dict(Partido.FASE_CHOICES)

        self.fields['ronda'] = forms.ChoiceField(
            choices=[(fase, f'{etiquetas[fase]} · {llaves} llave(s)')
                     for fase, llaves in posibles],
            label='¿Desde qué ronda arranca?',
            widget=forms.RadioSelect)

        self.maximo = max((llaves for _, llaves in posibles), default=0)
        for numero in range(self.maximo):
            for lado in ('local', 'visitante'):
                self.fields[f'{lado}_{numero}'] = forms.ChoiceField(
                    choices=opciones, required=False,
                    label=f'Llave {numero + 1} · {lado}')

        for campo in self.fields.values():
            clase = ('h-4 w-4 rounded-full border-gray-300 text-green-700 focus:ring-green-500'
                     if isinstance(campo.widget, forms.RadioSelect)
                     else 'campo-siembra')
            campo.widget.attrs['class'] = clase

    def llaves(self):
        """Los pares de campos que dibuja la pantalla, listos para recorrer."""
        return [{'numero': numero,
                 'local': self[f'local_{numero}'],
                 'visitante': self[f'visitante_{numero}']}
                for numero in range(self.maximo)]

    def clean(self):
        datos = super().clean()
        fase = datos.get('ronda')
        if not fase:
            return datos

        llaves = grupos.LLAVES_POR_RONDA[fase]
        elegidos, vistos = [], set()

        for numero in range(llaves):
            local = datos.get(f'local_{numero}')
            visitante = datos.get(f'visitante_{numero}')
            if not local or not visitante:
                raise forms.ValidationError(
                    f'Falta completar la llave {numero + 1}: elige los dos equipos.')
            if local == visitante:
                raise forms.ValidationError(
                    f'En la llave {numero + 1} elegiste el mismo equipo dos veces.')
            for pk in (local, visitante):
                if pk in vistos:
                    raise forms.ValidationError(
                        'Un equipo no puede jugar dos llaves de la misma ronda.')
                vistos.add(pk)
            elegidos.append((local, visitante))

        por_pk = {str(e.pk): e for e in self.categoria.equipos.all()}
        self.cruces = [(por_pk[local], por_pk[visitante])
                       for local, visitante in elegidos]
        self.fase = fase
        return datos


def _con_estado(torneos):
    for torneo in torneos:
        torneo.motivo_sorteo = ('' if torneo.es_por_grupos
                                else relampago.motivo_para_no_sortear(torneo))
    return torneos


_TEXTOS_PUBLICOS = {
    'titulo_pagina': 'Torneos relámpago',
    'seccion': 'Torneos',
    'encabezado': 'Torneos relámpago',
    'descripcion': 'Un solo día, eliminación directa. El empate se define en penales.',
    'vacio': 'Todavía no hay torneos relámpago.',
    'enlace_publico': False,
}

_TEXTOS_MIS_TORNEOS = {
    'titulo_pagina': 'Mis torneos',
    'seccion': 'Tablero · Torneos',
    'encabezado': 'Mis torneos relámpago',
    'descripcion': 'Los torneos que administras. Aquí los armas, los sorteas y cargas sus resultados.',
    'vacio': 'Todavía no tienes torneos. Crea el primero con el botón de arriba.',
    'enlace_publico': True,
}


def torneo_list(request):
    """El listado público: todos los torneos visibles.

    A propósito muestra los de todos, también al admin de liga: esta es la
    vitrina. La versión acotada a lo propio es `mis_torneos`, que es a donde
    lleva el tablero. Son dos entradas y no un `if` por rol adentro de esta,
    igual que en equipos y partidos.
    """
    return _listado(request, solo_propios=False)


@admin_liga_required
def mis_torneos(request):
    """El mismo listado, acotado a los torneos que uno administra."""
    return _listado(request, solo_propios=True)


def _listado(request, solo_propios):
    usuario = request.user
    es_admin = usuario.is_authenticated and (
        usuario.es_super_admin() or usuario.es_admin_liga())

    ambito = (torneos_administrados(usuario) if solo_propios
              else torneos_visibles(usuario))
    torneos = ambito.select_related('liga')
    administrados = set(
        torneos_administrados(usuario).values_list('pk', flat=True))
    for torneo in torneos:
        torneo.puede_administrar = torneo.pk in administrados

    motivo = motivo_para_no_crear(usuario) if es_admin else ''
    return render(request, 'torneos/torneo_list.html', {
        'torneos': _con_estado(list(torneos)),
        'puede_crear': es_admin and not motivo,
        'motivo_no_crear': motivo,
        'cuota': _cuota(usuario) if es_admin else None,
        'es_superadmin': usuario.is_authenticated and usuario.es_super_admin(),
        **(_TEXTOS_MIS_TORNEOS if solo_propios else _TEXTOS_PUBLICOS),
    })


def _cuota(usuario):
    """Cuantos torneos en curso tiene y cuantos puede tener."""
    if usuario.es_super_admin():
        return None
    return {
        'en_curso': torneos_administrados(usuario).en_curso().count(),
        'limite': usuario.limite_torneos,
    }


def _puede_administrar(usuario, torneo):
    return torneos_administrados(usuario).filter(pk=torneo.pk).exists()


def _categoria_del_torneo(usuario, torneo_pk, categoria_pk):
    torneo = get_object_or_404(
        torneos_administrados(usuario).select_related('liga'), pk=torneo_pk)
    categoria = get_object_or_404(torneo.categorias, pk=categoria_pk)
    return torneo, categoria


def _tarjetas_de_categoria(torneo):
    """Lo que el listado del torneo muestra de cada categoria, sin abrirla."""
    tarjetas = []
    for categoria in torneo.categorias.prefetch_related('equipos'):
        reparto = categoria.reparto
        tarjetas.append({
            'categoria': categoria,
            'reparto': [{'letra': letra, 'equipos': reparto[letra]}
                        for letra in categoria.letras_de_grupo],
            'inscritos': sum(reparto.values()) + categoria.equipos_sin_grupo,
            'sin_grupo': categoria.equipos_sin_grupo,
            'generados': categoria.partidos.filter(
                fase=Partido.FASE_REGULAR).exists(),
            'cerrados': grupos.cerrados(categoria),
            'pendientes': grupos.pendientes(categoria),
            'ronda': grupos.ronda_ya_armada(categoria),
            'campeon': grupos.campeon(categoria),
        })
    return tarjetas


def torneo_detalle(request, torneo):
    """La portada del torneo: su cuadro, o sus categorías si va por grupos."""
    torneo = get_object_or_404(
        torneos_visibles(request.user).select_related('liga'), liga__slug=torneo)
    puede_administrar = _puede_administrar(request.user, torneo)

    contexto = {
        'torneo': torneo,
        'puede_administrar': puede_administrar,
        'es_superadmin': request.user.is_authenticated and request.user.es_super_admin(),

    }

    if torneo.es_por_grupos:
        contexto['tarjetas'] = _tarjetas_de_categoria(torneo)
        return render(request, 'torneos/torneo_categorias.html', contexto)

    categoria = torneo.categoria
    equipos = (list(categoria.equipos.select_related('entrenador').order_by('nombre'))
               if categoria else [])
    partidos = (list(Partido.objects
                     .filter(categoria=categoria)
                     .select_related('equipo_local', 'equipo_visitante', 'sede',
                                     'ganador_penales')
                     .order_by('fecha', 'orden'))
                if categoria else [])

    contexto.update({
        'equipos': equipos,
        'partidos': partidos,
        'cuadro': relampago.cuadro(categoria) if categoria else None,
        'motivo_sorteo': relampago.motivo_para_no_sortear(torneo),
    })
    return render(request, 'torneos/torneo_detalle.html', contexto)


def torneo_categoria(request, torneo, categoria):
    """Una categoría del torneo: sus grupos, sus tablas, sus partidos y su cuadro."""
    torneo = get_object_or_404(
        torneos_visibles(request.user).select_related('liga'), liga__slug=torneo)
    categoria = get_object_or_404(torneo.categorias, slug=categoria)

    estado = grupos.resumen(categoria)
    equipos = list(categoria.equipos
                   .select_related('entrenador')
                   .annotate(cuantos_jugadores=Count('jugadores'))
                   .order_by('grupo', 'nombre'))

    estado.update({
        'torneo': torneo,
        'equipos': equipos,
        'plantillas': [
            {'letra': letra,
             'etiqueta': f'Grupo {letra}',
             'equipos': [e for e in equipos if e.grupo == letra]}
            for letra in categoria.letras_de_grupo
        ],
        'eliminacion': list(categoria.partidos
                            .exclude(fase=Partido.FASE_REGULAR)
                            .select_related('equipo_local', 'equipo_visitante',
                                            'sede', 'ganador_penales')
                            .order_by('fecha', 'orden')),
        'pasos': _pasos_de_categoria(categoria, estado),
        'puede_administrar': _puede_administrar(request.user, torneo),
        'es_superadmin': request.user.is_authenticated and request.user.es_super_admin(),
    })
    estado['jornadas'] = [_jornada_con_resumen(j) for j in estado['jornadas']]
    return render(request, 'torneos/torneo_categoria.html', estado)


def _jornada_con_resumen(jornada):
    """Le agrega a la jornada el día, las canchas y cuánto lleva jugado."""
    partidos = jornada['partidos']
    fechas = sorted(p.fecha for p in partidos if p.fecha)
    canchas = sorted({p.sede.nombre for p in partidos if p.sede})
    jugados = sum(1 for p in partidos if p.jugado)

    return {
        **jornada,
        'desde': fechas[0] if fechas else None,
        'hasta': fechas[-1] if fechas else None,
        'un_solo_dia': bool(fechas) and fechas[0].date() == fechas[-1].date(),
        'canchas': canchas,
        'jugados': jugados,
        'total': len(partidos),
        'completa': jugados == len(partidos) and bool(partidos),
    }


def _pasos_de_categoria(categoria, estado):
    """Los cuatro pasos de una categoría y en cuál va, para la guía de arriba."""
    hay_equipos = categoria.equipos.exists()
    hay_partidos = bool(estado['jornadas'])
    cerrados = estado['cerrados']
    hay_liguilla = estado['ronda_armada'] is not None
    hay_campeon = estado['campeon'] is not None

    crudos = [
        ('Inscribir equipos', hay_partidos or hay_equipos and cerrados, hay_equipos),
        ('Generar partidos', hay_partidos, hay_partidos),
        ('Jugar los grupos', cerrados, hay_partidos),
        ('Armar la liguilla', hay_campeon, hay_liguilla),
    ]

    pasos, actual_marcado = [], False
    for numero, (titulo, listo, empezado) in enumerate(crudos, start=1):
        if listo:
            situacion = 'listo'
        elif not actual_marcado:
            situacion = 'actual'
            actual_marcado = True
        else:
            situacion = 'pendiente'
        pasos.append({'numero': numero, 'titulo': titulo,
                      'situacion': situacion, 'empezado': empezado})
    return pasos


@admin_liga_required
def torneo_categoria_create(request, pk):
    torneo = get_object_or_404(torneos_administrados(request.user), pk=pk)
    return _formulario_de_categoria(request, torneo, instancia=None)


@admin_liga_required
def torneo_categoria_edit(request, pk, categoria_pk):
    torneo, categoria = _categoria_del_torneo(request.user, pk, categoria_pk)
    return _formulario_de_categoria(request, torneo, instancia=categoria)


def _formulario_de_categoria(request, torneo, instancia):
    modal = request.GET.get('modal') == '1'
    nueva = instancia is None

    if request.method == 'POST':
        form = TorneoCategoriaForm(torneo, request.POST, instancia=instancia)
        if form.is_valid():
            categoria = form.guardar()
            messages.success(
                request,
                f'Categoría "{categoria.nombre}" '
                f'{"creada" if nueva else "actualizada"} con '
                f'{categoria.grupos} grupo(s).')
            if modal:
                return JsonResponse({'success': True})
            return redirect(categoria)
    else:
        form = TorneoCategoriaForm(torneo, instancia=instancia)

    titulo = ('Nueva categoría' if nueva else f'Editar {instancia.nombre}')
    contexto = {'form': form, 'title': titulo, 'torneo': torneo}
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'torneos/torneo_form.html', contexto)


@superadmin_required
def torneo_categoria_delete(request, pk, categoria_pk):
    torneo, categoria = _categoria_del_torneo(request.user, pk, categoria_pk)

    equipos = categoria.equipos.all()
    entrenadores = entrenadores_sin_equipo_tras_borrar(equipos)
    premios = Palmares.objects.filter(categoria=categoria)

    arrastra = []
    for cantidad, etiqueta in (
        (equipos.count(), 'equipo(s)'),
        (Jugador.objects.filter(equipo__categoria=categoria).count(), 'jugador(es)'),
        (categoria.partidos.count(), 'partido(s)'),
        (entrenadores.count(), 'cuenta(s) de entrenador'),
        (premios.count(), 'registro(s) del palmarés'),
    ):
        if cantidad:
            arrastra.append(f'{cantidad} {etiqueta}')

    def limpiar():
        premios.delete()
        categoria.partidos.all().delete()
        equipos.delete()
        entrenadores.delete()

    return vista_eliminar(
        request,
        instancia=categoria,
        etiqueta=f'Categoría: {categoria.nombre}',
        url_listado='torneo-detalle',
        url_listado_args=[torneo.pk],
        mensaje_ok=f'Se eliminó la categoría "{categoria.nombre}" con todo su contenido.',
        arrastra=arrastra,
        antes_de_borrar=limpiar,
    )


@admin_liga_required
def torneo_categoria_generar(request, pk, categoria_pk):
    """Genera el todos contra todos de cada grupo de la categoría."""
    torneo, categoria = _categoria_del_torneo(request.user, pk, categoria_pk)
    if request.method == 'POST':
        motivo = grupos.motivo_para_no_generar(categoria)
        if motivo:
            messages.error(request, motivo)
        else:
            creados = grupos.generar(categoria)
            cuantas = len({partido.jornada for partido in creados})
            messages.success(
                request,
                f'{categoria.nombre}: se generaron {len(creados)} partido(s) en '
                f'{cuantas} jornada(s). Ponles fecha, hora y cancha desde la lista.')
    return redirect(categoria)


@admin_liga_required
def torneo_categoria_sembrar(request, pk, categoria_pk):
    """Arma a mano la primera ronda de la liguilla de una categoría."""
    torneo, categoria = _categoria_del_torneo(request.user, pk, categoria_pk)
    modal = request.GET.get('modal') == '1'

    motivo = grupos.motivo_para_no_sembrar(categoria)
    if motivo:
        messages.error(request, motivo)
        if modal:
            return JsonResponse({'success': False, 'recargar': True})
        return redirect(categoria)

    if request.method == 'POST':
        form = SiembraForm(categoria, request.POST)
        if form.is_valid():
            creados = grupos.sembrar(categoria, form.fase, form.cruces)
            etiqueta = creados[0].get_fase_display().lower() if creados else 'la ronda'
            messages.success(
                request,
                f'{categoria.nombre}: quedaron armadas {len(creados)} llave(s) de '
                f'{etiqueta}. De aquí en adelante los ganadores avanzan solos.')
            if modal:
                return JsonResponse({'success': True})
            return redirect(categoria)
    else:
        form = SiembraForm(categoria)

    contexto = {
        'form': form,
        'title': f'Armar la liguilla · {categoria.nombre}',
        'torneo': torneo,
        'categoria': categoria,
        'grupos': grupos.posiciones(categoria),
        'llaves_por_ronda': grupos.LLAVES_POR_RONDA,
    }
    if modal:
        return render(request, 'torneos/_siembra_modal.html', contexto)
    return render(request, 'torneos/torneo_siembra.html', contexto)


def motivo_para_no_crear(usuario):
    """Por que este usuario no puede crear un torneo mas, o '' si puede.

    Los torneos terminados no ocupan lugar: el evento se jugo y el admin tiene
    que poder armar el siguiente sin esperar a que se borre el viejo. Es el
    mismo criterio que `limite_ligas`.
    """
    if usuario.es_super_admin():
        return ''
    en_curso = torneos_administrados(usuario).en_curso().count()
    if en_curso < usuario.limite_torneos:
        return ''
    return (
        f'Alcanzaste el límite de {usuario.limite_torneos} torneo(s) en curso que '
        f'puedes tener. Termina alguno o contacta al Administrador General.'
    )


@admin_liga_required
def torneo_create(request):
    modal = request.GET.get('modal') == '1'

    motivo = motivo_para_no_crear(request.user)
    if motivo:
        messages.error(request, motivo)
        if modal:
            return JsonResponse({'success': False, 'recargar': True})
        return redirect('mis-torneos')

    if request.method == 'POST':
        form = TorneoForm(request.POST, request.FILES)
        if form.is_valid():
            torneo = form.guardar(request.user)
            siguiente = ('Ahora crea sus categorías.' if torneo.es_por_grupos
                         else f'Ahora inscribe sus {torneo.equipos} equipos.')
            messages.success(
                request,
                f'Torneo "{torneo.nombre}" creado ({torneo.fechas_texto}). {siguiente}')
            if modal:
                return JsonResponse({'success': True})
            return redirect(torneo)
    else:
        form = TorneoForm()

    contexto = {'form': form, 'title': 'Crear torneo'}
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'torneos/torneo_form.html', contexto)


@admin_liga_required
def torneo_edit(request, pk):
    torneo = get_object_or_404(torneos_administrados(request.user), pk=pk)
    modal = request.GET.get('modal') == '1'
    if request.method == 'POST':
        form = TorneoForm(request.POST, request.FILES, instancia=torneo)
        if form.is_valid():
            form.guardar(request.user)
            messages.success(request, 'Torneo actualizado.')
            if modal:
                return JsonResponse({'success': True})
            return redirect(torneo)
    else:
        form = TorneoForm(instancia=torneo)

    contexto = {'form': form, 'title': f'Editar torneo: {torneo.nombre}'}
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'torneos/torneo_form.html', contexto)


@admin_liga_required
def torneo_equipo_create(request, pk, categoria_pk=None):
    torneo = get_object_or_404(torneos_administrados(request.user), pk=pk)
    categoria = (get_object_or_404(torneo.categorias, pk=categoria_pk)
                 if categoria_pk else torneo.categoria)
    if categoria is None:
        messages.error(request, 'Este torneo todavía no tiene categorías.')
        return redirect(torneo)

    return _formulario_de_equipo(request, torneo, categoria, instancia=None)


@admin_liga_required
def torneo_equipo_edit(request, pk, categoria_pk, equipo_pk):
    torneo, categoria = _categoria_del_torneo(request.user, pk, categoria_pk)
    equipo = get_object_or_404(categoria.equipos, pk=equipo_pk)
    return _formulario_de_equipo(request, torneo, categoria, instancia=equipo)


def _formulario_de_equipo(request, torneo, categoria, instancia):
    modal = request.GET.get('modal') == '1'
    nuevo = instancia is None

    if request.method == 'POST':
        form = TorneoEquipoForm(torneo, categoria, request.user,
                                request.POST, request.FILES, instancia=instancia)
        if form.is_valid():
            equipo = form.guardar()
            destino = f' en el grupo {equipo.grupo}' if equipo.grupo else ''
            messages.success(
                request,
                f'"{equipo.nombre}" {"inscrito" if nuevo else "actualizado"}{destino}.')
            if modal:
                return JsonResponse({'success': True})
            return _volver_a(torneo, categoria)
    else:
        extra = {}
        sugerido = request.GET.get('grupo', '')
        if nuevo and sugerido in categoria.letras_de_grupo:
            extra['initial'] = {'grupo': sugerido}
        form = TorneoEquipoForm(torneo, categoria, request.user,
                                instancia=instancia, **extra)

    titulo = (f'Inscribir equipo en {categoria.nombre}' if nuevo
              else f'Editar {instancia.nombre}')
    contexto = {'form': form, 'title': titulo, 'torneo': torneo}
    if modal:
        return render(request, 'usuarios/modal_form.html', contexto)
    return render(request, 'torneos/torneo_form.html', contexto)


def _volver_a(torneo, categoria):
    if torneo.es_por_grupos:
        return redirect(categoria)
    return redirect(torneo)


@admin_liga_required
def torneo_sortear(request, pk):
    """Arma el cuadro al azar con los equipos inscritos. Solo eliminación directa."""
    torneo = get_object_or_404(torneos_administrados(request.user), pk=pk)
    if request.method == 'POST':
        motivo = relampago.motivo_para_no_sortear(torneo)
        if motivo:
            messages.error(request, motivo)
        else:
            creados = relampago.sortear(torneo)
            ronda = creados[0].get_fase_display().lower()
            messages.success(
                request,
                f'Cuadro sorteado: {len(creados)} partido(s) de {ronda}, desde las '
                f'{creados[0].fecha:%H:%M}. El empate se define en penales.')
    return redirect(torneo)


@superadmin_required
def torneo_delete(request, pk):
    """Elimina el torneo con todo lo suyo. Solo el Administrador General.

    Se lleva equipos, jugadores, partidos, las cuentas de sus entrenadores y su
    registro del palmarés: un torneo borrado no deja rastro en la vitrina.
    """
    torneo = get_object_or_404(Torneo, pk=pk)

    if torneo.terminado and not torneo.lista_para_eliminar:
        messages.error(
            request,
            f'"{torneo.nombre}" terminó hace poco y sigue en exhibición. '
            f'Podrás eliminarlo en {torneo.dias_en_vitrina} día(s).')
        return redirect('mis-torneos')

    equipos = Equipo.objects.filter(liga=torneo.liga)
    entrenadores = entrenadores_sin_equipo_tras_borrar(equipos)
    premios = Palmares.objects.filter(categoria__liga=torneo.liga)

    arrastra = []
    for cantidad, etiqueta in (
        (torneo.categorias.count(), 'categoría(s)'),
        (equipos.count(), 'equipo(s)'),
        (Jugador.objects.filter(equipo__liga=torneo.liga).count(), 'jugador(es)'),
        (Partido.objects.filter(categoria__liga=torneo.liga).count(), 'partido(s)'),
        (entrenadores.count(), 'cuenta(s) de entrenador'),
        (premios.count(), 'registro(s) del palmarés'),
    ):
        if cantidad:
            arrastra.append(f'{cantidad} {etiqueta}')

    def limpiar():
        premios.delete()
        Partido.objects.filter(categoria__liga=torneo.liga).delete()
        equipos.delete()
        entrenadores.delete()

    return vista_eliminar(
        request,
        instancia=torneo.liga,
        etiqueta=f'Torneo: {torneo.nombre}',
        url_listado='mis-torneos',
        mensaje_ok=f'Se eliminó el torneo "{torneo.nombre}" con todo su contenido, '
                   f'incluido su palmarés.',
        arrastra=arrastra,
        antes_de_borrar=limpiar,
    )
