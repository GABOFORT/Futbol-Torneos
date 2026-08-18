

(function () {
  function actualizar(contenedor) {
    var rol = contenedor.querySelector('[data-rol]');
    if (!rol) return;

    contenedor.querySelectorAll('[data-solo-rol]').forEach(function (campo) {
      var bloque = campo.closest('[data-campo]');
      if (!bloque) return;
      bloque.hidden = campo.getAttribute('data-solo-rol') !== rol.value;
    });
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute || !campo.hasAttribute('data-rol')) return;
    actualizar(campo.closest('form') || document);
  });

  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 &&
          (nodo.matches('[data-rol]') || nodo.querySelector('[data-rol]'));
      });
    });
    if (aparecio) document.querySelectorAll('form').forEach(actualizar);
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(actualizar);
  });
})();
