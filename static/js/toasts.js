// Los avisos de arriba a la derecha: cierre manual y desaparición sola.
//
// Estaba dentro de base.html —un <script> suelto y un onclick= en el botón—,
// que son las dos cosas que impiden pasar la Content-Security-Policy de modo
// reporte a modo bloqueo. Aquí es un archivo más, cacheable y sin excepciones
// que pedirle a la política.
//
// Antes el aviso se borraba de golpe con .remove() a los 6 segundos: aparecía
// un cartel, y seis segundos después había un hueco. Ahora se va con una
// transición, que es lo que le dice al ojo que el elemento se fue y no que la
// página parpadeó.
(function () {
  var VISIBLE_MS = 6000;
  var SALIDA_MS = 260;

  function despedir(toast) {
    if (toast.dataset.saliendo) return;
    toast.dataset.saliendo = '1';
    toast.classList.add('toast-saliendo');
    // Se espera a que termine la transición para sacarlo del DOM. Con
    // prefers-reduced-motion la transición dura ~0 y el temporizador igual
    // corre: el elemento se va, simplemente sin animarse.
    window.setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, SALIDA_MS);
  }

  function iniciar() {
    var raiz = document.getElementById('toast-root');
    if (!raiz) return;

    raiz.addEventListener('click', function (evento) {
      var boton = evento.target.closest('[data-cerrar-toast]');
      if (!boton) return;
      var toast = boton.closest('.toast-message');
      if (toast) despedir(toast);
    });

    raiz.querySelectorAll('.toast-message').forEach(function (toast) {
      var reloj = window.setTimeout(function () { despedir(toast); }, VISIBLE_MS);

      // El temporizador se para mientras el puntero está encima o el foco está
      // dentro. Un aviso de error puede llevar el nombre del campo que falló, y
      // que se esfume mientras se lee obliga a repetir la acción para volver a
      // verlo.
      function parar() { window.clearTimeout(reloj); }
      function seguir() { reloj = window.setTimeout(function () { despedir(toast); }, VISIBLE_MS); }
      toast.addEventListener('mouseenter', parar);
      toast.addEventListener('mouseleave', seguir);
      toast.addEventListener('focusin', parar);
      toast.addEventListener('focusout', seguir);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
