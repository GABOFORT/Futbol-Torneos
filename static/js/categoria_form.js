(function () {
  var LIBRE = '[data-libre]';
  var BLOQUE_RESTRICCIONES = '[data-restricciones]';
  var BLOQUE_MINIMOS = '[data-minimos]';
  var LIMITE = '[data-restriccion="limite_edad"]';
  var FORMATO = '[data-formato]';
  var BLOQUE_GRUPOS = '[data-solo-grupos]';
  var MINI_LIGUILLA = '[name="mini_liguilla"]';
  var POR_GRUPOS = 'grupos';

  function tapar(bloque, tapado) {
    if (!bloque) return;
    bloque.hidden = tapado;

    if ('inert' in bloque) bloque.inert = tapado;
  }

  function juegaPorGrupos(contenedor) {
    var elegido = contenedor.querySelector(FORMATO + ':checked');
    return !!(elegido && elegido.value === POR_GRUPOS);
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

    var porGrupos = juegaPorGrupos(contenedor);
    tapar(contenedor.querySelector(BLOQUE_GRUPOS), !porGrupos);

    var mini = contenedor.querySelector(MINI_LIGUILLA);
    if (mini) {
      if (porGrupos) mini.checked = false;
      tapar(mini.closest('.ajuste') || mini.parentElement, porGrupos);
    }
  }

  function actualizarTodos() {
    document.querySelectorAll('form').forEach(actualizar);
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute) return;
    var esLibre = campo.hasAttribute('data-libre');
    var esLimite = campo.getAttribute('data-restriccion') === 'limite_edad';
    var esFormato = campo.hasAttribute('data-formato');
    if (!esLibre && !esLimite && !esFormato) return;
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
