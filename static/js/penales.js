// En el formulario de resultado, el selector de "quien gano los penales" solo
// tiene sentido si el partido termino empatado. Se muestra u oculta segun los
// goles cargados, en vez de pedir un check aparte que podria contradecirlos.
//
// Los eventos se escuchan en el documento porque el formulario llega despues,
// inyectado en el modal.
(function () {
  // El ganador de la tanda y cuantos convirtio cada uno: los tres solo tienen
  // sentido con el partido empatado, asi que se muestran y ocultan juntos.
  var CAMPOS = [
    '[data-campo="ganador_penales"]',
    '[data-campo="penales_local"]',
    '[data-campo="penales_visitante"]',
  ];

  function actualizar(contenedor) {
    var local = contenedor.querySelector('[name="goles_local"]');
    var visitante = contenedor.querySelector('[name="goles_visitante"]');
    if (!local || !visitante) return;

    // Si un equipo no se presento no se patean penales: el partido se resuelve
    // 3-0 en el escritorio. Sin esta guarda los dos scripts se peleaban por el
    // mismo `hidden` (el marcador oculto queda en 0-0, que aca se leia como
    // empate) y los campos de la tanda volvian a aparecer solos.
    if (typeof window.hayEquipoAusente === 'function' && window.hayEquipoAusente(contenedor)) {
      return;
    }

    var hayEmpate = local.value !== '' && visitante.value !== '' &&
                    Number(local.value) === Number(visitante.value);

    CAMPOS.forEach(function (selector) {
      // En las rondas que no admiten penales el campo directamente no existe:
      // el formulario lo saca y en su lugar deja el aviso de que decide la tabla.
      var bloque = contenedor.querySelector(selector);
      if (!bloque) return;
      bloque.hidden = !hayEmpate;

      // Si dejo de haber empate se limpia lo cargado: si no, quedaria guardada
      // una tanda en un partido que ya no termino igualado.
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

  // Lo llama default.js cuando se deja de ganar por default: ahi vuelve a haber
  // marcador, y los penales tienen que recalcularse con el.
  window.revisarPenales = actualizar;

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
