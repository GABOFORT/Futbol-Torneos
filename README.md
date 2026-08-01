# Futbol-Torneos
Plataforma para administrar ligas, torneos, equipos y jugadores en un sistema deportivo empresarial.

## Configuración
1. Copia el archivo `.env.example` a `.env`.
2. Ajusta los valores de `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` y la conexión PostgreSQL.
3. Instala dependencias:

```powershell
python -m pip install -r requirements.txt
```

4. Ejecuta migraciones:

```powershell
python manage.py migrate
```

5. Crea el superusuario:

```powershell
python manage.py createsuperuser
```

6. Inicia el servidor:

```powershell
python manage.py runserver
```

## Estilos (Tailwind CSS)

El proyecto usa el **CLI standalone de Tailwind** (sin Node/npm). El CSS ya compilado vive en
`static/css/tailwind.css` y está versionado en el repo, así que no necesitas nada extra para correr el
proyecto tal cual.

Solo necesitas reconstruirlo cuando agregues o cambies clases de Tailwind:

```powershell
# Si no tienes tools/tailwindcss.exe (está en .gitignore por su tamaño), descárgalo una vez:
curl -L -o tools/tailwindcss.exe https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe

# Reconstruir el CSS (purgado y minificado):
./tools/tailwindcss.exe -i static/css/input.css -o static/css/tailwind.css --minify
```

**Importante — dónde busca las clases.** `static/css/input.css` escanea dos lugares:

- `templates/**/*.html`
- `apps/**/*.py` — porque `StyledFormMixin` (en `apps/usuarios/forms.py`) define ahí las clases de
  todos los campos de formulario.

Si sacas la segunda línea, al reconstruir el CSS **todos los formularios pierden el estilo** y no
aparece ningún error que lo avise.

**Componentes en CSS plano.** Algunos componentes (`.btn-accion`, `.dorsal`, `.usuario-chip`,
`.campo-archivo`…) están escritos como CSS normal dentro del `<style>` de `templates/base.html`, no
como clases de Tailwind. Ahí viven porque necesitan cosas que Tailwind no cubre bien —
`:has()`, superponer el número sobre la camiseta, la flecha propia de los `<select>`. No dependen de
la reconstrucción del CSS.

## Variable de entorno empresarial
Usa `.env` para definir:
- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

## Flujo del sistema a nivel empresarial

### 1. Roles y jerarquía

1. **Super Admin**
   - Es el dueño absoluto del sistema.
   - Control total de permisos, acceso, creación y edición de todos los usuarios.
   - Crea y administra cuentas de:
     - `Admin Liga`
     - `Entrenadores`
     - Otros perfiles (árbitros, staff, etc.) si se necesita.
   - Administra configuraciones globales, seguridad y visibilidad de datos.

2. **Admin Liga**
   - Opera bajo el Super Admin.
   - Crea y gestiona:
     - Ligas
     - Torneos
     - Categorías
     - Reglas de inscripción
     - Cantidad de equipos por liga/categoría
   - Decide qué equipos participan y en qué categoría entran.
   - Supervisa la estructura de la competencia.

3. **Entrenador**
   - Está debajo del Admin Liga.
   - Registra:
     - Su equipo
     - Plantilla de jugadores
     - Categoría en la que desea competir
     - Formación, alineación y detalle de quién jugará
   - Gestiona la información de su equipo y alumnos/jugadores.

---

## 2. Diagrama conceptual del flujo

- Super Admin → Admin Liga → Entrenador
- Liga → Torneo → Categoría → Equipo → Plantilla → Jugadores
- Roles con permisos escalonados y visibilidad restringida según jerarquía.

### Diagrama visual

```
[Super Admin]
      |
      v
 [Admin Liga]
      |
      v
 [Entrenador]

[Admin Liga] --> [Liga]
[Liga] --> [Torneo]
[Torneo] --> [Categoría]
[Categoría] --> [Equipo]
[Equipo] --> [Plantilla]
[Plantilla] --> [Jugadores]
```

---

## 3. Lógica del proceso

### Paso 1: Super Admin

- Genera el rol principal.
- Crea el `Admin Liga` y le da permisos administrativos.
- Controla que los procesos de alta y baja solo los vea quien debe verlos.

### Paso 2: Admin Liga

- Crea una liga nueva:
  - `Liga A`
  - `Liga B`
- Define las `categorías` que formarán parte de esa liga:
  - `Sub-15`
  - `Sub-17`
  - `Libre`
- Establece cuántos equipos entran por categoría:
  - 8 equipos en Sub-15
  - 10 equipos en Libre
- Crea torneos dentro de la liga:
  - Torneo Apertura
  - Torneo Clausura
- Define reglas del torneo:
  - Cuántos equipos por jornada
  - Si hay playoffs
  - Si hay fases de grupos

### Paso 3: Entrenadores

- Se registran o el Super Admin / Admin Liga les crea cuenta.
- Registran su equipo y plantilla:
  - Nombre del equipo
  - Jugadores
  - Categoría de competencia
  - Datos de contacto
- Proveen información competitiva:
  - Quién va a jugar
  - Formación
  - Disponibilidad
- Pueden actualizar la plantilla y la alineación.
- El sistema debe permitir:
  - Subir lista de jugadores
  - Marcar baja, lesión, sanción
  - Ver estado de aprobación

---

## 4. Reglas empresariales importantes

- El `Super Admin` nunca depende del `Admin Liga`; es superior.
- El `Admin Liga` no puede cambiar datos del `Super Admin`.
- El `Entrenador` no crea ligas ni categorías; él solo solicita participación y administra su equipo.
- La `Liga` es el contenedor de las competencias.
- El `Torneo` es un evento dentro de la liga.
- La `Categoría` define a qué nivel pertenece el equipo.
- El `Equipo` es gestionado por el entrenador.
- La `Plantilla` pertenece al equipo y se compone de `jugadores`.

---

## 5. Flujo de uso típico

1. Super Admin crea Admin Liga.
2. Admin Liga crea una Liga.
3. Admin Liga define categorías y número de equipos.
4. Admin Liga abre inscripción para entrenadores.
5. Entrenadores registran su equipo y plantillas.
6. Admin Liga revisa y aprueba los equipos por categoría.
7. Admin Liga publica calendario/torneo.
8. Entrenadores actualizan formaciones y lista de jugadores.
9. Admin Liga controla el estado de cada equipo y finaliza la inscripción.

---

## 6. Flujo completo del sistema

### Inicio del ciclo

1. El `Super Admin` ingresa al sistema.
2. Revisa el panel de control general y los permisos globales.
3. Crea uno o varios `Admin Liga` con acceso exclusivo a ligas y torneos.
4. Configura parámetros corporativos: políticas de inscripción, límites de equipos y reglas globales.

### Operación de competencias

5. `Admin Liga` accede y crea ligas nuevas.
6. Define categorías de competencia dentro de cada liga.
7. Configura torneos, fechas, formato (ascenso, fase de grupos, playoffs) y el número de equipos por categoría.
8. Publica la invitación de inscripción para entrenadores.

### Gestión de entrenadores y equipos

9. Los `Entrenadores` reciben invitación o se registran con un usuario.
10. Registran su equipo y completan la plantilla de jugadores.
11. Seleccionan la categoría de competencia y suben información relevante.
12. Actualizan la alineación y estado de cada jugador.
13. El sistema registra bajas, lesiones y sanciones.

### Revisión y aprobación

14. `Admin Liga` revisa cada inscripción de equipo.
15. Aprueba o rechaza equipos según reglas de la liga y cupos disponibles.
16. Ajusta la clasificación de equipos por categoría si es necesario.

### Publicación y ejecución

17. `Admin Liga` publica el calendario del torneo.
18. Los `Entrenadores` usan el sistema para ver fechas, plantillas y alineaciones.
19. El sistema mantiene el estado de cada equipo y la disponibilidad de jugadores.

### Cierre del ciclo

20. Finalizada la inscripción, el `Admin Liga` cierra el periodo de registro.
21. El `Super Admin` revisa métricas globales y auditoría de accesos.
22. El ciclo puede reiniciarse para la siguiente temporada o nuevo torneo.

---

## 7. Cómo se ve el modelo empresarial

- `Super Admin = CEO del sistema`
- `Admin Liga = gerente operativo de competiciones`
- `Entrenador = operador de su propio equipo`

### Resumen de permisos por rol

- **Super Admin**
  - Acceso a todas las secciones del sistema.
  - Gestión de usuarios y permisos.
  - Creación y edición de Admin Liga, entrenadores y perfiles adicionales.
  - Control de configuraciones globales, seguridad y visibilidad.

- **Admin Liga**
  - Creación y edición de ligas, torneos y categorías.
  - Definición de reglas de inscripción y cupos por categoría.
  - Revisión y aprobación de equipos inscritos.
  - Publicación de calendarios y administración de la competencia.
  - No puede modificar datos de Super Admin.

- **Entrenador**
  - Registro y actualización de su propio equipo.
  - Gestión de plantilla y jugadores.
  - Envío de información de formación, disponibilidad y estado de los jugadores.
  - No puede crear ligas ni categorías.

Este esquema es el más claro para una estructura jerárquica y de control en una plataforma deportiva empresarial.

---

## Todo list

- [x] Revisar modelos existentes y esquema de usuarios
- [ ] Diseñar nuevos modelos para roles, ligas, torneos y equipos
- [ ] Implementar modelos y registrar en admin
- [ ] Ejecutar migraciones y verificar la base de datos
