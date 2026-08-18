

(function () {
  function actualizar(contenedor) {
    var fecha = contenedor.querySelector('[data-min-masculino]');
    if (!fecha) return;

    var elegido = contenedor.querySelector('[data-sexo]:checked');

    var sexo = elegido ? elegido.value : 'masculino';

    var minimo = fecha.getAttribute('data-min-' + sexo);
    if (minimo && fecha.getAttribute('min') !== minimo) {
      fecha.setAttribute('min', minimo);
    }
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute || !campo.hasAttribute('data-sexo')) return;
    actualizar(campo.closest('form') || document);
  });

  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 &&
          (nodo.matches('[data-min-masculino]') || nodo.querySelector('[data-min-masculino]'));
      });
    });
    if (aparecio) document.querySelectorAll('form').forEach(actualizar);
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(actualizar);
  });
})();
