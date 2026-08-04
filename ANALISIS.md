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
  │
  ├─ Categoria      [unique: liga + nombre]
  │     ├─ limite_edad  U5 … U17     (se cuenta por año de nacimiento)
  │     ├─ cupo_equipos
  │     └─ inscripcion_abierta
  │
  ├─ Sede           [unique: liga + nombre]
  │     └─ latitud / longitud  (9 dígitos, 6 decimales → precisión < 1 m)
  │
  └─ Equipo         [unique: nombre + liga + categoria]
        ├─ entrenador → Usuario  [PROTECT]
        ├─ formacion
        └─ Jugador               [CASCADE]
              └─ [unique parcial: equipo + numero, si numero no es NULL]

Partido
  ├─ categoria, equipo_local, equipo_visitante
  ├─ jornada, fase (''|cuartos|semifinal|tercero|final), orden
  ├─ siembra_local / siembra_visitante     (puesto en la tabla, viaja entre rondas)
  ├─ fecha + fecha_original                (para detectar reprogramación)
  ├─ sede + sede_original                  (para detectar cambio de cancha)
  ├─ goles_local / goles_visitante
  ├─ ganador_penales + penales_local / penales_visitante
  └─ estado: programado | reprogramado | finalizado | cancelado
        │
        └─ Actuacion   [unique: partido + jugador]
              └─ goles, goles_en_contra, asistencias
```

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
| Una liga concluida no cuenta contra `limite_ligas` | `usuarios/views.py::liga_create` |
| Una liga concluida no se puede borrar antes de 30 días | `usuarios/views.py::liga_delete` |
| Corregir la final recalcula el palmarés; corregir una semi lo elimina | `palmares.cerrar` / `palmares.reabrir` |
| Corregir un resultado que cambia el ganador rehace los cruces afectados | `liguilla.avanzar` |
| No se generan partidos con la inscripción abierta | `torneos/views.py::categoria_generar_partidos` |
| Mínimo 2 equipos para generar partidos | idem |
| Cantidad impar de equipos → uno descansa por jornada | `calendario.armar_jornadas` |
| No se inicia liguilla con partidos pendientes | `liguilla.motivo_para_no_iniciar` |
| Tamaño del cuadro según equipos: ≥8 cuartos, ≥4 semis, ≥2 final | `liguilla.formato` |
| Empate en cuartos/semis → pasa el mejor de la tabla, sin penales | `Partido.ganador` |
| Empate en la final → obligatorio cargar la tanda de penales | `ResultadoForm.clean` |
| Los goles cargados deben cuadrar con el marcador | `actuaciones.errores` |
| No hay más asistencias que goles | idem |
| Gol en contra suma al marcador del rival, no a la tabla de goleo | `Partido._asignados` |
| La liguilla no cuenta para la tabla ni para porterías | `tabla.calcular`, `porteros.calcular` |
| Un jugador no entra si supera el límite de edad de la categoría | `JugadorForm.clean` |
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
- **`ligas_visibles(user)`** → qué puede **ver** (el público solo ve ligas activas)

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

Inventario de solo lectura ejecutado el 03/08/2026.

### Volumen

| Tabla | Registros |
|---|---:|
| Usuario | 204 |
| Liga | 7 |
| Categoria | 13 |
| Sede | 2 |
| Equipo | 202 |
| Jugador | 2 832 |
| Partido | 225 |
| Actuacion | 746 |

**Usuarios por rol:** 1 superadmin · 6 admin liga · 197 entrenadores

**Partidos por estado:** 178 finalizados · 46 programados · 1 reprogramado
**Partidos por fase:** 217 regular · 4 cuartos · 2 semifinal · 1 tercer lugar · 1 final

### Ligas cargadas

| Liga | Categorías | Equipos | Sedes | Partidos |
|---|---:|---:|---:|---:|
| **Liga Premier Villahermosa** (real) | 2 | 14 | 0 | 46 |
| La Liga | 2 | 38 | 2 | 179 |
| Liga MX | 2 | 40 | 0 | 0 |
| Premier League | 2 | 32 | 0 | 0 |
| Serie A | 2 | 34 | 0 | 0 |
| Bundesliga | 2 | 44 | 0 | 0 |
| Cachirules | 1 | 0 | 0 | 0 |

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

**No hay un solo dato corrupto.** Las validaciones del sistema están funcionando de
verdad, no solo declaradas.

### Observaciones sobre los datos

- **223 de 225 partidos no tienen sede asignada.** Solo hay 2 canchas dadas de alta, y
  ninguna en la liga real. Toda la función de mapas (Leaflet, alta de sede desde el pin,
  `url_como_llegar`) está construida pero sin uso.
- **46 partidos "programados" sin fecha** — es el estado normal recién generado el
  calendario, pero impacta en la portada (ver hallazgo #6).
- **185 de 204 usuarios nunca iniciaron sesión.** Las 197 cuentas de entrenador se
  crearon en lote (existe el CSV) y casi ninguna se usó todavía.
- **La única liguilla completa (con campeón) está en La Liga → Segunda División**, que es
  liga de prueba. La liga real va por la jornada 1-4.
- **236 sesiones acumuladas** en `django_session`. Nunca se corrió `clearsessions`.

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

- `estadisticas/views.py::estadisticas_liga_categorias` (línea 21)
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
