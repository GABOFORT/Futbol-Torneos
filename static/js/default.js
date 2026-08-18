

(function () {

  var CAMPOS = [
    '[data-campo="goles_local"]',
    '[data-campo="goles_visitante"]',
    '[data-campo="ganador_penales"]',
    '[data-campo="penales_local"]',
    '[data-campo="penales_visitante"]',
  ];

  window.hayEquipoAusente = function (contenedor) {
    var select = (contenedor || document).querySelector('[data-ausente]');
    return !!(select && select.value);
  };

  function actualizar(contenedor) {
    var select = contenedor.querySelector('[data-ausente]');
    if (!select) return;

    var hayAusente = !!select.value;

    CAMPOS.forEach(function (selector) {

      var bloque = contenedor.querySelector(selector);
      if (bloque) bloque.hidden = hayAusente;
    });

    contenedor.querySelectorAll('.seccion-actuaciones').forEach(function (seccion) {
      seccion.hidden = hayAusente;
    });

    avisar(contenedor, select, hayAusente);

    if (!hayAusente && typeof window.revisarPenales === 'function') {
      window.revisarPenales(contenedor);
    }
  }

  function avisar(contenedor, select, hayAusente) {
    var aviso = contenedor.querySelector('[data-aviso-default]');
    if (!aviso) return;

    aviso.hidden = !hayAusente;
    if (!hayAusente) return;

    var ganador = '';
    Array.prototype.forEach.call(select.options, function (opcion) {
      if (opcion.value && opcion.value !== select.value) ganador = opcion.textContent.trim();
    });

    var texto = ganador + ' gana 3-0 por default. No se cargan goleadores ni asistencias.';
    if (aviso.textContent !== texto) aviso.textContent = texto;
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute || !campo.hasAttribute('data-ausente')) return;
    actualizar(campo.closest('form') || document);
  });

  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 &&
          (nodo.matches('[data-ausente]') || nodo.querySelector('[data-ausente]'));
      });
    });
    if (aparecio) document.querySelectorAll('form').forEach(actualizar);
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(actualizar);
  });
})();
