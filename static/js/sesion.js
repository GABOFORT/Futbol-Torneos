

(function () {
  var caja = document.getElementById('sesion-aviso');
  if (!caja) return;

  var CLAVE_ACTIVIDAD = 'buho:sesion-actividad';

  var CADA_CUANTO_RENOVAR = 60000;

  var PULSO = 1000;

  var total = parseInt(caja.getAttribute('data-total'), 10);
  var aviso = parseInt(caja.getAttribute('data-aviso'), 10);
  var urlRenovar = caja.getAttribute('data-url-renovar');
  var urlExpirada = caja.getAttribute('data-url-expirada');
  var csrf = caja.getAttribute('data-csrf');

  if (!total || !aviso || aviso >= total) return;

  var anillo = document.getElementById('sesion-anillo-avance');
  var reloj = document.getElementById('sesion-reloj-texto');
  var botonSeguir = document.getElementById('sesion-seguir');

  var ultimaActividad = Date.now();
  var ultimaRenovacion = Date.now();
  var visible = false;
  var renovando = false;
  var focoPrevio = null;

  var vuelta = anillo ? 2 * Math.PI * parseFloat(anillo.getAttribute('r')) : 0;
  if (anillo) {
    anillo.style.strokeDasharray = vuelta;
    anillo.style.strokeDashoffset = 0;
  }

  function marcarActividad() {
    ultimaActividad = Date.now();
    try {
      localStorage.setItem(CLAVE_ACTIVIDAD, String(ultimaActividad));
    } catch (error) {

    }
  }

  function actividadReal() {
    try {
      var compartida = parseInt(localStorage.getItem(CLAVE_ACTIVIDAD), 10);
      if (compartida && compartida > ultimaActividad) return compartida;
    } catch (error) {  }
    return ultimaActividad;
  }

  ['mousedown', 'keydown', 'touchstart', 'scroll', 'click'].forEach(function (evento) {
    document.addEventListener(evento, marcarActividad, { passive: true });
  });

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) revisar();
  });

  function renovar(alVolver) {
    if (renovando) return;
    renovando = true;
    fetch(urlRenovar, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf },

      credentials: 'same-origin',
      cache: 'no-store'
    })
      .then(function (respuesta) {
        renovando = false;

        if (respuesta.status === 401) { expirar(); return; }
        if (!respuesta.ok) return;
        return respuesta.json().then(function (datos) {

          if (datos && datos.segundos) total = datos.segundos;
          ultimaRenovacion = Date.now();
          marcarActividad();
          if (alVolver) alVolver();
        });
      })
      .catch(function () {

        renovando = false;
      });
  }

  function expirar() {
    location.href = urlExpirada;
  }

  function comoReloj(segundos) {
    var minutos = Math.floor(segundos / 60);
    var resto = segundos % 60;
    return minutos + ':' + (resto < 10 ? '0' : '') + resto;
  }

  function mostrar() {
    if (visible) return;
    visible = true;

    focoPrevio = document.activeElement;
    caja.hidden = false;

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

      if (reloj.textContent !== texto) reloj.textContent = texto;
    }
    if (anillo) {

      var proporcion = Math.max(0, Math.min(1, faltan / aviso));
      anillo.style.strokeDashoffset = vuelta * (1 - proporcion);
    }
  }

  function revisar() {
    var inactivo = Math.floor((Date.now() - actividadReal()) / 1000);
    var faltan = total - inactivo;

    if (faltan <= 0) { expirar(); return; }

    if (faltan <= aviso) {
      mostrar();
      pintar(faltan);
      return;
    }

    ocultar();

    if (Date.now() - ultimaRenovacion >= CADA_CUANTO_RENOVAR) {
      renovar();
    }
  }

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

  document.addEventListener('keydown', function (evento) {
    if (visible && evento.key === 'Escape' && botonSeguir) botonSeguir.click();
  });

  marcarActividad();
  setInterval(revisar, PULSO);
})();
