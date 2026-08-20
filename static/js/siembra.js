(function () {
  var MARCO = '[data-llaves-por-ronda]';

  function cuantasLlaves(marco) {
    var mapa = {};
    (marco.getAttribute('data-llaves-por-ronda') || '').split(',').forEach(function (par) {
      var partes = par.split(':');
      if (partes.length === 2) mapa[partes[0]] = parseInt(partes[1], 10);
    });
    return mapa;
  }

  function tapar(bloque, tapado) {
    if (!bloque) return;
    bloque.hidden = tapado;
    if ('inert' in bloque) bloque.inert = tapado;
  }

  function equiposElegidos(marco) {
    var vistos = {};
    marco.querySelectorAll('.siembra-llave:not([hidden]) select').forEach(function (campo) {
      if (campo.value) vistos[campo.value] = (vistos[campo.value] || 0) + 1;
    });
    return vistos;
  }

  function marcarRepetidos(marco) {
    var vistos = equiposElegidos(marco);
    marco.querySelectorAll('.siembra-llave:not([hidden]) select').forEach(function (campo) {
      var repetido = campo.value && vistos[campo.value] > 1;
      campo.classList.toggle('campo-siembra-repetido', repetido);
    });
  }

  function actualizar(marco) {
    if (!marco) return;

    var elegida = marco.querySelector('input[name="ronda"]:checked');
    var visibles = elegida ? cuantasLlaves(marco)[elegida.value] || 0 : 0;

    marco.querySelectorAll('.siembra-llave').forEach(function (llave) {
      var numero = parseInt(llave.getAttribute('data-llave'), 10);
      var fuera = numero >= visibles;
      tapar(llave, fuera);
      llave.querySelectorAll('select').forEach(function (campo) {
        campo.disabled = fuera;
        if (fuera) campo.value = '';
      });
    });

    tapar(marco.querySelector('[data-siembra-llaves-marco]'), visibles === 0);
    tapar(marco.querySelector('[data-siembra-espera]'), visibles > 0);
    marcarRepetidos(marco);
  }

  function actualizarTodos() {
    document.querySelectorAll(MARCO).forEach(actualizar);
  }

  document.addEventListener('change', function (evento) {
    var marco = evento.target.closest && evento.target.closest(MARCO);
    if (!marco) return;
    if (evento.target.name === 'ronda') actualizar(marco);
    else if (evento.target.tagName === 'SELECT') marcarRepetidos(marco);
  });

  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 && (nodo.matches(MARCO) || nodo.querySelector(MARCO));
      });
    });
    if (aparecio) actualizarTodos();
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', actualizarTodos);
})();