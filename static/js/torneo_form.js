(function () {
  var MODALIDAD = '[data-modalidad]';
  var SOLO_GRUPOS = '[data-solo-grupos]';

  function contenedorDe(campo) {
    return campo.closest('label.ajuste') || campo.closest('[data-campo]') || campo;
  }

  function tapar(bloque, tapado) {
    if (!bloque) return;
    bloque.hidden = tapado;
    if ('inert' in bloque) bloque.inert = tapado;
  }

  function actualizar(ambito) {
    if (!ambito) return;

    var check = ambito.querySelector(SOLO_GRUPOS);
    if (!check) return;

    var permitidas = (check.getAttribute('data-solo-grupos') || '')
      .split(',')
      .filter(Boolean);

    var elegida = ambito.querySelector(MODALIDAD + ':checked');
    var activo = !!elegida && permitidas.indexOf(elegida.value) !== -1;

    tapar(contenedorDe(check), !activo);
  }

  function actualizarTodos() {
    document.querySelectorAll('form').forEach(actualizar);
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute || !campo.hasAttribute('data-modalidad')) return;
    actualizar(campo.closest('form') || document);
  });

  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 &&
          (nodo.matches(SOLO_GRUPOS) || nodo.querySelector(SOLO_GRUPOS));
      });
    });
    if (aparecio) actualizarTodos();
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', actualizarTodos);
})();