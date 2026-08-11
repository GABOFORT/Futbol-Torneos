# Cambios de seguridad de agosto 2026 — cómo pasarlos a desarrollo

Guía para dejar la máquina de desarrollo funcionando después de bajar los
commits `5e7971c`, `e9174f9` y los que siguen.

**Lo importante en una línea:** el código viaja solo con el `git pull`, pero
**el proyecto no arranca** hasta agregar unas variables al `.env` local,
instalar una dependencia nueva y correr las migraciones.

---

## 1. Qué se hizo en producción

Ocho arreglos, salidos de una auditoría completa del proyecto.

| # | Qué estaba mal | Dónde se arregló |
|---|---|---|
| 1 | XSS almacenado en el mapa de canchas | `static/js/mapa-sedes.js` |
| 2 | `SECRET_KEY` y `DB_PASSWORD` con el valor real como default | `futbol/settings.py` |
| 3 | Los validadores de contraseña nunca se ejecutaban | `apps/usuarios/forms.py` |
| 4 | 187 cuentas demo con contraseña publicada en un CSV | base de datos (no viaja por git) |
| 5 | Cookies de sesión sin marca de "solo HTTPS" | `futbol/settings.py` + `.env` |
| 6 | Sin límite de intentos de login | `django-axes` |
| 7 | La renovación del certificado iba a fallar | `web.config` de IIS (no viaja por git) |
| 8 | El puerto 80 servía el sitio sin cifrar | `web.config` de IIS (no viaja por git) |

Los detalles de cada uno están en el mensaje del commit `5e7971c`.

---

## 2. Lo que SÍ viaja con el `git pull`

No hay que hacer nada con esto, llega solo:

- El arreglo del XSS en `mapa-sedes.js`
- `PasswordValidadoMixin` en `apps/usuarios/forms.py`
- Las variables nuevas de `futbol/settings.py`
- `django-axes` agregado a `requirements.txt`
- `templates/usuarios/bloqueado.html` y sus estilos en `portada.css`
- El `.env.example` actualizado, que sirve de plantilla
- El `.gitignore` que ahora ignora también las copias del `.env`

---

## 3. Lo que hay que hacer a mano en desarrollo

### Paso 1 — Agregar las variables al `.env` local

```bash
SECRET_KEY=cualquier-cosa-larga-esto-es-solo-dev
DB_PASSWORD=la-de-tu-postgres-local

COOKIES_SEGURAS=False
FORZAR_HTTPS=False

AXES_FAILURE_LIMIT=5
AXES_COOLOFF_HORAS=0.25
```

**Por qué cada una:**

| Variable | Si falta |
|---|---|
| `SECRET_KEY` | **No arranca.** Se le quitó el default a propósito: antes, si faltaba, el proyecto levantaba con una clave conocida y nadie se enteraba |
| `DB_PASSWORD` | **No arranca**, por lo mismo |
| `COOKIES_SEGURAS` | Arranca (default `False`), pero conviene dejarla escrita |
| `FORZAR_HTTPS` | Arranca (default `False`) |
| `AXES_*` | Arranca con 5 intentos y 15 minutos |

**Van en `False` en desarrollo** porque ahí se entra por `http://localhost`.
Con `COOKIES_SEGURAS=True` el navegador no guardaría la cookie de sesión y
**no se podría iniciar sesión**.

> ⚠️ **No escribir el `.env` con PowerShell.** `Set-Content -Encoding utf8` en
> PowerShell 5.1 le mete un BOM —tres bytes invisibles al principio— y eso
> impide leer la primera variable. Pasó en producción el 11/08/2026: el sitio
> devolvía 502 y el error no decía nada útil. Usar el Bloc de notas, VS Code o
> Python.

### Paso 2 — Instalar la dependencia nueva

```powershell
pip install -r requirements.txt
```

Sin esto Django no levanta: `axes` está en `INSTALLED_APPS`.

### Paso 3 — Correr las migraciones

```powershell
python manage.py migrate
```

`django-axes` trae 10 migraciones: son las tablas donde anota los intentos
fallidos. Sin ellas el proyecto arranca, pero **revienta al intentar entrar**.

---

## 4. Lo que NO se replica en desarrollo

| Qué | Por qué |
|---|---|
| Las reglas del `web.config` (ACME y redirección a HTTPS) | Son de IIS. En desarrollo se usa `runserver`, no hay proxy |
| Las 187 cuentas demo neutralizadas | Se hizo sobre la base de producción, que es distinta de la local |
| La rotación de `SECRET_KEY` | Cada máquina tiene la suya |

---

## 5. Comprobar que quedó bien

```powershell
python manage.py check
```
Tiene que decir `System check identified no issues`.

Después, en el navegador:

| Prueba | Qué tiene que pasar |
|---|---|
| Crear un usuario con contraseña `12345` | Lo rechaza: *"demasiado corta"* |
| Crear uno con `Tlaloc-Verde-2026` | Lo acepta |
| Editar un usuario dejando la contraseña vacía | Guarda normal (vacío = no cambiar) |
| Fallar el login 5 veces con un usuario inventado | Sale la pantalla "Demasiados intentos" |
| Abrir el mapa de canchas y pulsar un pin | El globito muestra el nombre como texto |

Si quedaste bloqueado probando el login:

```powershell
python manage.py axes_reset
```

---

## 6. Lo que sigue pendiente

| Qué | Cuándo |
|---|---|
| Rotar la contraseña de PostgreSQL en producción | Sigue en el historial de git (commit `b2943d0`); quitarla del código no la borra del pasado |
| Verificar que el certificado se renovó solo | **23/09/2026** |
| Activar HSTS (`SECURE_HSTS_SECONDS`) | Solo **después** de comprobar lo anterior |

**Por qué HSTS espera:** le dice al navegador *"nunca más entres por HTTP"*, y
el navegador lo obedece aunque después nos arrepintamos. Si el certificado
venciera con HSTS activo, nadie podría entrar al sitio de ninguna forma, ni
saltando la advertencia. Primero hay que **ver** que la renovación funciona.
