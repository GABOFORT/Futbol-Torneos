// En el formulario de resultado, el selector de "quien gano los penales" solo
// tiene sentido si el partido termino empatado. Se muestra u oculta segun los
// goles cargados, en vez de pedir un check aparte que podria contradecirlos.
//
// Los eventos se escuchan en el documento porque el formulario llega despues,
// inyectado en el modal.
(function () {
  var CAMPO_PENALES = '[data-campo="ganador_penales"]';

  function actualizar(contenedor) {
    var bloque = contenedor.querySelector(CAMPO_PENALES);
    var local = contenedor.querySelector('[name="goles_local"]');
    var visitante = contenedor.querySelector('[name="goles_visitante"]');
    if (!bloque || !local || !visitante) return;

    var hayEmpate = local.value !== '' && visitante.value !== '' &&
                    Number(local.value) === Number(visitante.value);
    bloque.hidden = !hayEmpate;

    // Si dejo de haber empate se limpia la eleccion: si no, quedaria guardado
    // un ganador de penales en un partido que ya no termino igualado.
    if (!hayEmpate) {
      var select = bloque.querySelector('select');
      if (select) select.value = '';
    }
  }

  document.addEventListener('input', function (evento) {
    var campo = evento.target;
    if (campo.name !== 'goles_local' && campo.name !== 'goles_visitante') return;
    var contenedor = campo.closest('form') || document;
    actualizar(contenedor);
  });

  // Al abrir el modal el formulario ya viene con valores cargados (por ejemplo
  // al corregir un resultado), asi que hay que evaluarlo de entrada.
  var observador = new MutationObserver(function () {
    document.querySelectorAll('form').forEach(actualizar);
  });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(actualizar);
    observador.observe(document.body, { childList: true, subtree: true });
  });
})();
