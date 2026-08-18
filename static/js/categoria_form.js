

(function () {
  var LIBRE = '[data-libre]';
  var BLOQUE_RESTRICCIONES = '[data-restricciones]';
  var BLOQUE_MINIMOS = '[data-minimos]';
  var LIMITE = '[data-restriccion="limite_edad"]';

  function tapar(bloque, tapado) {
    if (!bloque) return;
    bloque.hidden = tapado;

    if ('inert' in bloque) bloque.inert = tapado;
  }

  function hayLimiteElegido(contenedor) {
    var elegido = contenedor.querySelector(LIMITE + ':checked');
    return !!(elegido && elegido.value);
  }

  function actualizar(contenedor) {
    if (!contenedor) return;
    var libre = contenedor.querySelector(LIBRE);
    if (!libre) return;

    tapar(contenedor.querySelector(BLOQUE_RESTRICCIONES), libre.checked);
    tapar(
      contenedor.querySelector(BLOQUE_MINIMOS),
      libre.checked || hayLimiteElegido(contenedor)
    );
  }

  function actualizarTodos() {
    document.querySelectorAll('form').forEach(actualizar);
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute) return;
    var esLibre = campo.hasAttribute('data-libre');
    var esLimite = campo.getAttribute('data-restriccion') === 'limite_edad';
    if (!esLibre && !esLimite) return;
    actualizar(campo.closest('form') || document);
  });

  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 &&
          (nodo.matches(LIBRE) || nodo.querySelector(LIBRE));
      });
    });
    if (aparecio) actualizarTodos();
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', actualizarTodos);
})();
