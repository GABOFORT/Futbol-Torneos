# Análisis integral del sistema — BUHO Sports League

> Revisión completa del código, el diseño, el flujo de negocio y la base de datos.
> **Fecha del análisis:** 3 de agosto de 2026
> **Alcance:** todo el proyecto `Futbol-Torneos` + inspección de solo lectura de la base `SISTEMA-FUTBOL`.
>
---

## ⚠️ Este documento es un documento vivo

**Todo cambio en el sistema se documenta aquí, en la misma tanda en que se hace.**
No después, no "cuando haya tiempo".

Aplica a: reglas de negocio · flujos · diseño · modelo de datos · permisos ·
vistas · validaciones. Ya sea que se **agregue**, se **modifique** o se **elimine**.

Al hacer un cambio hay que:

1. Actualizar la sección afectada (modelo, flujo, tabla de reglas, matriz de permisos).
2. Si el cambio resuelve un hallazgo, **marcarlo como resuelto con la fecha** — no
   borrarlo, para que quede el rastro de qué se arregló y cuándo.
3. Anotar el cambio en la [bitácora](#10-bitácora-de-cambios) al final del archivo.
4. Verificar los números de línea citados: se desfasan al tocar el código.

> El motivo de esta regla es concreto: el `README.md` de este mismo proyecto quedó
> describiendo un flujo que ya no existía (decía que el entrenador registra su equipo
> y que había un paso de aprobación; ninguna de las dos cosas es cierta). Un documento
> desactualizado es peor que no tener documento, porque se le cree.

---

---

## Índice

1. [Qué es el sistema](#1-qué-es-el-sistema)
2. [Arquitectura](#2-arquitectura)
3. [Modelo de datos](#3-modelo-de-datos)
4. [Flujo real del sistema](#4-flujo-real-del-sistema)
5. [Permisos y visibilidad](#5-permisos-y-visibilidad)
6. [Estado real de la base de datos](#6-estado-real-de-la-base-de-datos)
7. [Hallazgos](#7-hallazgos)
8. [Lo que está bien hecho](#8-lo-que-está-bien-hecho)
9. [Recomendaciones priorizadas](#9-recomendaciones-priorizadas)
10. [Bitácora de cambios](#10-bitácora-de-cambios)

---

## 1. Qué es el sistema

Plataforma Django para administrar ligas de fútbol infantil y juvenil. Encadena
ligas → categorías → equipos → jugadores → partidos → estadísticas, con tres roles
jerárquicos y una capa pública (vitrina) accesible sin iniciar sesión.

La liga real en producción es **Liga Premier Villahermosa** (categorías Hormiguitas y
Pandas). Las otras seis ligas cargadas —La Liga, Liga MX, Premier League, Serie A,
Bundesliga, Cachirules— son datos de prueba.

### Stack

| Capa | Tecnología |
|---|---|
| Backend | Django 6.0.6 · Python 3.14 |
| Base de datos | PostgreSQL (`SISTEMA-FUTBOL`) |
| Estilos | Tailwind CSS vía CLI standalone (sin Node/npm) |
| Imágenes | Pillow (redimensionado automático a 512 px) |
| Configuración | python-decouple (`.env`) |
| Mapas | Leaflet (vendorizado en `static/vendor/`) |
| Frontend | Server-rendered + JS vanilla (~800 líneas, sin framework) |
| Producción | waitress detrás de IIS como proxy inverso |

---

## 2. Arquitectura

Siete apps con separación real de responsabilidades, no solo carpetas:

| App | Responsabilidad |
|---|---|
| `apps/usuarios` | Modelo `Usuario`, permisos, y **utilidades transversales**: `filtros.py`, `eliminar.py`, `imagenes.py`, `archivos.py`, `estaticos.py` |
| `apps/torneos` | `Liga`, `Categoria`, `Sede` + la portada del sitio |
| `apps/equipos` | CRUD de equipos |
| `apps/jugadores` | CRUD de plantillas |
| `apps/partidos` | `Partido`, `Actuacion` + lógica en módulos separados |
| `apps/estadisticas` | Tablas de posiciones, goleo, asistencias, porterías |
| `apps/informacion` | Páginas estáticas (quiénes somos, reglamento, privacidad) |

### Módulos de lógica pura

La decisión arquitectónica más importante del proyecto: **la lógica de negocio no vive
en las vistas**. Está en módulos independientes y testeables:

| Módulo | Qué resuelve |
|---|---|
| `apps/partidos/calendario.py` | Round-robin por método del círculo (jornadas, localía alternada, equipo que descansa) |
| `apps/partidos/liguilla.py` | Cuadro de eliminación: formato, siembra, avance de rondas, dibujo del bracket |
| `apps/partidos/ficha.py` | Todos los números de la ficha de partido (rendimiento, historial, figuras, plantel) |
| `apps/partidos/actuaciones.py` | Lectura y validación de goles/asistencias del POST |
| `apps/estadisticas/tabla.py` | Cálculo de la tabla de posiciones (fuente única de la regla de puntos) |
| `apps/estadisticas/porteros.py` | Porterías menos vencidas, agrupadas por categoría |

`tabla.calcular()` la consumen **tres** pantallas distintas: la tabla de posiciones,
la ficha de partido (para el puesto de cada equipo) y la siembra de la liguilla. La
regla de "cuántos puntos vale un empate con penales ganados" está escrita una sola vez.

---

## 3. Modelo de datos

```
Usuario (AbstractUser)
  ├─ role: superadmin | adminliga | entrenador
  ├─ creado_por → self               (define quién puede ver y editar a quién)
  ├─ limite_ligas                    (cuota comercial por Admin Liga)
  └─ phone, organization

Liga ──M2M── Usuario(role=adminliga)
  ├─ fecha_pago + dias_gracia        (ciclo de cobranza mensual)
  ├─ activa                          (visibilidad pública)
  ├─ logo                            (o las iniciales, si no hay)
  ├─ portada                         (fondo de las pantallas de esta liga)
  │
  ├─ Categoria      [unique: liga + nombre]
  │     ├─ cupo_equipos
  │     ├─ inscripcion_abierta
  │     │
  │     ├─ QUIÉN ENTRA  (`libre` manda sobre los tres límites)
  │     │   ├─ libre                 (sin restricción: cualquier edad, peso y sexo)
  │     │   ├─ limite_edad  U5 … U17 (máximo; por año de nacimiento)
  │     │   │                        (+1 año para mujeres: U17 admite una de 18)
  │     │   ├─ edad_minima  30 … 80  (mínimo; categorías de veteranos)
  │     │   └─ peso_minimo  50 … 100 (kg; obliga a cargar `Jugador.peso`)
  │     │
  │     └─ CÓMO SE JUEGA  (se congela al generar los partidos)
  │         ├─ vueltas  1 | 2        (2 = ida y vuelta, localía invertida)
  │         ├─ empate_define_penales (apagado: el empate vale 1 punto y nada más)
  │         └─ mini_liguilla         (puestos 9-12; necesita 12 equipos o más)
  │
  ├─ Sede           [unique: liga + nombre]
  │     └─ latitud / longitud  (9 dígitos, 6 decimales → precisión < 1 m)
  │
  └─ Equipo         [unique: nombre + liga + categoria]
        ├─ entrenador → Usuario  [PROTECT]
        ├─ formacion
        └─ Jugador               [CASCADE]
              ├─ sexo: masculino | femenino   (define su límite de edad)
              └─ [unique parcial: equipo + numero, si numero no es NULL]

Partido
  ├─ categoria, equipo_local, equipo_visitante
  ├─ jornada, fase (''|cuartos|semifinal|tercero|final), orden
  ├─ siembra_local / siembra_visitante     (puesto en la tabla, viaja entre rondas)
  ├─ fecha + fecha_original                (para detectar reprogramación)
  ├─ sede + sede_original                  (para detectar cambio de cancha)
  ├─ goles_local / goles_visitante
  ├─ ganador_penales + penales_local / penales_visitante
  ├─ no_se_presento → Equipo        (ganado por default: el rival se lleva 3-0)
  └─ estado: programado | reprogramado | finalizado | cancelado
        │
        └─ Actuacion   [unique: partido + jugador]
              └─ goles, goles_en_contra, goles_de_penal, asistencias
```

> **`goles_de_penal` va dentro de `goles`, no aparte.** Un penal convertido
> durante el juego es un gol como cualquier otro: suma al marcador, a la tabla de
> goleo y a la bota de oro. El campo existe solo para poder decirlo en la ficha.
> No confundirlo con `Partido.penales_local` / `penales_visitante`, que son la
> **tanda que desempata**: esos no son goles, no crean ninguna `Actuacion`, y solo
> definen el punto extra en el regular o quién pasa en la liguilla.

### Decisiones de diseño acertadas

- **`fecha_original` / `sede_original`** — guardar el valor inicial permite decir "se
  reprogramó" y "cambió de cancha" *incluso después* de que el partido pasó a
  finalizado. El campo `estado` solo no alcanzaba, porque al cargar el resultado se
  perdía el rastro.

- **`siembra_local` / `siembra_visitante`** — el puesto en la tabla viaja con el equipo
  de ronda en ronda. Es lo que desempata sin necesidad de penales en cuartos y semis:
  la ventaja ganada durante el torneo regular. Muy bien pensado.

- **`Actuacion` agregada** — una fila por jugador con `goles=2`, no dos filas. Hace la
  carga mucho más rápida. El costo (no se sabe el minuto ni qué asistencia fue de qué
  gol) está documentado en el docstring del modelo.

- **`penales_local` / `penales_visitante` separados de `goles_*`** — un penal convertido
  en la tanda no es un gol del partido; el marcador sigue siendo el empate. Correcto
  según reglamento, y permite dibujar la tanda como en televisión.

- **`Sede` como tabla propia** en vez de texto libre dentro de `Partido` — la misma
  cancha se repite en decenas de partidos; corregir un pin mal puesto arregla todos.

- **Constraint parcial en el dorsal** — `UniqueConstraint(fields=['equipo','numero'],
  condition=Q(numero__isnull=False))`. Un equipo puede tener varios jugadores sin
  número, pero no dos con el 10.

### Puntos débiles del modelo

- **`Equipo.liga` es redundante** — se puede derivar de `categoria.liga`. Se valida por
  formulario, pero nada a nivel de base de datos impide que se desincronicen. Hoy están
  sanos (0 inconsistencias verificadas).

- **Un club en 3 categorías son 3 registros de `Equipo`** — por eso `ficha.historial()`
  tiene que buscar los enfrentamientos previos *por nombre* en vez de por ID. Funciona
  y está documentado, pero un modelo `Club` padre lo resolvería limpio.

- **Falta la entidad `Torneo`** que promete el README. Hoy la categoría *es* el torneo:
  no existe Apertura/Clausura, y volver a jugar una temporada implicaría borrar los
  partidos anteriores y perder el histórico.

- **Sin índices compuestos** en `Partido(categoria, fase, estado)` — el filtro más
  repetido de todo el sistema.

---

## 4. Flujo real del sistema

```
SUPERADMIN
   ├─ crea Admin Liga  (asignándole limite_ligas)
   ├─ registra los pagos mensuales de cada liga
   ├─ elimina ligas y usuarios
   └─ CORRIGE resultados ya cargados       ← exclusivo suyo

ADMIN LIGA
   ├─ crea su Liga (hasta su cuota)
   ├─ crea Categorías        (límite de edad + cupo de equipos)
   ├─ crea Entrenadores      (quedan marcados con creado_por = él)
   ├─ crea Equipos           (checkbox por categoría → N equipos de una vez)
   ├─ CIERRA INSCRIPCIÓN     ← requisito obligatorio para el paso siguiente
   ├─ GENERA PARTIDOS        (round-robin automático)
   ├─ asigna fecha + cancha  (marcando el pin en un mapa Leaflet)
   ├─ carga resultado + goleadores + asistentes
   ├─ INICIA LIGUILLA        (solo si el torneo regular terminó)
   └─ cada resultado de liguilla arma solo la ronda siguiente

ENTRENADOR
   ├─ ve únicamente sus equipos y sus partidos
   ├─ edita formación y observaciones de su equipo
   └─ gestiona la plantilla de jugadores (alta, baja, lesión, sanción)

PÚBLICO (sin cuenta)
   └─ tablas de posiciones, goleo, asistencias, porterías,
      ficha completa de partido y cuadro de liguilla
```

### Reglas de negocio implementadas

| Regla | Dónde vive |
|---|---|
| Al cargar el resultado de la final, la categoría se cierra sola | `palmares.cerrar_si_termino` |
| La liga cierra cuando todas sus categorías activas están cerradas | `palmares.cerrar_liga_si_termino` |
| El campeón sale del cuadro de liguilla, no de la tabla regular | `palmares._nombre_del_puesto` |
| Bota de oro y trofeo de asistencias son individuales, sin importar el equipo | `palmares._mejores_jugadores` |
| El guante de oro es del equipo con menos goles recibidos | `palmares._mejores_vallas` |
| Los empates se premian compartidos, en los tres premios | idem |
| Al eliminar una liga se van también **las cuentas de sus entrenadores** | `eliminar.entrenadores_sin_equipo_tras_borrar` |
| Un entrenador que además dirige en otra liga **se conserva** | idem (se mira lo que le queda, no lo que se va) |
| Un entrenador recién dado de alta, sin equipo todavía, no se toca | idem |
| El **Administrador de Liga no se borra** con su liga: es la cuenta del cliente y tiene su propia cuota | decisión de negocio, 06/08/2026 |
| Una liga concluida no cuenta contra `limite_ligas` | `usuarios/views.py::liga_create` |
| Una liga concluida no se puede borrar antes de 30 días | `usuarios/views.py::liga_delete` |
| Corregir la final recalcula el palmarés; corregir una semi lo elimina | `palmares.cerrar` / `palmares.reabrir` |
| Corregir un resultado que cambia el ganador rehace los cruces afectados | `liguilla.avanzar` |
| No se generan partidos con la inscripción abierta | `torneos/views.py::categoria_generar_partidos` |
| Mínimo 2 equipos para generar partidos | idem |
| Con calendario generado, un equipo nuevo entra entre la J2 y la J4 | `altas.jornada_de_ingreso` |
| La ventana se cierra al jugarse el primer partido de la J4 | `altas.motivo_para_no_agregar` |
| El equipo nuevo entra en la primera jornada sin partidos jugados | idem |
| Al entrar solo se crean SUS partidos: ninguno existente se mueve | `altas.agregar` |
| Sus partidos llenan primero los descansos; los que no caben quedan **pendientes** | `altas.plan` |
| Un partido pendiente no pertenece a ninguna jornada y se programa aparte | `Partido.fuera_de_jornada` |
| Los pendientes no cuentan para el descanso ni entran en el bloque de su jornada | `partidos/views.py::_agrupar` |
| El calendario les da su propia pastilla, junto a la de Liguilla | `_pastillas_jornada` |
| **Torneo relámpago: un día, eliminación directa, 8 o 16 equipos** | `Torneo` §3 |
| Solo lo crean el Administrador General y el Admin de Liga | `torneos.py::torneo_create` |
| Se apoya en una Liga con una sola Categoría, oculta del apartado de ligas | `ligas_administradas` / `ligas_visibles` |
| Todas las rondas van a partido único, sin ida y vuelta | `Partido.cierra_la_llave` |
| El empate se define en penales **en cualquier ronda** | `Partido.ganador` |
| El cuadro sale de un sorteo al azar, no de una siembra | `relampago.sortear` |
| No se puede sortear hasta tener los 8 o 16 equipos | `relampago.motivo_para_no_sortear` |
| Las rondas se programan con horas corridas del mismo día | `relampago._programar` |
| Un relámpago no deja palmarés de liga: su campeón sale del cuadro | `palmares.cerrar_si_termino` |
| Al jugarse su final graba palmarés propio, sin tabla final | `palmares.cerrar_torneo_si_termino` |
| Los relámpago salen en Inicio y en la vitrina, marcados como tales | `portada.relampagos` / `Palmares.es_torneo` |
| Las pantallas que listan separan liga y torneo; las que abren UN objeto, no | `ligas_y_torneos_visibles` / `..._administrados` |
| El Admin de Liga tiene cuota de torneos, igual que la de ligas | `Usuario.limite_torneos` |
| Un torneo terminado **no ocupa cuota**: se puede armar el siguiente | `torneos.motivo_para_no_crear` |
| Terminado = su final ya se jugó; no hay campo de estado que mantener | `Torneo.terminado` / `TorneoQuerySet.en_curso` |
| Un torneo terminado se exhibe 30 días antes de poder borrarse | `Torneo.dias_en_vitrina` |
| **En un relámpago solo se premia a los equipos**: sin bota de oro, guante ni asistencias | `palmares.cerrar_torneo_si_termino` |
| El cuadro se encoge con la pantalla y desborda dentro de su marco, no de la página | `.bracket-marco` · `--bracket-ronda` |
| Cantidad impar de equipos → uno descansa por jornada | `calendario.armar_jornadas` |
| No se inicia liguilla con partidos pendientes | `liguilla.motivo_para_no_iniciar` |
| Tamaño del cuadro según equipos: ≥8 cuartos, ≥4 semis, ≥2 final | `liguilla.formato` |
| Empate en cuartos/semis → pasa el mejor de la tabla, sin penales | `Partido.ganador` |
| **El formato lo decide cada categoría, no la liga** | `Categoria` §3 |
| A dos vueltas, la segunda es la primera con la localía invertida | `calendario.armar_jornadas` |
| Con el punto extra apagado, un empate vale 1 punto y no se ofrecen penales | `tabla.calcular` / `ResultadoForm` |
| El formato se congela al generar los partidos | `Categoria.ajustes_congelados` |
| Una sola puerta de entrada por categoría, en cascada: Libre › límite U › mínimos | `Categoria._error_de_restricciones` |
| El que gana limpia a los demás en vez de rechazar | idem |
| Una categoría no libre exige al menos un límite | idem |
| El peso solo es obligatorio donde hay peso mínimo | `Categoria.exige_peso` |
| Mini-liguilla: puestos 9-12, ida y vuelta, con tercer lugar | `liguilla.formato_mini` |
| La mini-liguilla necesita 12 equipos o más | `Categoria.juega_mini_liguilla` |
| Con mini-liguilla marcada, el cupo no puede ser menor a 12 | `Categoria._error_de_cupo` |
| Los dos cuadros avanzan por separado y no se mezclan | `Partido.cuadro` / `liguilla.series` |
| La siembra de la mini es su puesto real (9-12), no 1-4 | `liguilla._armar_cuadro` |
| **Solo la final del cuadro principal cierra la categoría** | `palmares.cerrar_si_termino` |
| Empate en la final → obligatorio cargar la tanda de penales | `ResultadoForm.clean` |
| Los goles cargados deben cuadrar con el marcador | `actuaciones.errores` |
| No hay más asistencias que goles | idem |
| Gol en contra suma al marcador del rival, no a la tabla de goleo | `Partido._asignados` |
| Un gol de penal del juego cuenta como gol normal (marcador, goleo, bota de oro) | `Actuacion.goles_de_penal` |
| Un penal no lleva asistencia: asistencias ≤ goles − goles de penal | `actuaciones.errores` |
| Un gol en contra no puede ser de penal | `actuaciones.leer` + `actuaciones.js` |
| Si un equipo no se presenta, el rival gana **3-0** (fijo, igual en toda liga) | `Partido.MARCADOR_DEFAULT` · `ResultadoForm.clean` |
| Un partido ganado por default no lleva goleadores ni asistencias | `partidos/views.py::partido_resultado` |
| El 3-0 por default cuenta normal en la tabla, y como valla invicta para el que sí llegó | `tabla.calcular`, `porteros.calcular` (sin cambios: es un 3-0 real) |
| El equipo ausente no recibe sanción extra: solo pierde | decisión de negocio, 05/08/2026 |
| La liguilla no cuenta para la tabla ni para porterías | `tabla.calcular`, `porteros.calcular` |
| Un jugador no entra si supera el límite de edad de la categoría | `Categoria.acepta` + `JugadorForm.clean` |
| **Las mujeres entran con un año más que la categoría** (U17 admite una de 18, U15 una de 16) | `Categoria.ANIOS_EXTRA_FEMENINO` |
| La tolerancia es de **un solo año** y es igual en todas las ligas | idem (constante, no campo configurable) |
| Todas las categorías son mixtas: no hay rama varonil ni femenil | decisión de negocio, 06/08/2026 |
| Ante la duda se aplica el límite estricto, el de los varones | `Categoria.edad_maxima_para` |
| El dorsal no se repite dentro del equipo | `JugadorForm.clean_numero` + constraint |
| No se carga resultado de un partido que no empezó | `partidos/views.py::partido_resultado` |
| No se reprograma un partido que ya tiene resultado | `partidos/views.py::partido_edit` |
| Liga vencida → el Admin Liga no puede entrar | `usuarios/views.py::_liga_bloqueada` |

### Diferencias con el README

El `README.md` está desactualizado y describe un flujo que ya no es el real:

| El README dice | La realidad |
|---|---|
| "El entrenador registra su equipo" | El **Admin Liga** crea el equipo y se lo asigna. El entrenador solo edita formación y observaciones |
| "Admin Liga revisa y aprueba equipos" | **No existe** flujo de aprobación. El cupo y el estado de inscripción hacen ese control |
| `Torneo` como entidad del modelo | No existe; la categoría cumple ese rol |
| El "Todo list" del final | Desactualizado: hay mucho más implementado de lo que lista |

**Acción sugerida:** reescribir las secciones 3 a 6 del README con el flujo de arriba.

---

## 5. Permisos y visibilidad

`apps/usuarios/permissions.py` separa dos ejes, y esa separación es correcta:

- **`ligas_administradas(user)`** → sobre qué puede **escribir**
- **`ligas_visibles(user)`** → qué puede **ver**: **lo público más lo propio**, es decir
  las ligas `activa=True` (la vitrina, que ve cualquiera) más las que uno administra
  aunque estén desactivadas

> **Corregido el 12/08/2026.** Hasta esa fecha `ligas_visibles` devolvía
> `ligas_administradas(user)` para el Admin de Liga, con el razonamiento de que cada liga
> es un negocio aparte. Eso vale para la **gestión**, no para la **vitrina**: aplicado a
> las pantallas públicas dejaba al administrador viendo *menos* que un visitante sin
> cuenta. Ver la bitácora del 12/08.

El tablero (`apps/usuarios/views.py`) **no usa esta función**: se acota con
`ligas_administradas` en todas sus consultas, así que sigue mostrando únicamente la liga
propia. Esa es la separación: gestión con una, vitrina con la otra.

Y un tercer nivel: **`Usuario.objects.entrenadores(para=...)`** acota por `creado_por`,
para que un Admin Liga no pueda ver ni editar los entrenadores dados de alta por otro.

### Matriz efectiva de permisos

| Acción | Superadmin | Admin Liga | Entrenador | Público |
|---|:-:|:-:|:-:|:-:|
| Usuarios (CRUD) | ✅ | ❌ | ❌ | ❌ |
| Entrenadores | ✅ | solo los suyos | ❌ | ❌ |
| Ligas: crear / editar | ✅ | ✅ (con cuota) | ❌ | ❌ |
| Ligas: eliminar | ✅ | ❌ | ❌ | ❌ |
| Registrar pago | ✅ | ❌ | ❌ | ❌ |
| Categorías / generar partidos / liguilla | ✅ | sus ligas | ❌ | ❌ |
| Equipos: crear / eliminar | ✅ | sus ligas | ❌ | ❌ |
| Equipo: formación y observaciones | ✅ | ✅ | su equipo | ❌ |
| Jugadores | ✅ | sus ligas | su equipo | ❌ |
| Partidos: fecha y cancha | ✅ | sus ligas | ❌ | ❌ |
| Resultado: cargar | ✅ | ✅ | ❌ | ❌ |
| Resultado: **corregir** | ✅ | ❌ | ❌ | ❌ |
| Estadísticas y ficha de partido | ✅ | ✅ | ✅ | ✅ |

Que **corregir un resultado ya cargado sea exclusivo del superadmin** es una buena
decisión de control interno: un error de tipeo no queda grabado para siempre, pero el
partido queda cerrado en el uso diario.

### Bloqueo por falta de pago

`Liga.fecha_pago` + 1 mes + `dias_gracia` (3 por defecto) = fecha límite. Si se pasa,
`_liga_bloqueada()` impide el login del Admin Liga y lo desloguea si ya estaba dentro.
El dashboard avisa cuando faltan 7 días o menos.

---

## 6. Estado real de la base de datos

Inventario **reconstruido el 06/08/2026**. Ese día pasaron dos cosas que cambian por
completo la foto anterior:

1. El superadmin **eliminó Liga Premier Villahermosa y Cachirules** desde la pantalla
   de ligas. Villahermosa era la única liga real en producción.
2. Las cinco ligas restantes se **regeneraron con datos de demostración coherentes**
   (ver la bitácora del 06/08 y `crear_datos_demo`).

Hoy **no queda ninguna liga real cargada**: las cinco que hay son de demostración.

### Volumen

| Tabla | 03/08 | 06/08 |
|---|---:|---:|
| Usuario | 204 | **408** |
| Liga | 7 | **5** |
| Categoria | 13 | **20** |
| Sede | 2 | **87** |
| Equipo | 202 | **211** |
| Jugador | 2 832 | **3 478** |
| Partido | 225 | **1 388** |
| Actuacion | 746 | **6 167** |
| Palmares | — | **8** |

**Usuarios por rol:** 2 superadmin · 6 admin liga · 400 entrenadores
(de esos, **197 son cuentas huérfanas** de las ligas borradas antes de que el borrado
arrastrara a sus entrenadores; se limpian con `manage.py limpiar_entrenadores`)

### Ligas cargadas

Todas son de demostración. Los clubes y los estadios son reales; las personas no.

| Liga | Categorías | Equipos | Sedes | Partidos | Estado |
|---|---:|---:|---:|---:|---|
| Bundesliga | 4 | 47 | 20 | 333 | 1 categoría concluida, 3 en juego |
| Liga MX | 3 | 31 | 15 | 164 | 1 concluida, 2 en juego |
| Premier League | 5 | 59 | 20 | 419 | 1 concluida, 4 en juego |
| Serie A | 2 | 17 | 12 | 109 | **concluida** · 30 días en vitrina |
| La Liga | 6 | 57 | 20 | 363 | 3 concluidas, 3 en juego |

**Cupos de 3 a 20 equipos**, quince tamaños distintos y siete categorías con cupo impar
(donde un equipo descansa cada jornada). Los planteles van de 13 a 20 jugadores.

**Ninguna liga tiene `fecha_pago` cargada**, así que hoy ninguna está vencida y el
bloqueo por cobranza nunca se disparó en la práctica.

### Palmarés grabados

Ocho categorías concluidas, con el podio y los premios congelados:

| Liga / Categoría | Campeón | Bota de oro | Guante de oro |
|---|---|---|---|
| Bundesliga / Sub-11 | Bayern München | Theo Braun (12) | 1. FC Nürnberg / B… (23) |
| Liga MX / Sub-13 | Pumas UNAM | Daniel Reyes Ramírez (11) | Puebla (15) |
| Premier League / Sub-9 | Newcastle United | Jack Walker, del Fulham (15) | Newcastle United (29) |
| Serie A / Sub-15 | Cagliari | Martina Russo, del Juventus (10) | Atalanta (13) |
| Serie A / Sub-17 | Milan | Marco Gallo (3) | Milan (3) |
| La Liga / Sub-7 | Real Madrid | Sergio Martínez Martín (11) | Mallorca (25) |
| La Liga / Sub-9 | Atlético de Madrid | Hugo Martín Fernández (12) | Valencia (12) |
| La Liga / Sub-15 | Barcelona | Álvaro Ruiz García (6) | Barcelona / Real S… (4) |

Confirman con datos las reglas que el sistema declara: **la bota de oro es individual y
no del campeón** (la ganan jugadores de Fulham y Juventus en categorías que ganaron
Newcastle y Cagliari), **los empates se premian compartidos** (dos guantes de oro con
`/`), y **el cierre en cadena funciona**: Serie A cerró sola al terminar sus dos
categorías, y las otras cuatro ligas siguen abiertas porque les quedan categorías en
juego.

### Verificación de integridad — todo limpio

| Chequeo | Resultado |
|---|:-:|
| Equipos cuya categoría pertenece a otra liga | 0 ✅ |
| Partidos con equipos de otra categoría | 0 ✅ |
| Partidos con local == visitante | 0 ✅ |
| Marcador ≠ suma de actuaciones cargadas | 0 ✅ |
| Jugadores fuera del límite de edad de su categoría | 0 ✅ |
| `ganador_penales` cargado sin empate en el marcador | 0 ✅ |
| Jugadores sin fecha de nacimiento | 0 ✅ |
| `goles_de_penal` mayor que `goles` en una actuación | 0 ✅ |
| Partidos por default con goleadores cargados | 0 ✅ |

**Sigue sin haber un solo dato corrupto**, ya con los campos nuevos (`goles_de_penal`,
`no_se_presento`) en uso.

### Escenarios cargados

Los datos de demostración cubren a propósito todos los caminos del sistema, para que
ninguna pantalla quede sin ejercitar:

| Escenario | Cantidad |
|---|---:|
| Partidos ganados por default (3-0, sin goleadores) | 37 |
| Tandas de penales | 69 |
| — de ellas, **finales definidas desde el punto penal** | 3 |
| — el resto, empates del regular con **+1 punto** | 66 |
| Goles de penal dentro del juego | 649 |
| Goles en contra | 86 |
| Partidos reprogramados (`fecha` ≠ `fecha_original`) | 128 |
| Cambios de cancha (`sede` ≠ `sede_original`) | 71 |
| Jugadoras mujeres | 716 |
| — de ellas, usando el **año extra de tolerancia** | 398 |
| Jugadores lesionados / sancionados / de baja | 166 / 99 / 65 |

**Los tres tamaños de cuadro de liguilla quedan cargados**, que era imposible con un
cupo único:

| Equipos en la categoría | Cuadro | Ejemplo |
|---|---|---|
| 8 o más | cuartos de final | Premier League / Sub-9 (20 equipos) |
| 4 a 7 | semifinales | La Liga / Sub-15 (5 equipos) |
| 2 o 3 | final directa | Serie A / Sub-17 (3 equipos) |

### Observaciones sobre los datos

- **12 partidos sin sede**: son las semifinales que el sistema creó solo al cerrarse los
  cuartos, y que todavía esperan fecha y cancha. Es el estado correcto —el propio mensaje
  dice *"Solo falta ponerles fecha y cancha"*—, no un dato faltante.
- **Los partidos por jugarse sí tienen fecha**, así que la portada ya no muestra partidos
  sin fecha. El hallazgo #6 sigue abierto igual: la consulta no excluye los nulos ni
  filtra por liga activa, solo que hoy no hay nulos que lo delaten.
- **197 cuentas de entrenador huérfanas**, de las ligas eliminadas antes del arreglo del
  06/08. No se borran solas: ver `manage.py limpiar_entrenadores`.
- **Rendimiento medido sobre las 21 pantallas públicas** con `RequestFactory`: todas
  responden 200 y **el peor caso son 27 consultas**. La tabla de goleo, que llegó a hacer
  1 822, quedó en 8 (ver #12). Las pantallas nuevas —canchas, calendario mensual y
  vitrina— resuelven con **1 consulta** cada una, y los gráficos con 3.
- **Sesiones acumuladas** en `django_session`. Nunca se corrió `clearsessions`.

### Estado de los hallazgos al 06/08/2026

Reverificado contra el código, no contra el documento:

| # | Hallazgo | Estado |
|:-:|---|---|
| 1 | `DEBUG=True` apuntando a la base real | **abierto** — `settings.py` ya usa `default=False`, pero el `.env` local dice `DEBUG=True` y apunta a `SISTEMA-FUTBOL` |
| 2 | Credenciales reales como default en `settings.py` | **abierto** — líneas 104-106 sin cambios |
| 3 | Faltan settings de seguridad | **abierto** — `check --deploy` devuelve 5 warnings (W004, W008, W012, W016, W018) |
| 4 | `credenciales-entrenadores.csv` en disco | **abierto** — sigue ahí, 13 KB |
| 5 | Plantillas de menores sin acotar por `ligas_visibles` | **abierto** — `jugador_list` sigue con `get_object_or_404(Equipo, pk=...)` |
| 6 | Portada muestra partidos sin fecha | ✅ **resuelto 06/08** — la portada se rehizo sobre `portada.py`, que filtra `fecha__gte=ahora` y acota todo a `Liga.activa=True` |
| 7 | Rehacer rondas de liguilla | ✅ resuelto 03/08 |
| 8 | `superadmin` sin `is_superuser` bloqueado | ✅ resuelto 05/08 |
| 9 | Fuga de visibilidad entre ligas | **parcial** — `estadisticas_liga_categorias` resuelto; siguen abiertos `tabla_posiciones`, `liguilla_categoria` y `equipo_detail` |
| 10 | El bloqueo por pago no alcanza a entrenadores | **abierto** |
| 11 | El ranking cuenta los partidos de liguilla | ✅ **resuelto 06/08** — `jugados` filtra `fase=FASE_REGULAR`, igual que `tabla.py` y `porteros.py` |
| 12 | N+1 en goleo y asistencias | ✅ **resuelto 06/08** — los equipos por categoría se precalculan en una consulta: de **1 822 a 8** consultas, de 1,2 s a 0,5 s |
| 13 | Sin paginación | **abierto** |
| 15 | Faltan índices compuestos | **abierto** — ningún modelo declara `indexes` |
| 16 | Cero tests | **abierto** — sigue sin existir un solo archivo de test |
| 18 | `.pyc` versionados | **abierto** |
| 19 | `LANGUAGE_CODE`/`TIME_ZONE` duplicados | **abierto** — líneas 136-138 y 160-161 |

---

## 7. Hallazgos

### 🔴 Seguridad — atender de inmediato

#### 1. `DEBUG=True` en un entorno que apunta a la base de producción

El `.env` de la máquina de desarrollo tiene `DEBUG=True`, y esa máquina usa **la misma
base PostgreSQL que producción**. Si esa configuración llega al servidor, cualquier
error 500 muestra la página de traceback de Django con **el `SECRET_KEY`, la contraseña
de PostgreSQL y todas las variables de entorno**.

`ALLOWED_HOSTS` además incluye la IP de LAN, lo que amplía quién puede provocar ese error.

**Fix:** `DEBUG=False` en el `.env` del servidor, sin excepciones.

#### 2. Credenciales reales como valores por defecto en `settings.py`

```python
# futbol/settings.py, líneas 104-106
'NAME': config('DB_NAME', default='SISTEMA-FUTBOL'),
'USER': config('DB_USER', default='sistema_user'),
'PASSWORD': config('DB_PASSWORD', default='<la contraseña real>'),
```

`settings.py` **sí está versionado en git**. Aunque sean solo *defaults*, son las
credenciales verdaderas y quedaron en el historial del repositorio.

**Fix:** cambiar los tres a `default=''`, y **rotar la contraseña de PostgreSQL**.
Reemplazar el valor en el archivo no lo borra del historial de git.

#### 3. Faltan por completo los settings de seguridad de Django

No están definidos:

```
SESSION_COOKIE_SECURE      CSRF_COOKIE_SECURE
SECURE_SSL_REDIRECT        SECURE_HSTS_SECONDS
SECURE_CONTENT_TYPE_NOSNIFF
X_FRAME_OPTIONS            CSRF_TRUSTED_ORIGINS
SECURE_PROXY_SSL_HEADER    ← necesario porque IIS hace de proxy
```

**Fix:** ejecutar `python manage.py check --deploy` y resolver la lista que devuelve.

#### 4. `credenciales-entrenadores.csv` en la raíz del proyecto

197 contraseñas en texto plano, junto a `manage.py`, desde el 29/07. Está correctamente
ignorado en `.gitignore` (`credenciales-*.csv`), pero el archivo sigue existiendo en disco.

**Fix:** borrarlo o moverlo a un gestor de contraseñas.

#### 5. Datos de menores accesibles sin iniciar sesión

`/jugadores/equipo/<id>/` (`jugadores/views.py::jugador_list`) hace
`get_object_or_404(Equipo, pk=equipo_id)` **sin acotar por `ligas_visibles`**.

Cualquier persona sin cuenta puede ver nombre, apellido, foto, dorsal y estado de niños
de **U5 a U17**, de cualquier equipo, incluso de ligas que se desactiven. La tabla no
muestra la fecha de nacimiento (bien), pero sigue siendo información personal de menores.

Como el sistema publica un aviso de privacidad, conviene revisar este punto también en
lo legal.

**Fix:** aplicar `ligas_visibles(request.user)` en `jugador_list`, y evaluar si la
plantilla debe ser pública o requerir sesión.

---

### 🟠 Bugs concretos

#### 6. La portada muestra partidos sin fecha como "próximos partidos"

`torneos/views.py::inicio`, línea 23: ordena por `fecha` sin excluir los nulos. En
PostgreSQL los `NULL` van al final en orden ascendente, pero como solo hay **1** partido
con fecha asignada, **4 de los 5 espacios de la portada están mostrando partidos sin
fecha**. Verificado contra la base.

Tampoco filtra por liga activa.

**Fix:**
```python
Partido.objects.filter(
    estado__in=Partido.ESTADOS_POR_JUGARSE,
    fecha__isnull=False,
    fecha__gte=timezone.now(),
    categoria__liga__activa=True,
)
```

#### 7. ✅ RESUELTO 03/08/2026 — Corregir un resultado de liguilla no rehacía la ronda siguiente

> **Arreglado.** `liguilla.avanzar()` ahora compara los cruces que *deberían* existir
> contra los que existen, y rearma solo los que cambiaron. Al rearmar un cruce se limpian
> su fecha, cancha, marcador y actuaciones —eran de un partido que no se va a jugar— y se
> borran las rondas que dependían de él (`DERIVADAS`). Si se borra la final, la categoría
> se reabre y se elimina su palmarés (`palmares.reabrir`).
>
> Es **quirúrgico**: si de dos semifinales solo cambia una, la otra conserva intactos su
> fecha, su cancha y su resultado. Verificado con una simulación revertida sobre
> La Liga / Segunda División.
>
> El texto original del hallazgo queda abajo como referencia.



`liguilla.py::_crear`, línea 186, sale temprano si la fase siguiente ya existe. Eso evita
duplicados (correcto), pero si el superadmin corrige un resultado de cuartos y **cambia
quién ganó**, la semifinal ya creada se queda con el equipo equivocado, y no hay forma de
arreglarlo desde la interfaz.

Con la liguilla real por comenzar, este es el bug de mayor riesgo operativo.

**Fix:** al corregir un resultado de liguilla, detectar si cambió el ganador y, en ese
caso, borrar y regenerar las rondas posteriores (avisando al usuario que se pierden sus
fechas y resultados).

#### 8. Un `superadmin` sin la casilla `is_superuser` queda bloqueado

`permissions.py::_role_test`, línea 8:

```python
return user.is_authenticated and (user.is_superuser or user.role in roles)
```

`admin_liga_required` solo pasa `('adminliga',)`. Un usuario con `role='superadmin'` e
`is_superuser=False` **no puede entrar** a ligas, categorías ni partidos — aunque
`Usuario.es_super_admin()` devuelva `True` para él y toda la interfaz lo trate como
administrador general.

Hoy no explota porque el único superadmin tiene el flag activo, pero es una trampa
esperando a la siguiente cuenta.

**Fix:** incluir `ROLE_SUPERADMIN` en `_role_test`, o usar `user.es_super_admin()`.

#### 9. Fuga de visibilidad entre ligas en estadísticas

Estas vistas usan `get_object_or_404(...)` sin acotar por `ligas_visibles`:

- ~~`estadisticas/views.py::estadisticas_liga_categorias`~~ ✅ **RESUELTO 05/08/2026**
- `estadisticas/views.py::tabla_posiciones` (línea 27)
- `estadisticas/views.py::liguilla_categoria` (línea 132)
- `equipos/views.py::equipo_detail` (línea 160)

Un Admin Liga —o cualquier visitante— puede ver la tabla, el cuadro de liguilla y las
categorías de **otra liga** simplemente escribiendo el ID en la URL. Contradice el
principio que el propio `permissions.py` documenta: *"cada liga es un negocio aparte y
no tiene por qué ver los equipos ni las tablas de las demás"*.

#### 10. El bloqueo por falta de pago no alcanza a los entrenadores

`usuarios/views.py::_liga_bloqueada` evalúa únicamente `role == ROLE_ADMIN_LIGA`. Si una
liga deja de pagar, su administrador queda bloqueado pero **sus 30 entrenadores siguen
entrando con normalidad**. Como palanca comercial, está incompleta.

#### 11. Los partidos jugados del ranking incluyen los de liguilla

`estadisticas/views.py`, línea 67: el diccionario `jugados` no filtra
`fase=FASE_REGULAR`, a diferencia de `tabla.py` y `porteros.py`, que sí lo hacen. El
divisor queda inflado y los promedios de goles por partido salen más bajos de lo real.

---

### 🟡 Rendimiento

#### 12. N+1 en las tablas de goleo y asistencias

`estadisticas/views.py::_partidos_del_equipo` (línea 113) ejecuta un
`Equipo.objects.count()` **por cada fila del ranking**. Con la tabla completa son
cientos de consultas solo para calcular una columna de promedio.

**Fix:** precalcular un dict `{categoria_id: cantidad_equipos}` antes del bucle, igual
que ya se hace con `jugados`.

#### 13. Sin paginación en ningún listado

`usuarios_list` trae 204 filas, `equipo_list` 202, `partido_list` sin filtro de jornada
trae 225. Hoy aguanta; con dos temporadas más de datos, no.

#### 14. Consultas repetidas en el chequeo de permisos

`equipo_edit`, `equipo_detail` y `jugadores/views.py::_puede_gestionar` ejecutan
`ligas_administradas(user).values_list('id', flat=True)` dentro de un `in`, disparando
una consulta extra en cada llamada.

#### 15. Faltan índices

`Partido(categoria, fase, estado)` y `Partido(categoria, jornada)` son los filtros de
casi todas las consultas del sistema y no tienen índice compuesto.

---

### 🔵 Deuda técnica

#### 16. Cero tests — la deuda más importante

No existe un solo archivo de test en el proyecto.

Y hay lógica que los pide a gritos, toda en funciones puras y baratas de testear:

- `calendario.armar_jornadas` — round-robin con par e impar de equipos
- `liguilla.formato` / `iniciar` / `avanzar` / `cuadro` — los tres tamaños de cuadro
- `tabla.calcular` — puntos, diferencia de gol, punto extra por penales
- `actuaciones.errores` — que los goles cuadren con el marcador
- `Partido.ganador` — la resolución de empates según la fase

**Es la inversión de mayor retorno del proyecto**, y es lo único que impide tocar
`liguilla.py` con confianza para arreglar el hallazgo #7.

#### 17. 2 192 líneas de CSS inline en `templates/base.html`

El archivo tiene 2 243 líneas y es ~90 % un bloque `<style>`. Consecuencias: se
retransmite en cada página (sin caché de CSS separado), no se puede minificar, y navegar
el template es difícil.

Las razones para usar CSS plano en vez de Tailwind están bien documentadas y son válidas
(`:has()`, superponer el dorsal sobre la camiseta, la flecha propia de los `<select>`).
Pero eso justifica un `static/css/componentes.css`, no meterlo dentro del template.

> **Se empezó a desarmar (06/08/2026).** El CSS de la portada, la barra y el pie
> se escribió en `static/css/portada.css`, fuera del template. Es el primer
> pedazo que sale del bloque `<style>`, y el criterio para lo que venga: cada
> componente con su prefijo, en su archivo, cacheable aparte.
>
> **Ya costó un bug visible (06/08/2026).** En un bloque de 2 000 líneas, dos
> componentes distintos —el podio de la vitrina y el banner del campeón de la
> liguilla— terminaron declarando las mismas clases `.podio-*` a mil líneas de
> distancia, y se pisaban: el nombre del equipo salía sin centrar y la copa del
> campeón se veía más chica que la del subcampeón. Encima, uno de los dos bloques
> llevaba tiempo sin usarse y nadie lo notó. Partir el CSS por componente hace que
> este tipo de colisión salte a la vista en vez de esconderse.

#### 18. Archivos `.pyc` versionados

`futbol/__pycache__/urls.cpython-314.pyc` aparece como modificado en `git status`. El
`.gitignore` tiene `__pycache__/`, pero esos archivos ya estaban trackeados de antes.

**Fix:** `git rm -r --cached futbol/__pycache__ apps/*/__pycache__`

#### 19. Configuración duplicada en `settings.py`

`LANGUAGE_CODE` y `TIME_ZONE` están definidos dos veces (líneas 136-138 y 160-161).

#### 20. Django sirve `/static/` y `/media/` en producción

`futbol/urls.py`, líneas 35-36. Está documentado el porqué (IIS proxea todo a waitress y
no hay nginx delante), pero es lento y, sobre todo, es el camino por el que se sirven las
fotos de los jugadores **sin ningún control de acceso**.

**Fix:** configurar IIS para servir esas dos rutas directamente desde disco. Mejora el
rendimiento y permite proteger `/media/`.

---

## 8. Lo que está bien hecho

Esta sección importa tanto como la anterior: el nivel del código es alto y no conviene
que la lista de hallazgos lo tape.

- **Los comentarios son excepcionales.** No explican *qué* hace el código, explican *por
  qué* — y ese "por qué" casi siempre es una decisión de producto o una regla de fútbol.
  `liguilla.py`, `porteros.py` y `ficha.py` se leen como documentación de negocio. Es lo
  mejor del proyecto.

- **La lógica no está en las vistas.** Módulos puros, reutilizables y testeables. Por eso
  `tabla.calcular()` sirve a tres pantallas distintas sin duplicar la regla de puntos.

- **Las validaciones son reales y están en capas.** `clean_numero` te dice *quién* tiene
  ocupado el dorsal, no solo que está ocupado. El límite de edad pone `min`/`max` en el
  selector de fecha **y** revalida en el servidor **y** explica cuántos años cumple el
  jugador en la temporada. El cupo de categoría se revalida al guardar por si se llenó
  mientras el formulario estaba abierto. Los goles tienen que cuadrar con el marcador.
  Los datos impecables encontrados en la base son consecuencia directa de esto.

- **Los mensajes explican el motivo en vez de esconderlo.**
  `motivo_para_no_iniciar()` y `motivo_para_no_recibir_equipos()` devuelven texto en vez
  de un booleano, para que la pantalla diga "faltan 3 partidos por jugarse" en lugar de
  simplemente ocultar el botón. Es una decisión de UX deliberada y aplicada con
  consistencia en todo el sistema.

- **`vista_eliminar` unificada** — un solo flujo de borrado para liga, categoría, equipo
  y usuario, con transacción, lista explícita de lo que se arrastra en cascada, motivo de
  bloqueo cuando no se puede borrar, y `ProtectedError` como red de seguridad.

- **Gestión de imágenes completa** — redimensionado a 512 px al subir (una foto de
  celular pesa varios MB), señales que borran los archivos huérfanos verificando primero
  que ningún otro registro los use, y tolerancia al bloqueo de archivos de Windows.

- **Cache-busting por `mtime`** en los estáticos, resuelto en un módulo compartido
  (`estaticos.py`) para que también lo puedan usar los modelos, no solo los templates.

- **Detalles de producto bien resueltos:** el bloque "descansa esta jornada" en vez de
  "no hay partidos"; el aviso de reprogramación que sobrevive al cierre del partido; los
  últimos cinco partidos clicables; la tanda de penales dibujada como en televisión; el
  mapa que abre centrado en la última cancha marcada de esa liga.

---

## 9. Recomendaciones priorizadas

| # | Acción | Motivo | Hallazgo |
|:-:|---|---|:-:|
| 1 | `DEBUG=False` en producción + `manage.py check --deploy` | Expone SECRET_KEY y contraseña de BD | #1, #3 |
| 2 | Sacar credenciales de `settings.py` y **rotar la contraseña** | Están en el historial de git | #2 |
| 3 | Borrar `credenciales-entrenadores.csv` del disco | 197 contraseñas en texto plano | #4 |
| 4 | Acotar `jugador_list` y `equipo_detail` por `ligas_visibles` | Datos de menores accesibles sin login | #5, #9 |
| 5 | Tests de `calendario`, `liguilla`, `tabla`, `actuaciones` | Funciones puras, alto riesgo, costo bajo | #16 |
| 6 | Arreglar la portada (`fecha__gte=now`) | Bug visible al público ahora mismo | #6 |
| 7 | Resolver el rehacer de rondas de liguilla | La liguilla real está por empezar | #7 |
| 8 | Agregar `ROLE_SUPERADMIN` a `_role_test` | Trampa latente en permisos | #8 |
| 9 | Extender el bloqueo por pago a los entrenadores | Palanca comercial incompleta | #10 |
| 10 | Precalcular equipos por categoría en los rankings | N+1 de cientos de consultas | #12 |
| 11 | Actualizar el `README.md` | Describe un flujo que ya no es el real | §4 |
| 12 | Mover el CSS de `base.html` a un archivo propio | 2 192 líneas sin cachear | #17 |

---

## 13. Cierre de temporada y palmarés

### El flujo

```
Se carga el resultado de la FINAL de una categoría
        ↓
La categoría se cierra sola  (cerrada=True, inscripción cerrada)
        ↓
Se congela el PALMARÉS: campeón, 2º, 3º, bota de oro,
trofeo de asistencias, guante de oro y la tabla final
        ↓
¿Quedan categorías activas sin cerrar en esa liga?
   SÍ → la liga sigue en curso
   NO → la liga se cierra  (cerrada=True, fecha_cierre=ahora)
        ↓
La liga concluida deja de contar contra `limite_ligas`
→ el admin ya puede crear la temporada siguiente
        ↓
Se exhibe 30 días en /estadisticas/vitrina/
        ↓
Cumplido el mes, el superadmin puede eliminarla.
El PALMARÉS sobrevive al borrado.
```

### `cerrada` no es `activa`

Son dos conceptos distintos y por eso no se reutilizó el campo:

| Campo | Qué significa |
|---|---|
| `activa` | Si se muestra al público. `activa=False` la **esconde** |
| `cerrada` | Si la temporada terminó. Una liga cerrada **sigue visible** |

Cerrar una liga usando `activa=False` habría escondido justo lo que hay que mostrar.

### Los premios

| Premio | A quién | Imagen |
|---|---|---|
| Copa de oro | Campeón (ganó la final) | `copa-transparente.png` |
| Copa de plata | Subcampeón | `copa-transparente-plata.png` |
| Copa de bronce | Tercer lugar | `copa-transparente-bronce.png` |
| **Bota de oro** | Máximo goleador — **individual** | `bota-oro-goleadores.png` |
| **Trofeo de asistencias** | Máximo asistidor — **individual** | `trofeo-oro-asistidores.png` |
| **Guante de oro** | Equipo con menos goles recibidos | `guante-oro-porteros.png` |

**Los individuales no dependen del campeón.** Los gana el mejor de la categoría aunque
su equipo haya sido eliminado en cuartos. Verificado con datos reales de La Liga /
Segunda División: el trofeo de asistencias lo gana un jugador de *Racing Guerreros*,
eliminado en cuartos.

**Los empates se premian compartidos en los tres.** Desempatar por menos partidos o por
asistencias sería decidir por el reglamento de la liga, que no le corresponde al sistema.
Por eso los ganadores se guardan separados por `' / '` y no como una clave foránea.

**El podio sale del cuadro de liguilla, no de la tabla.** El campeón es el que ganó la
final, no el que terminó primero en la fase regular.

### Por qué el palmarés va congelado

Dos motivos:

1. **La tabla y los rankings se recalculan en cada consulta.** Si el superadmin corrige
   un resultado viejo, el campeón podría cambiar solo. Un palmarés es un hecho histórico.
2. **Tiene que sobrevivir al borrado de la liga.** Por eso guarda **nombres y no claves
   foráneas**: cuando se eliminen los equipos y los jugadores, la fila sigue contando
   quién ganó. `categoria` es la única FK y está en `SET_NULL`.

La tabla final va como `JSONField` porque no se filtra ni se ordena: se muestra entera o
no se muestra.

### El formato de la liguilla

| Ronda | Formato | Si empatan |
|---|---|---|
| Cuartos de final | **Ida y vuelta** | Global igualado → pasa el mejor de la tabla |
| Semifinales | **Ida y vuelta** | Global igualado → pasa el mejor de la tabla |
| Tercer lugar | **Partido único** | Pasa el mejor de la tabla |
| Final | **Partido único** | **Penales** |

**La localía se invierte:** la ida la recibe el peor sembrado y la vuelta el mejor,
que cierra la serie en su cancha. Es la ventaja que se ganó durante el torneo regular.

**Los campos en la base:** `fase` (`cuartos`/`semifinal`/`tercero`/`final`) + `orden`
(qué llave del cuadro) + **`vuelta`** (booleano). Una llave son los dos partidos que
comparten `fase` y `orden`.

**El global se calcula por equipo, no por localía.** Sumar `goles_local` de los dos
partidos mezclaría a los dos equipos, porque quien juega de local cambia entre la ida y
la vuelta. `liguilla.series()` resuelve esto y expresa el global desde el punto de vista
de cada club.

**En liguilla los penales no suman punto.** En el torneo regular ganar la tanda vale un
punto extra; en la eliminación directa solo define quién pasa. La etiqueta lo distingue:
*"+1 penales"* en el regular, *"Ganó penales"* en la liguilla.

### Cómo se nombra cada partido

`Partido.etiqueta` y `Partido.etiqueta_corta` arman el nombre desde `fase` y `vuelta`:

```
Jornada 5                              J5
Liguilla · Cuartos de final · Ida      4tos I
Liguilla · Semifinal · Vuelta          Semi V
Liguilla · Tercer lugar                3er
Liguilla · Final                       Final
```

Viven en el modelo porque las usan el calendario, la ficha, el perfil del equipo y el
formulario de resultado, y tienen que decir lo mismo en todos lados. Antes cada pantalla
mostraba `Jornada 0` para los partidos de liguilla, que no significa nada.

### Dónde aparecen los trofeos

Tabla de posiciones · Tabla de goleo · Tabla de asistencias · Porterías menos vencidas ·
Perfil del equipo · Listado de equipos · **Detalle del equipo** · **Plantilla del equipo** ·
Ficha de partido · Cuadro de liguilla · Vitrina · **Tablero del entrenador**.

**Tres tamaños**, según el peso de la pantalla:

| Tamaño | Dónde |
|---|---|
| 18 px | Tablas densas: posiciones, goleo, asistencias, porterías |
| 28 px (`tam='md'`) | Tarjetas y listas: equipos, plantilla, llaves, ficha |
| 44 px (`tam='lg'`) | Encabezados: perfil del equipo, plantilla |

**Los premios individuales también lucen en el escudo de su club.** Que en un equipo
juegue el goleador del torneo es un mérito del club, y así se ve en el listado sin abrir
la tabla de goleo. El tooltip nombra al jugador (*"Bota de oro · Nelda Gusmán Chamú"*)
para que no se confunda con un premio de equipo.

Se precargan con `palmares.trofeos_por_categoria()`, **una sola consulta** sin importar
cuántas filas tenga la tabla, y se cuelgan de cada fila en la vista. No se buscan desde
el template: las plantillas de Django no saben indexar un diccionario con una clave
variable, y hacerlo con un filtro propio sería una consulta por fila.

### El mes de exhibición

`Liga.DIAS_EN_VITRINA = 30`. Se calcula **por fecha, no con tareas programadas** — el
proyecto no tiene cron ni Celery, y no hace falta: `dias_en_vitrina` compara
`fecha_cierre + 30 días` contra hoy.

El borrado **no es automático**: el superadmin ve el contador en el listado de ligas
("Quedan 12 días en vitrina") y elimina cuando llega a cero. `liga_delete` rechaza el
borrado de una liga concluida que todavía está en exhibición.

### Corregir un resultado después del cierre

- Si se corrige **la final** y cambia el campeón → el palmarés se **recalcula** en su
  misma fila, conservando la fecha de cierre original.
- Si se corrige una **semifinal** y cambia quién llega a la final → la final vieja se
  borra, y con ella el palmarés: `palmares.reabrir()` devuelve la categoría (y la liga)
  al estado de "en juego". Dejar el palmarés sería dejarle la copa a un equipo que ya no
  jugó la final.

---

## 10. Bitácora de cambios

Registro de todo lo que se agrega, modifica o elimina en el sistema. Lo más reciente
arriba.

**Cómo anotar:** fecha · qué se tocó · en qué sección de este documento se reflejó.
Si resolvió un hallazgo, citar su número.

| Fecha | Tipo | Cambio | Secciones actualizadas |
|---|---|---|---|
| 18/08/2026 | Fix + Permisos | **El tablero del Admin de Liga mostraba los torneos de todos.** Reportado mirando la pantalla: la tarjeta *Torneos* del tablero llevaba a `/torneos/`, que es la **vitrina** y lista los 21 torneos del sistema. Un admin entraba a gestionar los suyos y se encontraba con los de los otros seis. **La vista no estaba mal, estaba mal el enlace**: el listado público debe seguir mostrando todos —es la cara pública de la sección, igual que la portada muestra las 6 ligas activas a cualquiera— y lo que faltaba era la pantalla acotada a lo propio. Nueva ruta **`/torneos/mis-torneos/`** (`mis_torneos`, `@admin_liga_required`), que es a donde apuntan ahora las dos tarjetas del tablero. **Son dos vistas y no un `if` por rol dentro de una**: es la convención que el proyecto ya sigue en equipos (`equipo_list` / `mis-equipos`) y en partidos, y mezclarlas obliga a que cada plantilla, cada texto y cada consulta pregunten por el rol — que es exactamente el defecto de fondo que se corrigió el 12/08 en `ligas_visibles`, donde una sola función respondía *sobre qué escribo* y *qué puedo mirar* a la vez. Aquí la separación ya existía en `permissions.py` (`torneos_administrados` vs `torneos_visibles`); lo único que hacía falta era una entrada para cada una. El listado se extrajo a `_listado(request, solo_propios)` y los textos —título, encabezado, descripción, mensaje de vacío— viajan como diccionario por pantalla, así que **la plantilla es una sola** y no dice "Todavía no hay torneos relámpago" en la pantalla donde lo correcto es "Todavía no tienes torneos". La de *Mis torneos* ofrece un enlace a la vitrina, para no dejar sin camino a quien sí quiere ver los demás. **Efecto secundario atendido en la misma tanda**: las tres redirecciones de flujo de administración (cuota agotada, torneo aún en exhibición, borrado consumado) mandaban al listado público, o sea que después de gestionar algo el admin caía en la vitrina; ahora vuelven a `mis-torneos`. Lo mismo el *"← Todos los torneos"* de la ficha, que pasa a *"← Mis torneos"* cuando quien mira lo administra. **La cuota se sigue mostrando en las dos** pantallas, porque es información del usuario y no del listado. **Verificado**: 44 comprobaciones —los 7 admins ven **exactamente** sus 3 torneos y ninguno ajeno, el superadmin ve los 21, el público sigue mostrando los 21 a un admin de liga, visitante y entrenador quedan fuera de `mis-torneos` pero entran al público, y la ficha de un torneo ajeno sigue sin botón de editar— más las 9 suites de torneos, palmarés, borrado y pantallas sin una sola falla | §5, §7 |
| 14/08/2026 | Modelo + Negocio | **El formato del torneo pasa a decidirse por categoría.** Hasta hoy estaba clavado en el código: toda categoría se jugaba a **una vuelta**, todo empate en jornada se definía en **penales con punto extra**, y a la liguilla entraban siempre los **8 primeros**. El usuario lo planteó al revés: *"aquí no se juega como la Liga MX"*, y dentro de una misma liga la Sub-11 y la Libre no compiten igual. Seis ajustes nuevos en `Categoria`, agrupados en dos bloques: **quién entra** (`libre`, `limite_edad`, `edad_minima` 30-80, `peso_minimo` 50-100) y **cómo se juega** (`vueltas` 1|2, `empate_define_penales`, `mini_liguilla`). **(1) Ida y vuelta**: la segunda vuelta **no se vuelve a sortear**, es la primera con la localía invertida — que es lo que "vuelta" significa y además garantiza que cada par se vea una vez en cada cancha (verificado: con 8 equipos, los 28 pares salen exactamente 2 veces y nadie es local dos veces del mismo par). 15 equipos a dos vueltas → **30 jornadas, 210 partidos**. **(2) Punto extra apagado**: `tabla.calcular` deja de sumarlo *aunque el partido tenga cargado un ganador de penales* — si la regla se apagó, ese dato es de antes y sumarlo daría una tabla que no coincide con lo que la categoría dice que vale. El formulario de resultado directamente no ofrece los campos. **(3) Restricciones**: `libre` es un campo y no "los tres límites vacíos" porque son cosas distintas — vacío es una categoría a medio configurar y `libre` es una decisión tomada; sin esa distinción el alta de jugadores dejaría pasar a cualquiera por un descuido. Se prohíbe cargar edad máxima y mínima a la vez (U13 + "de 40 para arriba" no lo cumple nadie). Nuevo campo `Jugador.peso`, **opcional**: los 3 468 jugadores ya cargados no lo tienen y exigirlo de golpe dejaría toda plantilla existente sin poder guardarse; solo es obligatorio donde hay peso mínimo. La regla de admisión se centralizó en `Categoria.rechazo_para()`, que devuelve **`(campo, mensaje)`** y no solo el texto, para que el error se cuelgue donde está el problema — un mensaje sobre el peso debajo de la fecha de nacimiento manda a mirar el campo equivocado. **(4) Mini-liguilla**: los puestos 9-12 juegan su propio cuadro (semifinal ida y vuelta → tercer lugar + final) para que no terminen la temporada sin nada; necesita 12 equipos o más, porque con menos los cuatro puestos no existen completos. **El bloqueo técnico que había que resolver primero**: `fase` es plana, así que la semifinal de la mini y la de la principal se llamaban igual — `series()` agrupa por `(fase, orden)` y las habría fundido en una sola llave sumando goles de cuatro equipos distintos, y `avanzar()` habría alimentado **una** final con ganadores de los dos cuadros, coronando campeón a un equipo que nunca jugó esa final. Nuevo campo **`Partido.cuadro`** (`principal`/`consolacion`) por el que filtran `series`, `avanzar`, `_crear` y el dibujo del bracket. **Bug detectado y prevenido en la misma tanda**: `palmares.cerrar_si_termino()` se dispara con `fase == FASE_FINAL`, así que la final de la mini habría **cerrado la categoría y congelado el palmarés con el campeón de consolación**, con la final de verdad todavía por jugarse. **(5) Congelado**: los tres ajustes de formato se deshabilitan de verdad (`disabled`, no escondidos) en cuanto la categoría tiene partidos generados — Django ignora lo que llegue por POST y conserva el valor guardado. **(6) Pantalla**: el formulario pasó de 7 a 13 campos, la mitad de ellos decisiones de competencia, y en una sola columna "Vueltas del torneo regular" quedaba con el mismo peso visual que un textarea opcional. Se agrupa en cuatro secciones con título y una línea de para qué sirve cada una; los checkbox pasan a interruptores con área táctil de 44 px y estado visible al estar prendidos. El render de un campo se extrajo a **`_campo.html`**, compartido por la pantalla completa y el modal, que hasta ahora tenían copias distintas — un checkbox se veía como fila con borde en uno y como interruptor en el otro. **Verificado**: `check` 0 issues, 34 pruebas de reglas en memoria, 22 de mini-liguilla sobre una categoría real de 15 equipos dentro de una transacción revertida (siembras 9-12 correctas, cuadros sin equipos en común, el principal intacto mientras avanza la mini, la final de la mini no cierra la categoría), y **`crear_datos_demo` regenera las 5 ligas con conteos idénticos** — 211 equipos y los mismos partidos por categoría que antes del cambio, o sea que calendario, liguilla y palmarés siguen comportándose igual donde no se tocó nada | §3, §4 |
| 12/08/2026 | Diseño | **Calendario mensual: los días vacíos salían como cajas enormes.** Detectado mirando la pantalla. Son dos cosas distintas. **(1)** El día 12 aparecía con un recuadro verde llamativo estando vacío: es el marcador de **hoy** —correcto—, pero usaba `box-shadow: var(--anillo-foco)`, y ese token había subido ese mismo día de 0.15 a 0.35 de opacidad para que el foco de teclado se viera. Marcar "hoy" **no es un indicador de foco** aunque se dibuje igual, y acoplarlos hacía que tocar uno moviera el otro: token propio `--anillo-hoy` a 0.18, que ubica sin gritar. **(2)** La altura: la grilla estira todas las celdas de una fila a la del contenido más alto, así que un día con **20 partidos** hacía la fila de ~1 200 px y dejaba a sus seis vecinos como cajas vacías gigantes. El defecto era anterior, pero el piso tipográfico de 12 px hizo cada bloque ~20% más alto y lo volvió evidente. Se muestran **los primeros tres partidos y el resto tras un "+N más"**, que es lo que hacen Google Calendar y Outlook — se descartó el scroll interno (esconde la cuenta real) y el alto natural por celda (rompe la retícula y deja de parecer un calendario). Va con **`<details>` nativo y no con JavaScript**: se despliega en el sitio, funciona con el teclado, se imprime abierto y no hace falta inventar una ruta "día 13". Verificado sobre agosto de 2026: 101 bloques renderizados —**ningún partido se pierde, sólo se pliegan**— con cuatro días agrupados (+22, +19, +17, +24) | §7 |
| 12/08/2026 | Diseño | **Sistema de diseño: de 977 literales sueltos a tokens.** El CSS no tenía ni una sola propiedad personalizada en 6 212 líneas: 977 literales de color (140 distintos, el verde de marca escrito a mano 62 veces), 26 tamaños de fuente, 17 radios y 25 sombras. Nuevo **`static/css/tokens.css`**, que se carga **antes** que los demás en `base.html` — las variables se resuelven al usarse, así que las dos hojas de componentes las leen sin depender del orden entre ellas. Resultado: **59 literales restantes de 977** y 1 381 usos de token. **(1) Contraste — el único incumplimiento duro de WCAG AA que había**: `#9ca3af` da **2.54:1** sobre blanco y se usaba **56 veces como color de texto**, casi siempre combinado con tamaños de 10–11 px. Se sustituyó por `--texto-debil` (#6b7280, **4.83:1**) en los 51 contextos de texto, dejando intactos los 14 usos como borde o fondo, que son correctos. Antes de reemplazar se comprobó que ninguno estuviera sobre fondo oscuro —donde el cambio habría **empeorado** el contraste—: la franja de marcadores usa `#4ade80`, `#e5e7eb` y `#86efac`, y los dos botones de cerrar pasan a verde claro, no oscuro. Los seis tokens de texto pasan AA (4.83 a 17.74:1). **(2) Tipografía**: había **220 declaraciones a 13 px o menos, 94 de ellas a 11 px o menos**, incluido un `font-size: 9px`. Escala de diez pasos con **piso de 12 px**; 95 reglas subieron. **(3) Colisión de clases entre archivos, defecto visual activo**: `portada.css` carga antes que `sistema.css` y comparten especificidad, así que ganaba el segundo. `.cifra-numero` estaba declarada en los dos (1.75rem vs 2.5rem) — **las cuatro cifras de la portada se pintaban 43% más grandes de lo escrito** — y `.marcador` nombraba **dos componentes distintos**: la franja tipo ESPN de la portada y la caja de resultado del calendario, que recibía un `width: 11rem` forzado, un `border-right` y un `:hover` que nunca pidió. Es el mismo bug `.podio-*` del 06/08, ahora entre archivos: partir el CSS no bastó, faltaba el prefijo por componente. Renombradas a `.franja-marcador-*` y `.portada-cifra-*`. **(4) Áreas táctiles**: ocho controles por debajo de 44 px (`.btn-accion` 32, `.pastilla-jornada` 30 — el control más pulsado del sitio en móvil). Token `--toque: 2.75rem` (WCAG 2.5.8). `.equipo-enlace` se dejó como está a propósito: es texto dentro de una celda que ya aporta el área. **(5) Foco y deshabilitado**: había 22 reglas de foco y solo 5 con `focus-visible`; ahora hay una garantía global, con ámbar sobre los fondos oscuros donde un anillo verde no se vería, y los anillos suben de 0.15–0.18 a 0.35 de opacidad. Existía **una sola** regla `:disabled` en todo el CSS. Se añadió el estado y el **bloqueo de doble envío** en `forms.js` — sin `disabled`, que sacaría el botón del POST y perdería su `name`/`value`; con clase y guarda, y liberando en `pageshow` para que volver atrás no deje el formulario muerto. **(6) Sombras**: no se aplanaron las 25 a cuatro como sugería la auditoría, porque no cumplen la misma función — hay elevación neutra, sombras teñidas de verde bajo las tarjetas de marca, sombras para fondo oscuro y anillos de foco, que ni siquiera son sombras. Quedan **11 agrupadas por lo que comunican**. **(7) Breakpoints**: `640px` y `768px` eran `40rem` y `48rem` escritos en otra unidad; `68rem` se alineó a `64rem`. Se **conservan documentadas** dos excepciones: `56rem` (una grilla de siete columnas necesita más ancho que cualquier corte genérico) y `max-width: 26rem` (teléfonos pequeños). **(8) Imágenes**: 44 pasan a `loading="lazy"` + `decoding="async"`; quedan inmediatas las seis que se ven sin bajar la página (logo, hero, escudo de liga, pie). **No se borró ninguna imagen**, por indicación expresa. **(9) Toasts**: se borraban de golpe con `.remove()`; ahora salen con transición, se pausan al pasar el ratón o al recibir el foco —un aviso de error puede llevar el nombre del campo que falló— y el `<script>` suelto y el `onclick=` salieron a **`static/js/toasts.js`**, que es requisito para poder pasar la CSP de reporte a bloqueo. **(10)** Las 3 445 líneas con la sangría heredada del viejo `<style>` de `base.html` quedaron normalizadas. **Verificado**: `check` 0 issues, las 15 pantallas públicas y los 2 archivos nuevos en 200, cero tokens sin definir, llaves balanceadas en las tres hojas. **Lo que NO se tocó**: ni una plantilla cambió de estructura, ni una vista, ni el modelo. Lo bien hecho se dejó como estaba —49/49 `<img>` con `alt`, un `<h1>` por página, las 9 tablas con `overflow-x-auto`, mobile-first real, enlace de salto y `prefers-reduced-motion` | §2, §7 |
| 12/08/2026 | Fix | **`partido_list` reventaba con visitante sin cuenta.** Regresión introducida ese mismo día al pasar los botones de gestión a decisión por fila: `ligas_administradas(user)` pregunta por `user.es_super_admin()`, que un `AnonymousUser` no tiene, y el calendario es de las pantallas con más tráfico público. Se detectó al probar las 15 pantallas **sin sesión** —la verificación anterior se había hecho autenticado como admin de liga, y por ahí el fallo no aparece—. Ahora solo se consulta cuando hay alguien que pueda administrar. Comprobado con los cuatro roles: anónimo, entrenador, admin de liga y superadmin, los cuatro en 200 | §7 |
| 12/08/2026 | Fix + Permisos | **El Admin de Liga veía menos que un visitante sin cuenta.** `ligas_visibles()` devolvía `ligas_administradas(user)` para el Admin de Liga, así que en las pantallas **públicas** solo llegaba a su propia liga. Síntoma real: entrar como admin de Liga MX a Inicio → *Torneos en juego* → una liga ajena → pulsar un equipo de la tabla daba **404 en `/equipos/873/perfil/`** (FC Schalke 04, Bundesliga), y **cerrando sesión ese mismo enlace funcionaba**. El recorrido era incoherente en tres tramos: la portada ofrece las 6 ligas activas a todo el mundo (`portada.py::_ligas_publicas`, sin mirar quién entra), `tabla_posiciones` no está acotada y deja pasar, y `equipo_perfil` sí filtra por `ligas_visibles` y corta al tercer clic. **La causa de fondo es que la función mezclaba dos preguntas** que el propio `permissions.py` documenta como separadas: *sobre qué escribo* (`ligas_administradas`) y *qué puedo mirar*. Para el admin devolvía la primera. Ahora `ligas_visibles` es **lo público más lo propio**: `Liga.activa=True` unido a las administradas, con `distinct()` porque una liga propia y activa entra por los dos lados y saldría duplicada en los desplegables de filtros. **El tablero no se toca**: usa `ligas_administradas` en sus 5 consultas, así que sigue mostrando solo la liga propia — la gestión con una función, la vitrina con la otra. **Efecto secundario atendido en la misma tanda**: `partido_list` dibujaba los botones de programar y cargar resultado con un flag global (`puede_gestionar`), que alcanzaba mientras el calendario solo mostraba ligas propias; al ver ahora partidos ajenos, esos botones habrían aparecido sobre partidos de otros y al pulsarlos habrían dado 404 —`partido_edit` y `partido_resultado` sí acotan por `ligas_administradas`—. Pasó a decidirse por fila (`partido.se_puede_gestionar`). Verificado con un admin de Liga MX: ve 97 partidos en la J1 y botones solo en los 12 de su liga; editar un partido de otra liga le sigue dando 404; las 11 pantallas públicas responden 200; los 7 admins pasan de ver 1 liga a ver las 6 sin que cambie lo que administran. **No es regresión del despliegue**: el filtro venía de `50741f6`, anterior a bajar `main` | §5 |
| 07/08/2026 | Fix | **Portada de liga: franja gris antes del pie — segundo intento, el bueno.** El primer diagnóstico (`min-height: 100%` en `main.con-portada`) se probó y **no funcionó**: se midió con muestreo de píxel en dos capturas antes/después y la franja gris (`rgb(243,244,246)`, exactamente `bg-gray-100`) medía igual en ambas. La caja del `<main>` sí llegaba bien hasta el pie — el problema real es que `background-attachment: fixed` sobre un elemento cuyo alto se calcula por `flex-grow` (un cálculo en dos pasadas) a veces no repinta el fondo hasta el borde final de esa caja. **Se movió la portada del `<main>` al `<body>`**: mismo `background-attachment:fixed/cover/center`, pero ahora en el contenedor flex en sí (no en un item cuyo tamaño depende de flex-grow), y el recorte visual entre barra y pie sigue funcionando solo porque `.cabecera` y `.pie` son opacos y la tapan por arriba y por abajo — no hace falta CSS extra para "recortarla". Cambios: `templates/base.html` (`con-portada` y `--portada` pasan de `<main>` a `<body>`) y `static/css/sistema.css` (`main.con-portada` → `body.con-portada`, se sacó el `min-height`/`html{height:100%}` que no servían). **Ojo con esto para la próxima vez**: el fix no se vio hasta reiniciar Waitress — con `DEBUG=False` Django cachea los templates compilados en memoria del proceso, así que un cambio en un `.html` no se nota en producción hasta reiniciar el servidor (los `.css`/`.py` normales sí alcanzan con `collectstatic`/no hace falta reinicio para `.css`, pero un cambio en un template `.html` sí lo pide) | §13 (nota portada) |
| 07/08/2026 | Despliegue | **`origin/futbol` (commit `50741f6`) bajado a producción (`main`).** `main` y `futbol` habían divergido de verdad (`main` tenía el fix CSRF `2263eac` que `futbol` no tenía) — se resolvió con `git merge` real, no con el `reset --mixed` habitual, verificado sin conflictos y con el fix CSRF intacto tras el merge. Las 4 migraciones nuevas (`jugadores.0006_jugador_sexo`, `partidos.0014/0015`, `torneos.0011_liga_portada`) ya estaban aplicadas en la base real porque la carpeta `Futbol en local` de este mismo servidor comparte esa base y se usó como entorno de la sesión de hoy — `migrate` confirmó "nada que aplicar". `collectstatic` y `check --deploy` sin novedades (mismos 4 warnings de seguridad ya conocidos). Backup de la base tomado antes por el usuario (`NEW-07-08-2026.sql`, formato custom de `pg_dump`, requiere `pg_restore`). Waitress no tenía proceso corriendo (nadie lo reinicia solo tras una caída, ver riesgo ya documentado) — se levantó de nuevo y se verificó `/`, `/buscar/`, `/sedes/`, `/estadisticas/vitrina/` en 200. La liga real "Liga Premier Villahermosa" ya no aparece en la base (reemplazada por "LIGA PREMIER TABASCO", vacía) — confirmado con el usuario que es intencional, reconstrucción de la liga real bajo otro nombre | §7 (riesgo Waitress sin servicio), bitácora |
| 07/08/2026 | Modelo + Diseño | **Portada por liga: cada liga se ve con su propia identidad.** Campo `portada` en `Liga` (migración `torneos.0011`) que el Admin de Liga carga al crear o editar su liga, y que se pinta de fondo en **todas las pantallas de esa liga**, para todos —también para el público—, en lugar del gris `bg-gray-100` del sistema. **El problema de fondo no era la imagen sino saber de qué liga es cada pantalla:** no existe una "liga actual". Estadísticas manda `liga`, la tabla de posiciones manda `categoria`, el perfil de equipo manda `equipo` y la ficha manda `partido` — en tres de esas cuatro no hay ninguna variable llamada `liga`. Se resolvió con el template tag **`apps/torneos/templatetags/liga_actual.py`**, que recorre esos caminos en orden. **La regla es la misma para los tres roles** —visitante, Admin de Liga y Administrador General—: lo único que decide es de qué liga es la pantalla, nunca quién la mira. Hubo una regla de último recurso *("si el que entró tiene una sola liga, usa su portada")* pensada para darle fondo al tablero, y **se quitó el mismo día**: en la práctica le pegaba la portada del admin a **todas** las pantallas —inicio, buscador, canchas, vitrina, listado de equipos— que no son de ninguna liga en particular. El tablero queda gris. **Se descartó el context processor**, que era lo primero que parecía: solo recibe el `request` y no ve lo que la vista puso en el contexto, que es justo de donde sale la liga. También se descartó agregar `liga` al contexto de las ~20 vistas: una que se olvide se queda sin fondo y nada lo avisa. **La imagen nunca se muestra limpia**: capa fija propia (`.fondo-liga`), desenfoque de 3 px y velo blanco en degradado (0.93 arriba y abajo, 0.84 al medio). Sin velo, una portada oscura deja ilegible un sistema entero armado sobre fondo claro con tarjetas blancas — y el admin no se enteraría hasta que alguien se lo dijera. El desenfoque se apaga por debajo de 48rem (cuesta caro en un celular de gama baja y la imagen ya viene muy escalada) y la capa entera se oculta al imprimir. El gris pasó al `<html>` porque un `z-index: -1` no se ve si el `<body>` tiene fondo opaco. **Tope de reducción propio**: `TOPE_PANTALLA_PX = 1920` en `imagenes.py`, porque con los 512 px del resto de las imágenes una portada a pantalla completa se vería pixelada y parecería culpa de la imagen subida. **Verificado en 14 pantallas**: aparece en estadísticas de liga, tabla, liguilla, detalle de equipo y ficha de partido; **no** aparece en la portada del sitio, el buscador, el mapa de canchas, la vitrina, el listado de ligas ni en las categorías de otra liga — las que mezclan ligas o no son de ninguna se quedan en gris a propósito, porque elegir "la primera que aparezca" sería arbitrario. Nueva carpeta `portadas-ligas/` en `MEDIA_ROOT`, al lado de `logos-ligas/`; se borró `equipos/`, que estaba vacía y ningún modelo usaba | §3, §7 |
| 07/08/2026 | Fix | **`achicar_imagen` reventaba si el archivo ya no estaba en disco.** `getattr(campo, 'file', None)` sobre un `FieldFile` cuyo archivo fue borrado lanza `FileNotFoundError`, y eso tumbaba el `save()` entero: no se podía ni corregir el nombre de una liga hasta volver a subirle la imagen. Afectaba también a escudos y fotos de jugadores, y el escenario es realista porque `MEDIA_ROOT` es configurable — si apunta a otra carpeta, todas las imágenes quedan "perdidas" a la vez. Se envolvió en un `try/except` con el mismo criterio que el `except` que ya tenía la función para archivos corruptos: un problema con el archivo no debe impedir guardar el registro. Apareció al probar la portada de liga | §7 |
| 06/08/2026 | Diseño + Negocio | **Once correcciones sobre la cara pública, pedidas mirando la pantalla.** (1) **Las tarjetas de "Partidos de hoy" quedaban desparejas**: un nombre de dos renglones —*Wolverhampton Wanderers*— empujaba la fila de chips hacia abajo solo en esa tarjeta. La tarjeta pasa a ser una columna flex con los chips anclados al fondo. (2) **Escudo en la plantilla**, que arrancaba con un texto suelto. (3) y (6) **Los filtros eran solo para administradores**: en el calendario `partido_list` los armaba dentro de un `if puede_gestionar`, y en equipos la plantilla los escondía con `puede_filtrar`. El visitante —el que más los necesita, porque entra a buscar a su equipo entre doce categorías— no tenía ninguno. Ahora son para todos, acotados por `ligas_visibles`. (4) **"Jugador del momento", rehecho**: mostraba un número y la palabra *participaciones*, que no dice si fueron goles o pases. Ahora lleva escudo, dorsal, tres cifras separadas y **su mejor partido concreto** —*"2 goles y 2 asistencias ante Wolverhampton"*— que enlaza a esa ficha. (5) **El emoji 🏆 pasa a ser la copa real**, la misma imagen de la vitrina. (8) **"Torneos en juego" sube arriba de los partidos.** (9) **Los rankings muestran 5 y no 10**: con diez, las tres columnas empujaban el resto fuera de pantalla. (10) **El buscador dejó de cambiar de tamaño**: se ensanchaba al enfocarlo y movía la barra entera justo cuando alguien iba a escribir. (11) **Seguir equipos**, abajo | §7 |
| 06/08/2026 | Diseño | **La barra pasa a dos niveles.** En una sola fila entraban siete secciones, el buscador y el bloque de sesión, todo apretado. Ahora: arriba identidad, buscador y sesión sobre el verde oscuro; abajo la navegación sobre el verde de marca, con la sección activa subrayada en amarillo y los desplegables con una línea de descripción por opción. Es fija al hacer scroll —en un calendario de un mes, volver arriba para cambiar de sección era un scroll entero— y en el celular sigue siendo una fila con menú lateral. El borde inferior transparente en cada enlace reserva el lugar del subrayado para que el texto no salte 3 px al pasar el mouse | §7 |
| 06/08/2026 | Negocio + Diseño | **Seguir equipos, guardado en el navegador.** El visitante no tiene cuenta, así que el sistema no puede saber cuál es "su" equipo. Una estrella en la tarjeta y en la página del club lo guarda en **su propio dispositivo** con `localStorage`, y la portada abre con **"Tus equipos"** y sus próximos partidos. **No se guarda nada en el servidor y no se pide ningún dato** — en un sitio con información de menores eso es una ventaja, no una limitación. El HTML de la sección **lo arma el servidor**, no el JavaScript: el navegador manda los ids a `/mis-equipos/` y recibe el fragmento ya dibujado, así el estilo, el formato de fechas y el filtro por ligas públicas quedan en un solo lugar. Los ids vienen del cliente y **no son de fiar**: se filtran a números, se topan en 20 y se consultan acotados a las ligas públicas — probado con `abc`, `1;drop`, ids inexistentes y una lista de cien. Se descartó la cuenta de aficionado: abrir registro público en un sistema con datos de menores es una decisión de negocio y legal, no de diseño. De paso, **la página del equipo suma "Próximos partidos" y "Últimos resultados"**: estaban solo dentro del perfil en modal, que hay que saber que existe para abrirlo | §4, §7 |
| 06/08/2026 | Diseño | **SEO, accesibilidad y estados de carga.** Las páginas tenían `<title>` y nada más: **sin descripción ni Open Graph**, compartir el enlace de un partido por WhatsApp mostraba una dirección pelada. Ahora cada pantalla declara su descripción, y la ficha de partido comparte el cruce, el torneo y el marcador — *"Hertha BSC vs Eintracht Frankfurt · Bundesliga · Sub-11 · Cuartos · Final 2-4"*. Se agregaron `canonical` y `theme-color`. **Accesibilidad**: enlace de salto al contenido para quien navega con teclado, foco visible en la barra, `aria-pressed` en las estrellas, `aria-expanded` en el menú del celular, `aria-haspopup` en los desplegables, áreas de toque de 44 px y respeto por `prefers-reduced-motion`. **El modal ya no se queda mudo** mientras trae la ficha: muestra un indicador y, si falla la red, un mensaje en vez de girar para siempre | §7 |
| 06/08/2026 | Fix + Diseño | **La ficha de partido salía sin diseño al abrirla por enlace.** `partido_detalle.html` era un **fragmento** —empezaba en `<div class="ficha-modal">`, sin `<html>`, sin barra ni hoja de estilos— porque siempre se había abierto dentro del modal del calendario. Las pantallas nuevas la enlazaban con un `<a href>` normal, así que el navegador mostraba el HTML crudo. Se partió en dos siguiendo la convención que el proyecto ya usa en jugadores, categorías y equipos: **`_ficha_partido.html`** es el fragmento y **`partido_detalle.html`** la página completa que lo envuelve; la vista devuelve uno u otro según `?modal=1`, que se agregó a los cinco `data-url` que la abren en modal. La página suma migas de pan, atajos al pie (tabla, las dos plantillas, cómo llegar) e incluye el modal, para que los botones internos —perfil de equipo, otra ficha— sigan funcionando. **Ahora el enlace de un partido se puede compartir.** `resultado_form.html` tenía el mismo defecto y recibió el mismo tratamiento | §7 |
| 06/08/2026 | Fix | **El desplegable de la barra no abría: ninguno de los dos.** Tailwind v4 genera `.group-hover\:block:is(:where(.group):hover *)`, y `:where()` **pesa cero**, así que ese selector vale lo mismo que una clase suelta — igual que `.nav-menu`. Empatados en especificidad gana el que va después, y `portada.css` se carga después de `tailwind.css`: mi `display: none` ganaba siempre. Al mover el estilo de la barra a mi archivo rompí ese equilibrio sin verlo. Consecuencia real: desde la computadora **no se llegaba a goleadores, asistencias, porterías ni gráficos**. Abrir y cerrar pasa a resolverse en `portada.css`, al lado del `display: none` que lo controla y sin depender de Tailwind, con `:hover` y `:focus-within` —ahora también abre con el teclado, que antes tampoco andaba—, un puente invisible para que el hueco entre botón y menú no corte el hover, y la flecha que gira al desplegarse. **Y se corrigió el método de verificación**: la prueba de humo solo miraba que la página respondiera 200, y una página responde perfecto con el menú roto. Ahora se recorren todos los enlaces de la barra y del pie y se pide cada uno: 27 enlaces, 0 rotos | §7 |
| 06/08/2026 | Fix | **Rota una convención del proyecto sin darme cuenta, y repuesta.** `.vscode/settings.json` dice, textual: *"Nada de apagar validaciones: las plantillas no llevan etiquetas de Django dentro de atributos `style`… los anchos de las barras van con clases (`.ancho-45`)"*. Las pantallas nuevas —y las del 05/08— habían vuelto al `style="width: {{ x }}%"`, que es exactamente lo que el editor marca como error de CSS. Corregidos **los 9 casos** (portada, panorama de liga y gráficos) y también los `style` estáticos que quedaban. El helper `_a_paso` estaba escondido dentro de `perfil.py`: se movió a **`apps/usuarios/barras.py`**, junto al resto de las utilidades transversales, con `a_paso()` y un `reparto()` nuevo que le da el sobrante del redondeo al tramo más grande para que una barra partida en tres sume 100 exacto. Se agregaron las clases **`.alto-N`** —no existían— para las barras verticales. Aparte: el comentario que puse en `base.html` contenía la etiqueta de estilos escrita con sus signos, y el editor la tomaba como apertura real **aunque estuviera dentro de un comentario de Django**, parseando el resto del archivo como CSS; ése era el error de la línea 10 | §7 |
| 06/08/2026 | Diseño | **Gráficos del torneo** (`/estadisticas/graficos/`): goles por jornada, equipos más ofensivos, equipos menos goleados y cómo terminan los partidos (local / empate / visitante), con filtro por categoría. Nuevo `apps/estadisticas/graficos.py`, **3 consultas**. Se agrega en una sola pasada sobre los partidos y **no con `annotate` sobre relaciones**: los goles de un equipo viven en dos columnas según juegue de local o de visitante, y unir las dos relaciones multiplica las filas — el mismo error que ya había aparecido en las vallas de la portada. **Las barras son CSS**, sin librería: meter una de cientos de KB por cuatro gráficos de barras no se paga, y las alturas se calculan en Python porque el template de Django no sabe dividir. Los porcentajes del reparto se calculan dejando el último como el resto: redondear los tres por separado daba 101 y desbordaba la barra. Solo entran equipos con 4 partidos o más —con dos, cualquiera encabeza— y solo torneo regular, igual que la tabla | §7 |
| 06/08/2026 | Fix | **El goleo pasó de 1 822 consultas a 8.** `_partidos_del_equipo` ejecutaba un `Equipo.objects.count()` por cada renglón de la tabla, solo para dividir y mostrar el promedio; ahora los equipos por categoría se precalculan en una consulta, como ya se hacía con los partidos jugados (**resuelve #12**). De paso, `jugados` pasa a filtrar `fase=FASE_REGULAR` igual que `tabla.py` y `porteros.py`: los partidos de liguilla inflaban el divisor y todos los promedios de gol salían más bajos de lo real (**resuelve #11**). La tabla completa bajó de 1,2 s a 0,5 s | §7 · **resuelve #11 y #12** |
| 06/08/2026 | Diseño | **Tres pantallas públicas nuevas: buscador, canchas y calendario mensual.** (1) **Buscador** (`/buscar/`), una sola caja que encuentra jugadores, equipos, torneos y canchas a la vez — quien busca no sabe en qué tabla está lo que quiere. Insensible a acentos por el `unaccent` que ya usaba `filtros.buscar`, así que *garcía* y *garcia* dan lo mismo. Acotado por `ligas_visibles` y resuelto en 4 consultas. **No busca árbitros**: no hay modelo ni campo, y ofrecer un filtro que nunca devuelve nada es peor que no tenerlo. (2) **Canchas** (`/sedes/`): las 87 sedes con coordenadas en un mapa Leaflet, 1 consulta. El módulo de mapas estaba construido desde julio para elegir la cancha de un partido, pero **no existía ninguna pantalla que las mostrara juntas**: quien viene a ver dónde juega su hijo no tenía a dónde ir. Los datos de cada pin se leen del listado que ya está en la página, así que con el JS apagado la lista sigue sirviendo con su enlace a Google Maps. Leaflet se carga solo en esa pantalla. (3) **Calendario mensual** (`/partidos/calendario/`): responde la pregunta que hace quien no administra nada —*qué se juega este sábado*— mezclando todas las categorías, mientras que el listado por jornadas sigue sirviendo para seguir una sola. Grilla de siete columnas en escritorio; en el celular los días vacíos se ocultan y queda una lista. El mes llega por la URL y **no se confía en él**: un mes 13 o un año de cinco cifras caen al mes actual en vez de reventar. Las tres quedaron enlazadas en la barra y en el pie | §7 |
| 06/08/2026 | Diseño + Negocio | **La cara pública del sitio: portada, barra y pie.** El sistema estaba armado para quien administra; quien entra sin cuenta —los padres, que son la mayoría del tráfico— encontraba una portada con tres listas sueltas y una barra llena de pantallas de gestión. Ahora: **franja de marcadores** arriba de todo con lo que se juega hoy (el elemento que hace que un sitio se lea como sitio deportivo; se tomó de ESPN, que el cliente puso de referencia), **hero** con el partido destacado y cuenta regresiva, **cuatro cifras** vivas, **partidos de hoy** con hora, cancha y categoría, **jugador del momento**, **últimos resultados**, los **tres rankings** (goleo, asistencias, vallas), **torneos en juego** con barra de avance y **últimos campeones**. Todo en `apps/torneos/portada.py`, **31 consultas fijas**. El partido destacado no lo marca nadie: es el cruce de los dos equipos mejor ubicados entre los que se vienen. **La barra se partió en dos**: arriba solo lo público (Inicio · Partidos · Tablas · Equipos · Palmarés · Información) y la gestión —Categorías, Jugadores, Roles— se fue al tablero, que es donde el admin y el entrenador ya la tenían con contexto. **El pie de página existía como plantilla y nadie lo incluía**: el sitio se venía mostrando sin pie desde siempre; ahora son cuatro columnas con navegación, reglamento, aviso de privacidad y la nota sobre datos de menores. **Nada se inventó**: se descartaron noticias, tarjetas, Fair Play, árbitros, marcadores en vivo, clima, comentarios e inscripción en línea porque no hay datos que los sostengan | §7 (#6, #17) |
| 06/08/2026 | Diseño | **Escudos generados para los 211 equipos, que no tienen ninguno cargado.** `Equipo.escudo_url` devolvía la misma imagen gris para todos: el calendario y las tablas quedaban llenos de manchas idénticas. Nuevo `apps/usuarios/monograma.py`: las iniciales del club sobre un color propio, como **SVG en una `data:` URI**. Entra donde ya había un `<img src>`, así que **las trece pantallas que muestran un escudo no se tocaron**; escala sin pixelarse de los 28 px de la llave a los 80 px del detalle; y no hay archivos que guardar ni borrar. El color sale de un `md5` del nombre y no de `hash()`, que cambia en cada arranque de Python: el mismo club tiene siempre el mismo color. Veinte colores y no doce por el problema del palomar — una categoría llega a 20 equipos. `Liga.iniciales` pasa a usar el mismo criterio, para que una liga y un club no se abrevien con reglas distintas | §7 |
| 06/08/2026 | Diseño | **La vitrina, rediseñada: de tres copas flotando a una premiación.** Arreglada la colisión de clases, la pantalla quedaba correcta pero plana — la información estaba bien y no se veía como nada. Cambios: (1) **pedestales numerados** bajo cada copa, con altura y color de metal propios (oro 5rem, plata 3.5rem, bronce 2.5rem); es lo que convierte tres imágenes sueltas en un podio, porque la jerarquía se lee por altura antes que por texto; (2) un **escenario** con la luz cayendo desde arriba al centro (degradado radial) y una línea de piso donde los tres pedestales apoyan; (3) **resplandor dorado** solo en la copa del campeón, que lo distingue sin agrandar tipografías; (4) los **premios pasan de icono suelto a tarjeta**, en rejilla que se acomoda sola, cada una con la franja de su color, la **cifra como dato principal** y los ganadores separados —importa cuando un premio tiene tres empatados y el de al lado uno solo—; (5) franja de medalla arriba de cada temporada, fecha de cierre como sello ámbar y *"Ver la tabla final"* como pastilla en vez de enlace suelto. Verificado sobre los 8 palmarés: 23 pedestales, y el de 2 lugares (Serie A / Sub-17) sale con 1 y 2, sin bronce | §7 (#17) |
| 06/08/2026 | Fix + Diseño | **El podio de la vitrina se veía chueco: dos componentes compartían el nombre de las clases.** La vitrina y el banner del campeón del cuadro de liguilla usaban los dos `.podio`, `.podio-copa` y `.podio-equipo`, y el CSS de uno se colaba en el otro. Consecuencias, todas visibles en pantalla: **el nombre del equipo salía pegado a la izquierda** (la liguilla convertía `.podio-equipo` en un flex con `justify-content: flex-start`), **la copa del campeón quedaba más chica que las de plata y bronce** —`.podio-primero .podio-copa` le ganaba **por especificidad**, dos clases contra una, a la altura que ponía la liguilla— los nombres quedaban a distinta altura porque el `align-items` de la liguilla pisaba al de la vitrina, y de fondo aparecía el recuadro verde con degradado del banner. El podio de la vitrina pasa a `vitrina-podio-*`: columnas del mismo ancho apoyadas en una línea de piso común, copa del campeón por encima de las otras dos, nombre centrado y con `overflow-wrap` para los nombres largos, y un corte adaptativo a 40rem. Al revisarlo apareció que **el bloque `.podio-*` de la liguilla era CSS muerto**: ese banner había pasado a `bracket-campeon-*` y nadie lo usaba desde entonces — 50 líneas eliminadas. Verificado contra los 8 palmarés cargados, incluido el de 2 lugares (Serie A / Sub-17, que no tiene tercer puesto porque con 3 equipos la liguilla es solo la final) | §7 (#17) |
| 06/08/2026 | Datos | **Las cinco ligas de demostración, rehechas con datos coherentes.** Nuevo comando `manage.py crear_datos_demo` (con `--resumen` para ver qué haría y `--borrar` para deshacer). Antes eran 2 categorías idénticas por liga llamadas *Primera/Segunda División* —que no es una categoría de edad— con equipos de nombre combinatorio (*Independiente* + animal) y una Serie A Primera **U7 con 255 jugadores**. Ahora: **20 categorías** con la nomenclatura real del formativo (Sub-7 a Sub-17), **clubes reales** de cada liga y **87 estadios con coordenadas verificadas** contra Wikipedia/latitude.to, y nombres de persona verosímiles del país de cada liga. **No se usan identidades de menores reales**: son datos de prueba en una base de producción que publica su propio aviso de privacidad. **Cupos de 3 a 20 equipos** (quince tamaños, siete impares) y planteles de 13 a 20: con un cupo único, dos tercios de `liguilla.py` no se ejecutaban nunca — ahora quedan cargados los tres cuadros (cuartos, semifinales y final directa). El comando **no fabrica filas a mano**: el calendario lo arma `calendario.armar_jornadas`, la liguilla la arma y la avanza `liguilla.iniciar`/`avanzar` y el palmarés lo graba `palmares.cerrar_si_termino`, así que si alguna de esas reglas se rompe el comando falla. Verificado: 0 fallas en las nueve comprobaciones de integridad y 200 en las 16 pantallas principales | §6 |
| 06/08/2026 | Negocio + Permisos | **Al eliminar una liga se van sus entrenadores.** Antes quedaban vivos y sin equipos: así se juntaron 197 cuentas fantasma. Nueva `eliminar.entrenadores_sin_equipo_tras_borrar(equipos)`, que decide **por lo que le queda al entrenador y no por lo que se va**: quien además dirige en otra liga se conserva —y borrarlo habría reventado igual, porque `Equipo.entrenador` es PROTECT— y quien fue dado de alta y todavía no tiene equipo no se toca. La pantalla de confirmación ahora lista *"N cuenta(s) de entrenador"* junto con lo demás que se arrastra. **El Administrador de Liga no se borra**: es la cuenta del cliente, tiene su propia cuota y puede crear otra liga. Para las 197 que ya estaban sueltas: `manage.py limpiar_entrenadores` (lista sin borrar; borra solo con `--confirmar`) | §4 |
| 06/08/2026 | Negocio + Modelo + Diseño | **Las mujeres entran con un año más que la categoría.** En U17 juega una jugadora de 18, en U15 una de 16; un solo año, no dos. Campo `sexo` en `Jugador` (migración `jugadores.0006`) y constante `Categoria.ANIOS_EXTRA_FEMENINO = 1` — va como constante y no como campo configurable por el mismo motivo que `MARCADOR_DEFAULT`: es reglamento, no preferencia de liga. `edad_maxima_para(sexo)`, `nacimiento_minimo_para(sexo)` y `acepta(fecha, sexo)` reemplazan a las versiones de un solo límite, así que **la regla sigue escrita una sola vez** y todas las pantallas la heredan. El campo de sexo va **arriba** de la fecha de nacimiento porque la condiciona, y `sexo-edad.js` corre el tope del selector al cambiarlo: los dos topes viajan en `data-min-masculino` / `data-min-femenino` calculados por el servidor, el JS solo elige cuál aplica. El `clean` revalida igual, porque un POST armado a mano ignora cualquier tope de la página. **El error nombra los dos límites** y, cuando la fecha entraría marcando Femenino, lo dice — sin eso el mensaje hablaba de la fecha y el problema estaba en el campo de al lado, tanto al cargar una jugadora como al corregirle el sexo a una ya cargada. Se muestra en la plantilla (columna con pastilla y el límite en el tooltip), en el encabezado del equipo, en la tarjeta de categoría —que anunciaba un solo límite y contradecía a la validación— y en el alta de categoría. **Backfill:** los 2 832 jugadores existentes quedaron en masculino, que es el límite estricto; se revisó antes que la liga real tuviera 12 jugadores y el resto fueran ligas de prueba. Verificado: 0 jugadores fuera de su límite con la regla nueva. De paso, `_radios.html` pasó de `grid-cols-3` a flex: con 2 opciones dejaba una celda vacía que se leía como un campo a medio cargar | §3, §4 |
| 06/08/2026 | Documentación | **Reverificación completa** del código y de la base (solo lectura). Se actualizó el inventario de §6 con los números de hoy (241 partidos, 776 actuaciones, 2 palmarés, 2 superadmin), se agregaron los palmarés grabados y la tabla de **estado de cada hallazgo**, comprobada contra el código y no contra este documento. Sin cambios de negocio. Hallazgos nuevos: 14 partidos finalizados con goles y sin actuaciones (carga por simulación, no por pantalla) y ninguna liga con `fecha_pago`, así que el bloqueo por cobranza nunca se ejercitó | §6 |
| 05/08/2026 | Diseño | **Listado de ligas con datos.** Cada fila decía solo *"2 categoría(s)"* y todas se veían iguales. Ahora es una rejilla de tarjetas con el **estado de la liga**, un **anillo de avance del calendario** (SVG inline, el recorte del trazo se calcula en `resumen._anillo` porque el template no puede multiplicar y meter JS por un número fijo sería pagarlo caro), y cuatro cifras: equipos/cupo, jugadores, partidos jugados y goles con promedio. Al pie, **los campeones** si la temporada terminó, o **qué falta hacer** si no arrancó. `resumen.panorama()` resuelve **las 7 ligas en 8 consultas fijas**: agrupa por liga en una pasada en vez de llamar a `panel()` en un bucle, que habría pasado de cien | §7 |
| 05/08/2026 | Diseño + Permisos | **Panorama de la liga en Estadísticas.** La pantalla era una lista de nombres de categorías que no decía nada. Ahora abre con cuatro cifras (equipos/cupo, jugadores, partidos jugados con barra de avance, goles y promedio) y una tarjeta por categoría con **líder, goleador, estado del torneo y progreso por jornada**. Nuevo módulo `apps/estadisticas/resumen.py` (`panel()` y `tarjetas()`): el líder sale de `tabla.calcular()` y no de un `annotate` propio, para no reescribir la regla de los puntos. Los vacíos dicen **qué falta hacer** ("Cierra la inscripción para poder generar el calendario") en vez de "sin datos". Cuesta 15 consultas en la liga más grande. De paso, `estadisticas_liga_categorias` pasa a acotarse por `ligas_visibles` — **resuelve parcialmente el hallazgo #9**: antes se llegaba a cualquier liga escribiendo su id en la URL | §7 · **resuelve parte de #9** |
| 05/08/2026 | Permisos + Modelo + Diseño | **Alta de un Administrador General.** Cinco arreglos: (1) `Usuario.save()` sincroniza el rol con los flags de Django — un Administrador General queda con `is_superuser`/`is_staff` en `True` por cualquier vía (pantalla, admin, shell); (2) `_role_test` pasa a preguntar por `es_super_admin()` en vez de `is_superuser` — **resuelve el hallazgo #8**: un `role='superadmin'` sin el flag quedaba bloqueado en ligas, categorías y partidos; (3) `ligas_visibles` usa el mismo criterio, igualándose a `ligas_administradas`; (4) el campo **`limite_ligas` desaparece** salvo para el Administrador de Liga (`static/js/roles.js` lo oculta y `CuotaSegunRolMixin.clean` lo descarta también en el servidor, porque esconder un campo no impide mandarlo por POST); (5) `usuario_create` graba `creado_por`. Verificado en la base: 0 cuentas quedaron en el estado roto | §4, §5 · **resuelve #8** |
| 05/08/2026 | Diseño | **Logo de la liga en la vitrina.** La tarjeta de cada temporada concluida encabeza con el logo (o las iniciales si no tiene). Sale de `registro.categoria.liga`, que ya venía en el `select_related`, y solo mientras la liga exista: el palmarés guarda nombres y no claves foráneas justamente para sobrevivir a su borrado, así que el nombre se sigue tomando del registro congelado | §13 |
| 05/08/2026 | Diseño | La fila de goles pasó de `grid` a `flex`: al sumarle el campo "de penal" quedó con un control más que la de asistencias y la **✕ de quitar se caía al renglón de abajo**. Ahora la ✕ va siempre pegada a la derecha (`margin-left:auto`) en las dos secciones. Además el tope de penales se muestra al lado del campo (*"de 3"*) y en su tooltip: antes recortaba el número en silencio y parecía un límite del partido, cuando **el límite es por goleador** | §13 |
| 05/08/2026 | Fix + Diseño | **El desplegable "¿Alguno no se presentó?" trababa la página.** Dos causas: `default.js` creaba y borraba el nodo del aviso, lo que despertaba al observador del DOM en cada cambio; y `default.js` y `penales.js` se peleaban por el mismo `hidden` (con el marcador oculto en 0-0, penales.js lo leía como empate y volvía a mostrar la tanda). Se resolvió sacando el aviso a la plantilla —el JS ya no muta la lista de nodos— y coordinando los dos scripts con `window.hayEquipoAusente()` / `window.revisarPenales()`. Además el desplegable pasa a ocupar la fila completa: su texto de ayuda empujaba la grilla y dejaba los dos marcadores en renglones distintos. Quitado el icono ⚠ de la pastilla "Por default" | §13 |
| 05/08/2026 | Negocio + Modelo + Diseño | **Partido ganado por default.** Campo `no_se_presento` en `Partido` (migración `partidos.0015`) que guarda *qué* equipo faltó, no un sí/no: con el equipo se sabe también quién ganó y la ficha puede nombrarlo. Constante `MARCADOR_DEFAULT = 3`, fija para todas las ligas. El formulario de resultado pregunta primero si alguno no se presentó y, al elegirlo, **esconde el marcador y las secciones de goleadores** — no hay nada que cargar — y muestra quién gana. El 3-0 lo pone el servidor e ignora cualquier marcador que venga. Aviso ámbar en la ficha (*"Ganó por default · X no se presentó"*) y pastilla "Por default" en la tarjeta del calendario. **`tabla.py` y `porteros.py` no se tocaron**: es un 3-0 real, así que cuenta normal en la tabla y como valla invicta para el que sí llegó. El ausente no recibe sanción extra | §3, §4 |
| 05/08/2026 | Negocio + Modelo + Diseño | **Goles de penal en la ficha del partido.** Campo `goles_de_penal` en `Actuacion` (migración `partidos.0014`), campo numérico por fila en el formulario de resultado, y etiqueta *"de penal"* en la crónica. Va **dentro** de `goles`: no cambia el marcador, la tabla de goleo ni la bota de oro. Se decidió **no** registrar el minuto del gol (no se consulta) ni distinguir penales en la tabla de goleo. Validaciones nuevas: penales ≤ goles de la fila, un gol en contra no puede ser de penal, y asistencias ≤ goles − penales | §3, §4 |
| 03/08/2026 | Diseño | Trofeos en la plantilla del equipo; escala de tamaños (18/28/44 px); premios de la vitrina centrados y adaptables; contraste corregido en los botones Ida/Vuelta; bloque de felicitación alineado | §13 |
| 03/08/2026 | Negocio | Los premios individuales (bota de oro, trofeo de asistencias) también se muestran **en el escudo del club** del premiado, con su nombre en el tooltip | §13 |
| 03/08/2026 | Diseño | **Felicitación al entrenador** en su tablero cuando su equipo sube al podio, con los trofeos del club y los individuales de sus jugadores | §13 |
| 03/08/2026 | Negocio + Modelo | **La liguilla pasa a ida y vuelta** en cuartos y semifinales; final y tercer lugar a partido único. Campo `vuelta` en `Partido` (migración `partidos.0013`), concepto de *serie* en `liguilla.py`, global de los dos partidos, y localía invertida (la vuelta la recibe el mejor sembrado) | §4, §13 |
| 03/08/2026 | Fix | En liguilla los penales ya no dicen "+1 punto": ahí no suman, solo definen quién pasa | §13 |
| 03/08/2026 | Fix | Los "últimos 5 partidos" se ordenaban por jornada, y la liguilla (jornada 0) quedaba **antes** que el torneo regular: un equipo que ya jugó la eliminación mostraba sus últimas 5 fechas del regular. Ahora se ordena por fecha | §13 |
| 03/08/2026 | Diseño | Nueva propiedad `Partido.etiqueta` / `etiqueta_corta`: el calendario, la ficha, el perfil y el formulario dicen `Liguilla · Semifinal · Ida` en vez de `Jornada 0` | §13 |
| 03/08/2026 | Fix | **Resuelto el hallazgo #7**: corregir un resultado de liguilla que cambia el ganador ahora rehace los cruces afectados de la ronda siguiente y borra las que dependían de ellos. Es quirúrgico: los cruces que no cambian conservan fecha, cancha y resultado | §13 · **resuelve #7** |
| 03/08/2026 | Negocio + Modelo | **Cierre de temporada y palmarés**: al cargar el resultado de la final la categoría se cierra sola y se congela el palmarés (campeón, subcampeón, 3º, bota de oro, trofeo de asistencias, guante de oro, tabla final). La liga cierra cuando cierran todas sus categorías. Campos `cerrada`/`fecha_cierre` en Liga y Categoría, modelo `Palmares`, migración `torneos.0010` | §3, §4, §13 |
| 03/08/2026 | Negocio | Las ligas concluidas **dejan de contar** contra `limite_ligas`: el admin puede arrancar la temporada siguiente sin esperar | §4 |
| 03/08/2026 | Diseño | Las 5 imágenes de premios restantes (plata, bronce, bota, trofeo, guante) eran JPEG o PNG sin canal alfa; dos pesaban 1.4–1.8 MB. Convertidas a PNG con transparencia real | §11 |
| 03/08/2026 | Datos | Reajuste del calendario de **La Liga / Segunda División**: el torneo regular se corrió 14 días atrás para dar lugar a la fase final. Liguilla del 24/07 al 03/08, con la final hoy 11:00 sin resultado | — |
| 03/08/2026 | Diseño | **Perfil de equipo en modal**: al pulsar cualquier escudo o nombre de equipo se abre su perfil (calendario, posición, racha, radar de 5 ejes y figuras). Nuevo `apps/equipos/perfil.py`, vista `equipo_perfil` y plantilla `equipos/_perfil_modal.html` | §12 (nota del perfil) · bitácora |
| 03/08/2026 | Diseño | `static/img/copa-transparente.png` era un **JPEG renombrado a `.png`**, por eso salía con fondo blanco en el cuadro de liguilla. Se le quitó el fondo, se recortó el margen vacío y se guardó como PNG real con canal alfa | §11 (nota sobre imágenes) |
| 03/08/2026 | Documentación | Análisis inicial completo del sistema y creación de este archivo | Todas |

### Nota técnica — imágenes con transparencia

**Renombrar un `.jpg` a `.png` no le agrega transparencia.** JPEG no tiene canal alfa;
el formato directamente no lo soporta. El navegador lee el contenido real del archivo,
no su extensión, y muestra el fondo que la imagen traiga.

Para que una imagen tenga fondo transparente en este proyecto tiene que cumplir:

| Requisito | Cómo verificarlo |
|---|---|
| Formato real PNG (o WebP) | `Image.open(ruta).format` debe decir `PNG` |
| Modo `RGBA`, no `RGB` | `Image.open(ruta).mode` |
| Canal alfa con ceros | `im.getchannel('A').getextrema()` debe dar `(0, 255)` |

Comando de verificación rápida:

```powershell
python -c "from PIL import Image; im=Image.open('static/img/ARCHIVO.png'); print(im.format, im.mode, im.getchannel('A').getextrema() if im.mode=='RGBA' else 'SIN CANAL ALFA')"
```

Dos cuidados al procesar estas imágenes:

- **Recortar el margen vacío** con `im.getchannel('A').getbbox()`, no con `im.getbbox()`.
  Un píxel invisible conserva su color guardado, así que el bbox de la imagen completa
  devuelve siempre el tamaño original.
- **Reescalar en alfa premultiplicado**: `im.convert('RGBa').resize(...).convert('RGBA')`.
  Sin esto, el color de los píxeles invisibles se mezcla al interpolar y deja un halo
  claro en el contorno, muy visible sobre el fondo verde oscuro del cuadro de liguilla.

> Ojo: `apps/usuarios/imagenes.py::achicar_imagen` **sí** preserva la transparencia de lo
> que suben los usuarios (detecta `RGBA`/`LA` y guarda PNG en ese caso; solo convierte a
> JPEG lo que es opaco). Esta nota aplica a los archivos estáticos de `static/img/`, que
> no pasan por esa función.

<!--
Plantilla para las próximas entradas:

| DD/MM/AAAA | Negocio \| Flujo \| Diseño \| Modelo \| Permisos \| Fix | Descripción breve de qué se agregó/modificó/eliminó | §N, §M · resuelve #X |

Tipos:
  Negocio   → una regla de negocio nueva, cambiada o eliminada
  Flujo     → cambia el orden o los pasos de un proceso
  Diseño    → cambia una pantalla, un componente o la navegación
  Modelo    → cambia la estructura de datos (campos, tablas, relaciones)
  Permisos  → cambia quién puede ver o hacer qué
  Fix       → corrige un hallazgo de la sección 7
-->

### Nota de diseño — el perfil de equipo y sus métricas

**Qué es.** Un modal que se abre al pulsar el escudo o el nombre de un equipo en
cualquier pantalla. Muestra: calendario completo, posición en la tabla, racha,
distribución de ganados/empatados/perdidos, un radar de 5 ejes y el podio de
goleadores y asistidores.

**Dónde es pulsable un equipo:**

| Pantalla | Qué abre el perfil |
|---|---|
| Calendario de partidos | Escudo y nombre de cada equipo de la tarjeta |
| Ficha de partido | Escudo y nombre de cada lado |
| Tabla de posiciones | Nombre del equipo |
| Tabla de goleo y de asistencias | Columna Equipo |
| Porterías menos vencidas | Escudo y nombre |

Pendientes a propósito: el **cuadro de liguilla** (las llaves son muy compactas y
envolver el escudo rompería el layout de flex) y el **listado de equipos** (sus
tarjetas ya llevan a la página de detalle, que es una navegación deliberada).

**Regla de las métricas: nada inventado.** El sistema no captura posesión, tiros,
tarjetas, faltas, córners, minutos jugados ni alineaciones. Un radar al estilo de
los videojuegos ("Ataque / Físico / Regate / Velocidad") sería inventado, porque
esos ejes no tienen dato detrás.

Los 5 ejes que se usan salen todos de marcadores y actuaciones:

| Eje | Cómo se calcula |
|---|---|
| Ataque | Goles a favor ÷ partidos jugados |
| Defensa | Goles recibidos ÷ partidos jugados (invertido) |
| Efectividad | Puntos ÷ puntos posibles (PJ × 3) |
| Solidez | Partidos sin recibir goles ÷ partidos jugados |
| Juego colectivo | Asistencias ÷ goles del equipo |

**Se normalizan contra la propia categoría, no contra un número elegido a dedo.**
Un 80 en Ataque significa *"llega al 80% del mejor ataque de su categoría"* — una
afirmación que la base puede respaldar. En los ejes donde lo bueno es el número
más chico (goles recibidos) se invierte la razón: el que menos recibe llega a 100.

**Dos guardas contra mostrar ruido como si fuera información:**

- El radar **no se dibuja con menos de 3 partidos jugados** (`MINIMO_PARA_RADAR`).
  Con uno o dos, un 4-0 de arranque dejaba al equipo con el mejor ataque de la
  categoría y el pentágono lo presentaba como una verdad.
- Los equipos que **no jugaron quedan fuera de la normalización**: su cero no es
  un mérito ni un demérito, y arruinaba la escala de todos los demás.

**Rendimiento.** El perfil resuelve en ~14 consultas y no crece con el tamaño de
la categoría: para normalizar se apoya en `tabla.calcular` y `porteros.calcular`,
que ya resuelven toda la categoría con una cantidad fija de consultas, en vez de
recorrer equipo por equipo.

**Estado vacío.** De los 202 equipos cargados, solo los de 3 categorías tienen
partidos jugados; el resto abre un perfil casi vacío. Por eso el vacío se explica
una sola vez arriba ("Todavía no jugó partidos") en lugar de repetir "sin datos"
en cinco secciones.

**Permisos.** Acotado por `ligas_visibles`, igual que la ficha de partido. A
diferencia de `equipo_detail`, al entrenador **no** se lo limita a su propio
equipo: el perfil se abre casi siempre pulsando el escudo de un rival, y no
muestra nada que la ficha de partido no muestre ya.

---

## Diagnóstico general

Es un proyecto **bien construido**, con criterio de diseño real y por encima de lo típico
en un sistema de este tamaño. La lógica de negocio es sólida, está bien separada, bien
documentada y bien validada — y la base de datos, sin un solo registro inconsistente, lo
demuestra.

Los problemas serios **no están en la lógica**. Están en dos lugares:

1. **La configuración de despliegue** (hallazgos #1 a #4): `DEBUG=True`, credenciales en
   el repositorio, settings de seguridad ausentes.
2. **La consistencia del alcance de visibilidad** (hallazgos #5 y #9): algunas vistas
   aplican el principio de aislamiento por liga y otras se lo saltaron.

Y por encima de todo, la **ausencia total de tests** es lo único que impide tocar la
liguilla con confianza justo antes de que arranque la de verdad.
