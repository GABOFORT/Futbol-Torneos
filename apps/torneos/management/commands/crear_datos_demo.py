"""Rehace las cinco ligas de demostracion con datos coherentes.

    python manage.py crear_datos_demo            # borra y reconstruye
    python manage.py crear_datos_demo --borrar   # solo borra
    python manage.py crear_datos_demo --resumen  # que quedaria, sin tocar nada

NO toca la Liga Premier Villahermosa, que es la liga real en produccion. La
lista de ligas afectadas sale de _datos_demo.LIGAS y de ningun otro lado.

Todo corre dentro de una transaccion: si algo falla a mitad de camino, la base
queda como estaba.

**Por que se simula usando el codigo del sistema y no escribiendo filas a mano:**
el calendario lo arma `calendario.armar_jornadas`, la liguilla la arma y la
avanza `liguilla.iniciar` / `liguilla.avanzar`, y el palmares lo graba
`palmares.cerrar_si_termino`. Datos escritos a mano se verian bien y estarian
mal: un cuadro de liguilla que no respeta la siembra, un campeon que no salio de
la final. Ademas, si alguna de esas reglas se rompe, este comando falla, que es
justo lo que uno quiere que pase.
"""
import datetime
import random
import unicodedata

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.equipos.models import Equipo
from apps.jugadores.models import Jugador
from apps.partidos import liguilla as liguilla_mod
from apps.partidos.calendario import armar_jornadas
from apps.partidos.models import Actuacion, Partido
from apps.torneos import palmares as palmares_mod
from apps.torneos.models import Categoria, Liga, Palmares, Sede
from apps.usuarios.models import Usuario

from ._datos_demo import (
    FORMACIONES, JUGADORES_MAXIMO, JUGADORES_MINIMO, LIGAS, NOMBRES,
    posiciones_para,
)

# Semilla fija: dos corridas dan exactamente los mismos datos. Sirve para poder
# hablar de "el 3-0 de Arsenal" sabiendo que sigue ahi despues de rehacer.
SEMILLA = 20260806

# Marca de las cuentas que crea este comando. Es lo unico que mira `--borrar`
# para saber que usuario puede eliminar: nunca toca una cuenta que no creo el.
PREFIJO_DT = 'dt-demo-'


def sin_acentos(texto):
    normalizado = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in normalizado if not unicodedata.combining(c))


def slug(texto):
    return sin_acentos(texto).lower().replace(' ', '-').replace("'", '')


class Command(BaseCommand):
    help = 'Rehace las ligas de demostracion con clubes, canchas y planteles reales.'

    def add_arguments(self, parser):
        parser.add_argument('--borrar', action='store_true',
                            help='Solo borra los datos de demostracion, sin reconstruir.')
        parser.add_argument('--resumen', action='store_true',
                            help='Muestra que se va a borrar y que se va a crear, sin tocar la base.')

    def handle(self, *args, **opciones):
        self.rng = random.Random(SEMILLA)
        self.hoy = timezone.localdate()
        self.sede_de_equipo = {}
        self._cache_planteles = {}

        nombres_ligas = [cfg['nombre'] for cfg in LIGAS]
        ligas = {liga.nombre: liga for liga in Liga.objects.filter(nombre__in=nombres_ligas)}

        faltan = set(nombres_ligas) - set(ligas)
        if faltan:
            self.stderr.write(f'No existen estas ligas: {", ".join(sorted(faltan))}')
            return

        if opciones['resumen']:
            self._resumen(ligas)
            return

        with transaction.atomic():
            self._borrar(ligas)
            if opciones['borrar']:
                self.stdout.write(self.style.SUCCESS('Datos de demostracion eliminados.'))
                return
            self._construir(ligas)

        self._huerfanos()

    # ------------------------------------------------------------------ resumen

    def _resumen(self, ligas):
        self.stdout.write('SE BORRARIA:')
        for liga in ligas.values():
            cats = liga.categorias.count()
            eqs = Equipo.objects.filter(liga=liga).count()
            jug = Jugador.objects.filter(equipo__liga=liga).count()
            par = Partido.objects.filter(categoria__liga=liga).count()
            pal = Palmares.objects.filter(liga_nombre=liga.nombre).count()
            self.stdout.write(
                f'  {liga.nombre:18} cat={cats} equipos={eqs} jugadores={jug} '
                f'partidos={par} sedes={liga.sedes.count()} palmares={pal}')

        self.stdout.write('\nSE CREARIA:')
        total_cat = total_eq = 0
        for cfg in LIGAS:
            self.stdout.write(f'  {cfg["nombre"]} ({len(cfg["categorias"])} categorias):')
            for nombre, limite, cupo, perfil in cfg['categorias']:
                total_cat += 1
                total_eq += cupo
                self.stdout.write(
                    f'      {nombre:8} {limite:4} {cupo:3} equipos  {perfil:14} '
                    f'{"impar, uno descansa" if cupo % 2 else ""}')
        medio = (JUGADORES_MINIMO + JUGADORES_MAXIMO) // 2
        self.stdout.write(
            f'\n  {total_cat} categorias · {total_eq} equipos · '
            f'~{total_eq * medio} jugadores')

    # ------------------------------------------------------------------- borrar

    def _borrar(self, ligas):
        """Borra en el orden que exigen las claves foraneas.

        Partido antes que Sede y Equipo porque los referencia con PROTECT.
        Equipo antes que Categoria y que los entrenadores, por lo mismo.
        Jugador y Actuacion se van en cascada y no hay que nombrarlos.
        """
        ids = [liga.id for liga in ligas.values()]

        Partido.objects.filter(categoria__liga_id__in=ids).delete()
        Equipo.objects.filter(liga_id__in=ids).delete()
        Sede.objects.filter(liga_id__in=ids).delete()
        Categoria.objects.filter(liga_id__in=ids).delete()
        # El palmares no tiene FK a la liga (guarda el nombre, justamente para
        # sobrevivir a su borrado), asi que se busca por nombre.
        Palmares.objects.filter(liga_nombre__in=list(ligas)).delete()
        # Solo las cuentas que creo este comando. Las 197 que ya existian no se
        # tocan: no las creo el, y borrar cuentas ajenas no es su trabajo.
        Usuario.objects.filter(username__startswith=PREFIJO_DT).delete()

    def _huerfanos(self):
        """Avisa de los entrenadores viejos que quedaron sin equipo.

        No se borran solos: son cuentas que creo otra persona, con contraseñas
        entregadas. Que las elimine quien sepa si se usan.
        """
        sueltos = Usuario.objects.filter(
            role=Usuario.ROLE_ENTRENADOR, equipos__isnull=True,
        ).exclude(username__startswith=PREFIJO_DT).count()
        if sueltos:
            self.stdout.write(self.style.WARNING(
                f'\nQuedaron {sueltos} entrenadores viejos sin ningun equipo. '
                f'No se borraron: son cuentas que no creo este comando.\n'
                f'Para revisarlas y eliminarlas: python manage.py limpiar_entrenadores'))

    # ---------------------------------------------------------------- construir

    def _construir(self, ligas):
        for cfg in LIGAS:
            liga = ligas[cfg['nombre']]
            liga.fecha_inicio = datetime.date(*cfg['inicio'])
            liga.fecha_final = datetime.date(*cfg['final'])
            liga.activa = True
            # Se reabre: la temporada que se va a cargar esta en curso. Si queda
            # alguna categoria sin cerrar, la liga no esta terminada.
            liga.cerrada = False
            liga.fecha_cierre = None
            liga.save()

            sedes = self._crear_sedes(liga, cfg)
            self.stdout.write(f'\n{liga.nombre}')

            # Primero se inscriben TODAS las categorias de la liga y recien
            # despues se juega. No es un detalle de orden: al cargar la final de
            # una categoria el sistema cierra la liga si no le queda ninguna
            # otra en juego, y creandolas de a una la primera en terminar
            # cerraba la liga entera antes de que existieran las demas.
            armadas = []
            for nombre_cat, limite, cupo, perfil in cfg['categorias']:
                categoria = self._crear_categoria(liga, nombre_cat, limite, cupo, perfil)
                equipos = self._crear_equipos(liga, categoria, cfg, sedes, cupo)
                armadas.append((categoria, equipos, perfil, nombre_cat, limite))

            for categoria, equipos, perfil, nombre_cat, limite in armadas:
                self._simular(categoria, equipos, sedes, perfil, cfg)
                self.stdout.write(
                    f'   {nombre_cat:8} {limite:4} {perfil:14} '
                    f'{len(equipos):2} equipos · '
                    f'{Partido.objects.filter(categoria=categoria).count():3} partidos · '
                    f'{Jugador.objects.filter(equipo__categoria=categoria).count():3} jugadores')

            # La liga cierra sola si todas sus categorias terminaron. Se relee
            # porque el cierre de la ultima final pudo haberla tocado.
            liga.refresh_from_db()
            palmares_mod.cerrar_liga_si_termino(liga)

    def _crear_sedes(self, liga, cfg):
        """Una sede por estadio. Dos clubes pueden compartirla (San Siro)."""
        sedes = {}
        for _, nombre, lat, lon in cfg['clubes']:
            if nombre in sedes:
                continue
            sedes[nombre] = Sede.objects.create(
                liga=liga, nombre=nombre,
                direccion='', latitud=lat, longitud=lon,
            )
        return sedes

    def _crear_categoria(self, liga, nombre, limite, cupo, perfil):
        return Categoria.objects.create(
            liga=liga,
            nombre=nombre,
            limite_edad=limite,
            cupo_equipos=cupo,
            # Con calendario generado la inscripcion tiene que estar cerrada: es
            # el requisito que el propio sistema exige para generar los partidos.
            inscripcion_abierta=(perfil == 'sin_calendario'),
            activa=True,
            descripcion=f'Categoria formativa {nombre} de {liga.nombre}.',
        )

    def _crear_equipos(self, liga, categoria, cfg, sedes, cupo):
        equipos = []
        # Se toman los primeros del listado: asi los clubes grandes estan en
        # todas las categorias y los chicos solo en las de cupo amplio, que es
        # como funciona el futbol formativo de verdad.
        for club, nombre_sede, _, _ in cfg['clubes'][:cupo]:
            dt = self._crear_entrenador(liga, categoria, club, cfg['pais'])
            equipo = Equipo.objects.create(
                nombre=club, liga=liga, categoria=categoria, entrenador=dt,
                formacion=self.rng.choice(FORMACIONES),
            )
            # La cancha del club, para que siempre reciba en su estadio. Se
            # guarda por id y no en el objeto: los partidos de liguilla los crea
            # el sistema y llegan aca releidos de la base, sin el atributo.
            self.sede_de_equipo[equipo.id] = sedes[nombre_sede]
            equipo.sede_demo = sedes[nombre_sede]
            self._crear_plantel(equipo, categoria, cfg['pais'])
            equipos.append(equipo)
        return equipos

    def _crear_entrenador(self, liga, categoria, club, pais):
        nombre, apellido = self._persona(pais, 'varon' if self.rng.random() < 0.8 else 'mujer')
        usuario = f'{PREFIJO_DT}{slug(liga.nombre)}-{slug(club)}-{slug(categoria.nombre)}'
        return Usuario.objects.create(
            username=usuario[:150],
            first_name=nombre,
            last_name=apellido,
            role=Usuario.ROLE_ENTRENADOR,
            # Contraseña inutilizable: son cuentas de demostracion y nadie tiene
            # que poder entrar con ellas.
            password=make_password(None),
            organization=club,
        )

    def _persona(self, pais, sexo):
        datos = NOMBRES[pais]
        nombre = self.rng.choice(datos[sexo])
        apellido = self.rng.choice(datos['apellidos'])
        if datos['compuesto']:
            # En Mexico y España se llevan los dos apellidos.
            segundo = self.rng.choice(datos['apellidos'])
            if segundo != apellido:
                apellido = f'{apellido} {segundo}'
        return nombre, apellido

    def _crear_plantel(self, equipo, categoria, pais):
        """El plantel: dorsal unico, posiciones repartidas y edad valida.

        La cantidad se sortea dentro del rango porque los planteles de verdad no
        tienen todos los mismos jugadores.

        Las mujeres se cargan con la tolerancia de un año que permite el
        reglamento, y algunas justo en el limite: es el caso que hay que poder
        ver funcionando en pantalla.
        """
        cantidad = self.rng.randint(JUGADORES_MINIMO, JUGADORES_MAXIMO)
        posiciones = posiciones_para(cantidad)
        dorsales = self.rng.sample(range(1, 41), cantidad)
        anio = categoria.anio_temporada

        jugadores = []
        for indice, posicion in enumerate(posiciones):
            # Alrededor de una de cada cinco es mujer: el sistema es mixto.
            femenino = self.rng.random() < 0.20
            sexo = Jugador.SEXO_FEMENINO if femenino else Jugador.SEXO_MASCULINO
            nombre, apellido = self._persona(pais, 'mujer' if femenino else 'varon')

            tope = categoria.edad_maxima_para(sexo)
            # Un plantel formativo no es todo de la misma edad: hay chicos del
            # año y algunos mas grandes. Las mujeres, ademas, pueden llegar al
            # año extra, y unas cuantas lo usan.
            if femenino and self.rng.random() < 0.35:
                edad = tope
            else:
                edad = self.rng.randint(max(4, tope - 2), tope)
            nacimiento = datetime.date(
                anio - edad, self.rng.randint(1, 12), self.rng.randint(1, 28))

            jugadores.append(Jugador(
                equipo=equipo,
                nombre=nombre,
                apellido=apellido,
                sexo=sexo,
                fecha_nacimiento=nacimiento,
                posicion=posicion,
                numero=dorsales[indice],
                estado=self._estado_jugador(),
            ))
        Jugador.objects.bulk_create(jugadores)

    def _estado_jugador(self):
        sorteo = self.rng.random()
        if sorteo < 0.05:
            return Jugador.ESTADO_LESION
        if sorteo < 0.08:
            return Jugador.ESTADO_SANCION
        if sorteo < 0.10:
            return Jugador.ESTADO_BAJA
        return Jugador.ESTADO_ACTIVO

    # ----------------------------------------------------------------- simular

    def _simular(self, categoria, equipos, sedes, perfil, cfg):
        if perfil == 'sin_calendario':
            return   # equipos inscritos y nada mas: la inscripcion sigue abierta

        partidos = self._generar_calendario(categoria, equipos, perfil)

        if perfil == 'arranque':
            # Calendario recien armado: se juega solo la primera jornada, el
            # resto queda por delante con su fecha puesta.
            self._jugar(partidos, hasta_jornada=1)
            return

        if perfil == 'mitad':
            ultima = max(p.jornada for p in partidos)
            self._jugar(partidos, hasta_jornada=ultima // 2)
            return

        # 'liguilla' y 'terminada' necesitan el torneo regular completo.
        self._jugar(partidos)
        self._simular_liguilla(categoria, sedes, hasta_el_final=(perfil == 'terminada'))

    def _generar_calendario(self, categoria, equipos, perfil):
        """Arma el fixture con el mismo round-robin que usa el sistema."""
        jornadas = armar_jornadas(equipos)

        # De donde arranca el calendario, para que hoy la categoria este justo
        # en el punto que pide su perfil: lo jugado queda atras y lo que falta,
        # por delante.
        if perfil == 'arranque':
            primera = self.hoy - datetime.timedelta(days=7)
        elif perfil == 'mitad':
            primera = self.hoy - datetime.timedelta(days=7 * (len(jornadas) // 2))
        else:
            primera = self.hoy - datetime.timedelta(days=7 * (len(jornadas) + 6))

        creados = []
        for numero, cruces in enumerate(jornadas, start=1):
            dia = primera + datetime.timedelta(days=7 * (numero - 1))
            for local, visitante in cruces:
                hora = self.rng.choice([9, 10, 11, 12, 16, 17])
                cuando = timezone.make_aware(
                    datetime.datetime.combine(dia, datetime.time(hora, 0)))
                creados.append(Partido(
                    categoria=categoria,
                    equipo_local=local, equipo_visitante=visitante,
                    # `orden` es la llave del cuadro de liguilla: en el torneo
                    # regular no significa nada y queda en cero.
                    jornada=numero, orden=0,
                    fecha=cuando, fecha_original=cuando,
                    sede=local.sede_demo, sede_original=local.sede_demo,
                    estado=Partido.ESTADO_PROGRAMADO,
                ))
        Partido.objects.bulk_create(creados)
        self._mover_algunos(creados)
        return creados

    def _mover_algunos(self, partidos):
        """Reprogramaciones y cambios de cancha.

        Se guardan como los guarda el sistema: `fecha` cambia y `fecha_original`
        queda con la primera, que es lo que permite avisar 'se reprogramo' aun
        despues de que el partido termino.
        """
        for partido in partidos:
            if self.rng.random() < 0.10:
                partido.fecha = partido.fecha + datetime.timedelta(days=self.rng.choice([1, 2, 7]))
                partido.estado = Partido.ESTADO_REPROGRAMADO
                partido.save(update_fields=['fecha', 'estado'])
            if self.rng.random() < 0.06:
                otras = list(Sede.objects.filter(
                    liga=partido.categoria.liga).exclude(pk=partido.sede_id))
                if otras:
                    partido.sede = self.rng.choice(otras)
                    partido.save(update_fields=['sede'])

    def _jugar(self, partidos, hasta_jornada=None):
        for partido in partidos:
            if hasta_jornada is not None and partido.jornada > hasta_jornada:
                continue
            self._cargar_resultado(partido)

    def _cargar_resultado(self, partido, es_final=False):
        """Carga un resultado con sus goleadores, respetando todas las reglas.

        Las mismas que valida `actuaciones.errores` al cargarlo por pantalla:
        los goles asignados tienen que dar el marcador, y no puede haber mas
        asistencias que goles de jugada.
        """
        # Un equipo no se presenta cada tanto: el rival gana 3-0 y no hay nada
        # que cargar. Es un caso raro pero existe, y el sistema lo contempla.
        if not partido.es_liguilla and self.rng.random() < 0.03:
            ausente = self.rng.choice([partido.equipo_local, partido.equipo_visitante])
            partido.no_se_presento = ausente
            if ausente.id == partido.equipo_local_id:
                partido.goles_local, partido.goles_visitante = 0, Partido.MARCADOR_DEFAULT
            else:
                partido.goles_local, partido.goles_visitante = Partido.MARCADOR_DEFAULT, 0
            partido.estado = Partido.ESTADO_FINALIZADO
            partido.save()
            return

        goles_local = self._marcador()
        goles_visitante = self._marcador()

        # Una de cada tres finales se va a los penales. Se fuerza el empate en
        # vez de esperar a que salga solo: la tanda que corona campeon es de los
        # caminos mas delicados del sistema y tiene que quedar cargado en los
        # datos, no depender de la suerte del sorteo.
        if es_final and self.rng.random() < 0.35:
            goles_visitante = goles_local

        if es_final and goles_local == goles_visitante:
            # La final empatada se define por penales, y el sistema exige la
            # tanda cargada. Se dibuja como en television.
            tiros = self.rng.randint(3, 5)
            perdidos = self.rng.randint(1, 2)
            gana_local = self.rng.random() < 0.5
            partido.penales_local = tiros if gana_local else tiros - perdidos
            partido.penales_visitante = tiros - perdidos if gana_local else tiros
            partido.ganador_penales = (
                partido.equipo_local if gana_local else partido.equipo_visitante)
        elif not partido.es_liguilla and goles_local == goles_visitante and self.rng.random() < 0.30:
            # En el torneo regular el empate se puede desempatar por penales:
            # el que gana la tanda se lleva un punto extra.
            tiros = self.rng.randint(3, 5)
            gana_local = self.rng.random() < 0.5
            partido.penales_local = tiros if gana_local else tiros - 1
            partido.penales_visitante = tiros - 1 if gana_local else tiros
            partido.ganador_penales = (
                partido.equipo_local if gana_local else partido.equipo_visitante)

        partido.goles_local = goles_local
        partido.goles_visitante = goles_visitante
        partido.estado = Partido.ESTADO_FINALIZADO
        partido.save()

        self._repartir(partido, goles_local, goles_visitante)

    def _marcador(self):
        """Un marcador de futbol formativo: casi siempre entre 0 y 4."""
        return self.rng.choices(
            [0, 1, 2, 3, 4, 5, 6],
            weights=[18, 26, 22, 15, 10, 6, 3],
        )[0]

    def _repartir(self, partido, goles_local, goles_visitante):
        """Convierte el marcador en goleadores, asistentes y goles en contra.

        Un gol en contra suma al marcador del rival: por eso se descuenta de los
        goles que reparten los jugadores propios y se carga en un jugador del
        otro equipo.
        """
        planteles = {
            'local': self._disponibles(partido.equipo_local_id),
            'visitante': self._disponibles(partido.equipo_visitante_id),
        }
        if not planteles['local'] or not planteles['visitante']:
            return

        filas = {}

        def sumar(jugador_id, campo, cantidad):
            fila = filas.setdefault(jugador_id, {
                'goles': 0, 'goles_en_contra': 0, 'goles_de_penal': 0, 'asistencias': 0})
            fila[campo] += cantidad

        for lado, rival, marcador in (
            ('local', 'visitante', goles_local),
            ('visitante', 'local', goles_visitante),
        ):
            if not marcador:
                continue

            # Uno de cada veinticinco goles es en contra del rival.
            en_contra = 1 if (marcador and self.rng.random() < 0.04) else 0
            if en_contra:
                sumar(self.rng.choice(planteles[rival]).id, 'goles_en_contra', 1)

            propios = marcador - en_contra
            penales = 0
            for _ in range(propios):
                goleador = self._goleador(planteles[lado])
                sumar(goleador.id, 'goles', 1)
                # Uno de cada siete goles llega desde el punto penal. Va DENTRO
                # de `goles`, no aparte: al marcador ya sumo.
                if self.rng.random() < 0.14:
                    sumar(goleador.id, 'goles_de_penal', 1)
                    penales += 1

            # Un penal no se asiste, y un gol en contra tampoco: el tope de
            # asistencias son los goles de jugada del equipo.
            asistibles = propios - penales
            for _ in range(asistibles):
                if self.rng.random() < 0.55:
                    sumar(self.rng.choice(planteles[lado]).id, 'asistencias', 1)

        Actuacion.objects.bulk_create([
            Actuacion(partido=partido, jugador_id=jid, **valores)
            for jid, valores in filas.items() if any(valores.values())
        ])

    def _disponibles(self, equipo_id):
        """Los que pueden jugar: un lesionado o un sancionado no anota."""
        if equipo_id not in self._cache_planteles:
            self._cache_planteles[equipo_id] = list(
                Jugador.objects.filter(equipo_id=equipo_id, estado=Jugador.ESTADO_ACTIVO))
        return self._cache_planteles[equipo_id]

    def _goleador(self, plantel):
        """Los goles no se reparten parejo: los hace mas el que juega adelante."""
        pesos = {'delantero': 10, 'medio': 5, 'defensa': 2, 'portero': 1}
        return self.rng.choices(plantel, weights=[pesos[j.posicion] for j in plantel])[0]

    # ---------------------------------------------------------------- liguilla

    def _simular_liguilla(self, categoria, sedes, hasta_el_final):
        """Juega la liguilla usando el motor del sistema, ronda por ronda.

        No se arman los cruces a mano: los arma `liguilla.iniciar` con la
        siembra que sale de la tabla, y `liguilla.avanzar` crea la ronda
        siguiente al cerrarse la anterior. Asi el cuadro que queda en la base es
        el que el sistema habria armado solo.
        """
        motivo = liguilla_mod.motivo_para_no_iniciar(categoria)
        if motivo:
            self.stderr.write(f'      liguilla no iniciada: {motivo}')
            return

        liguilla_mod.iniciar(categoria)

        # Hasta donde se juega. Si la categoria no tiene que terminar, se corta
        # antes de la final para que quede una liguilla en curso de verdad.
        fases = [Partido.FASE_CUARTOS, Partido.FASE_SEMIFINAL,
                 Partido.FASE_TERCERO, Partido.FASE_FINAL]
        if not hasta_el_final:
            fases = fases[:1]

        dia = self.hoy - datetime.timedelta(days=35)
        for fase in fases:
            pendientes = list(Partido.objects.filter(
                categoria=categoria, fase=fase, estado__in=Partido.ESTADOS_POR_JUGARSE,
            ).select_related('equipo_local', 'equipo_visitante').order_by('orden', 'vuelta'))
            if not pendientes:
                continue

            for partido in pendientes:
                cuando = timezone.make_aware(
                    datetime.datetime.combine(dia, datetime.time(self.rng.choice([11, 16]), 0)))
                partido.fecha = cuando
                partido.fecha_original = cuando
                sede = self._sede_de(partido.equipo_local, sedes)
                partido.sede = sede
                partido.sede_original = sede
                partido.save(update_fields=['fecha', 'fecha_original', 'sede', 'sede_original'])

                self._cargar_resultado(partido, es_final=(fase == Partido.FASE_FINAL))
                # Cerrada la ronda, el sistema arma la siguiente solo.
                liguilla_mod.avanzar(partido)
                if fase == Partido.FASE_FINAL:
                    palmares_mod.cerrar_si_termino(partido)
            dia += datetime.timedelta(days=7)

    def _sede_de(self, equipo, sedes):
        """La cancha del club que hace de local en ese cruce."""
        return self.sede_de_equipo.get(equipo.id) or self.rng.choice(list(sedes.values()))
