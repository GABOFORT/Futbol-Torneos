

(function () {

  var CAMPOS = [
    '[data-campo="ganador_penales"]',
    '[data-campo="penales_local"]',
    '[data-campo="penales_visitante"]',
  ];

  function actualizar(contenedor) {
    var local = contenedor.querySelector('[name="goles_local"]');
    var visitante = contenedor.querySelector('[name="goles_visitante"]');
    if (!local || !visitante) return;

    if (typeof window.hayEquipoAusente === 'function' && window.hayEquipoAusente(contenedor)) {
      return;
    }

    var hayEmpate = local.value !== '' && visitante.value !== '' &&
                    Number(local.value) === Number(visitante.value);

    CAMPOS.forEach(function (selector) {

      var bloque = contenedor.querySelector(selector);
      if (!bloque) return;
      bloque.hidden = !hayEmpate;

      if (!hayEmpate) {
        var campo = bloque.querySelector('select, input');
        if (campo) campo.value = '';
      }
    });
  }

  document.addEventListener('input', function (evento) {
    var campo = evento.target;
    if (campo.name !== 'goles_local' && campo.name !== 'goles_visitante') return;
    var contenedor = campo.closest('form') || document;
    actualizar(contenedor);
  });

  window.revisarPenales = actualizar;

  var observador = new MutationObserver(function () {
    document.querySelectorAll('form').forEach(actualizar);
  });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(actualizar);
    observador.observe(document.body, { childList: true, subtree: true });
  });
})();
