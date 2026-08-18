# Avisos técnicos — líneas que no se pueden tocar

El 18/08/2026 se eliminaron todos los comentarios del proyecto. Este archivo
recoge los avisos que iban pegados a líneas que **se ven como un error y no lo
son**. Sin el aviso, el próximo que lea ese código lo "corrige" y rompe algo que
ya se rompió antes.

Cada entrada dice: dónde está, qué pasa si se toca, y cuándo pasó.

---

## 1. `AXES_LOCKOUT_PARAMETERS` va con lista anidada

`futbol/settings.py`

```python
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
```

La lista dentro de otra lista significa **la combinación** usuario+IP. Escrita
plana — `['username', 'ip_address']` — django-axes la entiende como dos reglas
independientes: bloquea por usuario **o** por IP.

**Qué pasó el 11/08/2026:** estaba plana. Alguien falló 8 veces con el usuario
`PREMIER`, eso bloqueó la IP, y detrás de IIS la IP es la misma para todo el
mundo. **El sitio entero quedó sin acceso.** Cualquiera podía tumbarlo con cinco
intentos fallidos y un usuario inventado.

No aplanar nunca.

---

## 2. La cabecera del proxy lleva nombre propio, no el convencional

`futbol/settings.py`

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_ESQUEMA_ORIGINAL', 'https')
```

El nombre estándar sería `HTTP_X_FORWARDED_PROTO`. **No se usa a propósito:**
Waitress borra toda cabecera que empiece por `X-Forwarded-` salvo que se arranque
declarando un proxy de confianza (`clear_untrusted_proxy_headers` vale `True` de
fábrica).

Con el nombre convencional **nunca funcionó**: Django creyó que toda petición era
HTTP desde el primer día. Eso causó el bucle infinito de redirecciones del
11/08/2026 al activar `SECURE_SSL_REDIRECT`.

Se usa un nombre propio en vez de configurar el flag de Waitress porque el
servidor **se levanta a mano**, no como servicio de Windows: un flag olvidado en
el arranque rompería el bloqueo de axes en silencio. Una cabecera con otro nombre
funciona se arranque como se arranque.

Lo mismo aplica a `HTTP_X_IP_CLIENTE`, que es de donde sale la IP real del
visitante (`AXES_CLIENT_IP_CALLABLE`). Sin ella, `REMOTE_ADDR` es siempre
`127.0.0.1` — la conexión la abre IIS, no el visitante.

---

## 3. `AXES_CLIENT_IP_CALLABLE` apunta a una función propia, no a `AXES_IPWARE_*`

`futbol/settings.py` → `apps/usuarios/auditoria.py::ip_de`

Las opciones `AXES_IPWARE_*` **solo funcionan con el paquete django-ipware
instalado**, y no lo está. Axes las ignora en silencio y se queda con
`REMOTE_ADDR`. Se probó.

---

## 4. `SECRET_KEY` y `DB_PASSWORD` no llevan `default`

`futbol/settings.py`

```python
SECRET_KEY = config('SECRET_KEY')
'PASSWORD': config('DB_PASSWORD'),
```

Sin `default` a propósito: son secretos y no pueden vivir en un archivo
versionado. Si falta la variable, el arranque revienta con `UndefinedValueError`,
que es exactamente lo que se busca — mejor no arrancar que arrancar con una clave
conocida, porque con la `SECRET_KEY` se firman las sesiones.

**No agregarles un `default` "para que arranque".**

Nombre, host y puerto sí conservan `default`: no son secretos.

---

## 5. La CSP está en modo reporte, no en modo bloqueo

`futbol/settings.py`

```python
SECURE_CSP_REPORT_ONLY = { ... }
```

En modo reporte el navegador **anota** lo que bloquearía pero no bloquea nada.
Está así porque las plantillas todavía tienen scripts y estilos en línea; con la
política en modo bloqueo dejarían de funcionar hoy mismo.

Para pasar a bloqueo real hay que mover esos inline a archivos de `static/js/` y
recién entonces renombrar la variable a `SECURE_CSP`. **No antes.**

`UNSAFE_INLINE` está en `style-src` y nunca en `script-src`: un estilo inyectado
no ejecuta código, y ponerlo en `script-src` sería regalar la protección entera.

---

## 6. El orden del borrado en cascada de una liga

`apps/usuarios/views.py::liga_delete`

```python
premios.delete()
equipos.delete()
entrenadores.delete()
```

Ese orden es obligatorio: `Equipo.entrenador` es `PROTECT`, así que los equipos
tienen que irse **antes** que las cuentas de entrenador.

Además, `entrenadores_sin_equipo_tras_borrar(equipos)` se calcula **antes** de
borrar nada: después del `delete()` ya no se sabe quiénes eran.

`Equipo.liga` es `PROTECT` a propósito — protege contra borrados accidentales
desde el admin de Django o desde un script. La cascada se hace explícita solo en
esta vista.

---

## 7. En `eliminar.py`, los datos de la bitácora se leen antes del `delete()`

`apps/usuarios/eliminar.py`

Después del `delete()` la instancia se queda sin `pk` y la línea de la bitácora
saldría con `None`. Se registra con nivel `WARNING` y no `INFO` a propósito: es
la línea que se va a buscar el día que alguien pregunte quién borró algo.

---

## 8. Las rutas de `/static/` y `/media/` en `futbol/urls.py` son un respaldo

`futbol/urls.py`

```python
re_path(r'^static/(?P<path>.*)$', servir_estatico, ...)
re_path(r'^media/(?P<path>.*)$', servir_estatico, ...)
```

Hoy **no se usan**: IIS sirve esas dos rutas del disco (regla `ExcluirEstaticos`
en `web.config`). Se dejan puestas a propósito — si esa regla se perdiera en un
cambio futuro, el sitio se vería feo pero seguiría funcionando, en vez de quedarse
sin estilos ni imágenes.

**Por qué IIS y no Django:** Waitress tiene un número fijo de hilos y cada
escudo, foto y CSS ocupaba uno mientras se transfería. Pidiendo en bucle la
portada de una liga (1920 px) se le agotaban los hilos y **el sitio dejaba de
responder hasta para el login**. No hace falta ninguna vulnerabilidad, alcanza
con un `for` en un script.

---

## 9. `SECURE_REDIRECT_EXEMPT` protege la renovación del certificado

`futbol/settings.py`

```python
SECURE_REDIRECT_EXEMPT = [r'^\.well-known/acme-challenge/']
```

El desafío de Let's Encrypt tiene que poder responderse por `http://` simple. Hoy
no llega hasta Django — IIS lo sirve del disco antes, regla `ExcluirDesafioACME`,
que va **primero** — pero si esa regla se perdiera, sin esta excepción la
renovación empezaría a fallar sin que nadie se entere hasta que el certificado
vence.

En `web.config` hace falta además el `mimeMap` de `.well-known`: los archivos que
escribe Let's Encrypt no tienen extensión y de fábrica IIS se niega a servir lo
que no sabe qué tipo es.

---

## 10. Al editar `web.config`: nunca dos guiones seguidos dentro de un comentario

`docs/web.config.referencia`

Un comentario XML no admite `--`. Escribir el nombre de un flag de Waitress tal
cual (con los dos guiones que lleva delante) **invalida el archivo entero**, y
entonces IIS responde `500.19` en todas las URLs.

Pasó el 11/08/2026 y tiró el sitio.

---

## 11. El orden de las reglas de `web.config`

`docs/web.config.referencia`

1. `ExcluirDesafioACME` — primero, o el desafío del certificado termina en Django
   (404) y la validación falla.
2. `RedirigirAHTTPS` — después del anterior, para que la validación siga
   sirviéndose por http simple.
3. `ExcluirEstaticos` — después de los dos anteriores y **antes** del proxy.
4. `ReverseProxyInboundRule1` — último: captura `(.*)` y se lleva todo a Django.

El `set` de las cabeceras **sobreescribe** lo que mande el cliente, y eso es lo
que las hace confiables: nadie puede inventarse una IP para esquivar el bloqueo
de axes, porque IIS pisa su valor con el de la conexión TCP real.

---

## 12. `CARPETA_LOGS` y `MEDIA_ROOT` llevan un `or`, no solo `default`

`futbol/settings.py`

```python
CARPETA_LOGS = Path(config('CARPETA_LOGS', default='') or (BASE_DIR / 'logs'))
MEDIA_ROOT = config('MEDIA_ROOT', default='') or str(BASE_DIR / 'media')
```

`decouple` aplica el `default` solo si la variable **no está** en el `.env`. Si
está pero vacía —que es como el `.env.example` documenta "usa la de por
defecto"— devuelve cadena vacía, y `Path('')` es `Path('.')`: las bitácoras y las
imágenes habrían ido a parar al directorio desde el que se lanzó el servidor.

La carpeta de logs va fuera de `STATIC_ROOT` y de `MEDIA_ROOT` a propósito: Django
sirve esas dos por URL, así que un log ahí adentro sería descargable desde el
navegador.

---

## 13. `django_browser_reload` solo se monta con `DEBUG=True`

`futbol/settings.py` y `futbol/urls.py`

Su endpoint es un flujo de eventos que mantiene **tomado un hilo de Waitress por
conexión**, y Waitress arranca con cuatro (`iniciar_produccion.bat` no le pasa
`--threads`). El día que alguien encienda `DEBUG` en el servidor para depurar
algo, cuatro peticiones a esa URL dejarían el sitio sin responder.

El middleware va en la **posición 0**: tiene que envolver a todos los demás para
poder inyectar su script en el HTML ya armado.

---

## 14. `input.css` escanea también `apps/**/*.py`

`static/css/input.css` (ya documentado en el `README.md`)

Porque `StyledFormMixin` (en `apps/usuarios/forms.py`) define ahí las clases de
todos los campos de formulario. Si se saca esa línea, al reconstruir el CSS
**todos los formularios pierden el estilo** y no aparece ningún error que lo
avise.

---

## 15. `AUTHENTICATION_BACKENDS`: axes va primero

`futbol/settings.py`

Es el que corta el intento cuando la cuenta está bloqueada, antes de que el
backend de siempre se ponga a comparar el hash. Si fuera segundo, el bloqueo no
serviría de nada.
