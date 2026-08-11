// Aviso de sesión por vencer, con cuenta regresiva.
//
// QUIÉN MANDA ACÁ. El servidor, siempre. La sesión vence sola a los 20 minutos
// por SESSION_COOKIE_AGE (futbol/settings.py), corra este script o no. Todo lo
// que hay abajo es cortesía: avisar antes en vez de que la persona descubra que
// se quedó afuera al pulsar "Guardar" y perder lo que estaba cargando.
//
// EL PROBLEMA QUE RESUELVE, que no es obvio. Mover el mouse NO renueva nada del
// lado del servidor: la sesión se renueva con peticiones HTTP, no con actividad
// en la pantalla. Sin este archivo, alguien leyendo la tabla de posiciones media
// hora sin pulsar un enlace veía la página perfectamente normal mientras su
// sesión ya estaba muerta. Por eso acá la actividad real dispara un "toque" al
// servidor (ver renovar()): así lo que ve el usuario y lo que sabe el servidor
// dicen lo mismo.
//
// ENTRE PESTAÑAS. La actividad se comparte por localStorage. Sin eso, trabajar
// en una pestaña mientras otra está quieta hacía saltar el aviso en la quieta, y
// al usuario le aparecía "¿sigues ahí?" justo mientras escribía en la de al lado.
(function () {
  var caja = document.getElementById('sesion-aviso');
  if (!caja) return;   // visitante sin sesión: no hay nada que vigilar

  var CLAVE_ACTIVIDAD = 'buho:sesion-actividad';

  // Cada cuánto se le toca la puerta al servidor mientras hay actividad. No en
  // cada movimiento del mouse —serían cientos de peticiones por minuto— sino
  // como mucho una vez por minuto. Con 20 minutos de margen sobra de lejos.
  var CADA_CUANTO_RENOVAR = 60000;

  // El pulso del reloj. Un segundo es lo más grueso que se puede usar sin que la
  // cuenta regresiva se vea a los saltos.
  var PULSO = 1000;

  var total = parseInt(caja.getAttribute('data-total'), 10);
  var aviso = parseInt(caja.getAttribute('data-aviso'), 10);
  var urlRenovar = caja.getAttribute('data-url-renovar');
  var urlExpirada = caja.getAttribute('data-url-expirada');
  var csrf = caja.getAttribute('data-csrf');

  // Si los números vienen rotos se prefiere no hacer nada antes que sacar a
  // alguien de su trabajo por un error de configuración.
  if (!total || !aviso || aviso >= total) return;

  var anillo = document.getElementById('sesion-anillo-avance');
  var reloj = document.getElementById('sesion-reloj-texto');
  var botonSeguir = document.getElementById('sesion-seguir');

  var ultimaActividad = Date.now();
  var ultimaRenovacion = Date.now();
  var visible = false;
  var renovando = false;
  var focoPrevio = null;

  // La circunferencia sale del radio que tiene el SVG en el HTML, en vez de
  // escribir el número acá: si el diseño cambia el tamaño del círculo, el
  // anillo sigue funcionando sin que haya que acordarse de tocar este archivo.
  var vuelta = anillo ? 2 * Math.PI * parseFloat(anillo.getAttribute('r')) : 0;
  if (anillo) {
    anillo.style.strokeDasharray = vuelta;
    anillo.style.strokeDashoffset = 0;
  }

  // --- Actividad -----------------------------------------------------------

  function marcarActividad() {
    ultimaActividad = Date.now();
    try {
      localStorage.setItem(CLAVE_ACTIVIDAD, String(ultimaActividad));
    } catch (error) {
      // Modo privado de algunos navegadores. Se sigue sin compartir entre
      // pestañas, que es peor pero no rompe nada.
    }
  }

  // La actividad más reciente entre esta pestaña y las demás.
  function actividadReal() {
    try {
      var compartida = parseInt(localStorage.getItem(CLAVE_ACTIVIDAD), 10);
      if (compartida && compartida > ultimaActividad) return compartida;
    } catch (error) { /* ver arriba */ }
    return ultimaActividad;
  }

  // passive: estos eventos se disparan muchísimo y avisarle al navegador que no
  // se va a llamar a preventDefault() le permite no bloquear el scroll.
  ['mousedown', 'keydown', 'touchstart', 'scroll', 'click'].forEach(function (evento) {
    document.addEventListener(evento, marcarActividad, { passive: true });
  });

  // Volver a la pestaña cuenta como actividad, pero además hay que revisar el
  // reloj enseguida: si la laptop estuvo suspendida una hora, los temporizadores
  // de JavaScript no corrieron y sin esto la pantalla se vería normal un rato
  // largo con la sesión ya vencida.
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) revisar();
  });

  // --- Servidor ------------------------------------------------------------

  function renovar(alVolver) {
    if (renovando) return;
    renovando = true;
    fetch(urlRenovar, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf },
      // same-origin y no 'include': la cookie de sesión tiene que viajar, pero
      // no hace falta abrirlo a otros dominios.
      credentials: 'same-origin',
      cache: 'no-store'
    })
      .then(function (respuesta) {
        renovando = false;
        // 401 = el servidor dice que ya no hay sesión. Manda él, no el reloj
        // de esta pantalla.
        if (respuesta.status === 401) { expirar(); return; }
        if (!respuesta.ok) return;
        return respuesta.json().then(function (datos) {
          // El servidor devuelve los segundos que quedan de verdad. Se le hace
          // caso: si alguien cambió SESION_MINUTOS en el .env, esta pantalla se
          // entera sin recargar.
          if (datos && datos.segundos) total = datos.segundos;
          ultimaRenovacion = Date.now();
          marcarActividad();
          if (alVolver) alVolver();
        });
      })
      .catch(function () {
        // Error de red: puede ser el wifi del club, no la sesión. Se deja que
        // el reloj siga corriendo; si de verdad venció, el próximo intento
        // devolverá 401 y ahí sí se cierra.
        renovando = false;
      });
  }

  function expirar() {
    location.href = urlExpirada;
  }

  // --- Pantalla ------------------------------------------------------------

  function comoReloj(segundos) {
    var minutos = Math.floor(segundos / 60);
    var resto = segundos % 60;
    return minutos + ':' + (resto < 10 ? '0' : '') + resto;
  }

  function mostrar() {
    if (visible) return;
    visible = true;
    // Se recuerda dónde estaba el foco para devolverlo al cerrar: si alguien
    // estaba escribiendo en un campo, tiene que volver ahí y no al principio
    // del formulario.
    focoPrevio = document.activeElement;
    caja.hidden = false;
    // El scroll del fondo se congela: con el aviso abierto, mover la rueda y
    // ver moverse la página de atrás se siente roto.
    document.body.classList.add('sesion-quieta');
    if (botonSeguir) botonSeguir.focus();
  }

  function ocultar() {
    if (!visible) return;
    visible = false;
    caja.hidden = true;
    document.body.classList.remove('sesion-quieta');
    if (focoPrevio && focoPrevio.focus) focoPrevio.focus();
    focoPrevio = null;
  }

  function pintar(faltan) {
    if (reloj) {
      var texto = comoReloj(faltan);
      // Solo se escribe si cambió: asignar el mismo texto igual reemplaza el
      // nodo y hace que el lector de pantalla lo vuelva a cantar cada segundo.
      if (reloj.textContent !== texto) reloj.textContent = texto;
    }
    if (anillo) {
      // El anillo se vacía a medida que se acaba el tiempo del aviso.
      var proporcion = Math.max(0, Math.min(1, faltan / aviso));
      anillo.style.strokeDashoffset = vuelta * (1 - proporcion);
    }
  }

  // --- El reloj ------------------------------------------------------------

  function revisar() {
    var inactivo = Math.floor((Date.now() - actividadReal()) / 1000);
    var faltan = total - inactivo;

    if (faltan <= 0) { expirar(); return; }

    if (faltan <= aviso) {
      mostrar();
      pintar(faltan);
      return;
    }

    // Hay actividad y queda tiempo: si el aviso estaba abierto (porque la
    // persona volvió y movió el mouse) se cierra solo.
    ocultar();

    // Mientras se trabaja, se le toca la puerta al servidor de a ratos para que
    // la sesión de allá no venza mientras acá se ve todo bien. Este es el
    // corazón del asunto, no un detalle.
    if (Date.now() - ultimaRenovacion >= CADA_CUANTO_RENOVAR) {
      renovar();
    }
  }

  // --- Botones -------------------------------------------------------------

  if (botonSeguir) {
    botonSeguir.addEventListener('click', function () {
      botonSeguir.disabled = true;
      botonSeguir.textContent = 'Reconectando…';
      marcarActividad();
      renovar(function () {
        botonSeguir.disabled = false;
        botonSeguir.textContent = 'Seguir conectado';
        ocultar();
      });
    });
  }

  // Escape también sirve para seguir conectado: es el gesto natural para sacar
  // de encima una ventana, y acá cerrarla significa justamente "sigo acá".
  document.addEventListener('keydown', function (evento) {
    if (visible && evento.key === 'Escape' && botonSeguir) botonSeguir.click();
  });

  // A propósito NO se cierra al hacer clic en el fondo, al revés que el modal
  // de las fichas: un clic perdido no puede ser lo que decida si la sesión
  // sigue viva. Que haya que pulsar el botón es la idea.

  marcarActividad();
  setInterval(revisar, PULSO);
})();
