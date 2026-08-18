

(function () {
  var VISIBLE_MS = 6000;
  var SALIDA_MS = 260;

  function despedir(toast) {
    if (toast.dataset.saliendo) return;
    toast.dataset.saliendo = '1';
    toast.classList.add('toast-saliendo');

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
