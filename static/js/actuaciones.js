

(function () {
  function form() {
    return document.querySelector('#modal-form[data-local]');
  }

  document.addEventListener('click', function (evento) {
    var agregar = evento.target.closest('[data-agregar]');
    if (agregar) {
      evento.preventDefault();
      agregarFila(agregar.getAttribute('data-agregar'));
      return;
    }
    var quitar = evento.target.closest('.quitar-fila');
    if (quitar) {
      evento.preventDefault();
      quitar.closest('.fila-actuacion').remove();
      recalcular();
    }
  });

  document.addEventListener('input', recalcular);
  document.addEventListener('change', recalcular);

  function agregarFila(seccion) {
    var plantilla = document.querySelector('#plantilla-fila');
    var contenedor = document.querySelector('[data-seccion="' + seccion + '"] [data-filas]');
    if (!plantilla || !contenedor) return;

    var fila = plantilla.content.cloneNode(true).querySelector('.fila-actuacion');
    fila.querySelectorAll('[name]').forEach(function (campo) {
      campo.name = campo.name.replace('__CAMPO__', seccion);
    });

    if (seccion !== 'gol') {
      fila.querySelectorAll('[data-solo-goles]').forEach(function (nodo) { nodo.remove(); });
    }

    contenedor.appendChild(fila);
    reindexar();
    fila.querySelector('select').focus();
  }

  function reindexar() {
    var filas = document.querySelectorAll('[data-seccion="gol"] .fila-actuacion');
    filas.forEach(function (fila, indice) {
      var check = fila.querySelector('input[name="gol_en_contra"]');
      if (check) check.value = indice;
      ajustarPenal(fila, check);
    });
  }

  function ajustarPenal(fila, check) {
    var etiqueta = fila.querySelector('.campo-penal');
    var penal = fila.querySelector('.penal-actuacion');
    if (!etiqueta || !penal) return;

    var cantidad = numero(fila.querySelector('.cantidad-actuacion'));
    var enContra = !!(check && check.checked);
    var tope = enContra ? 0 : Math.max(cantidad, 0);

    if (penal.max !== String(tope)) penal.max = tope;
    if (numero(penal) > tope) penal.value = tope;

    var ayuda = enContra
      ? 'Un gol en contra no puede ser de penal: al penal lo patea el rival.'
      : 'Cuántos de esos ' + cantidad + ' gol(es) fueron de penal. Máximo ' + tope +
        '. Si necesitas más, súbele los goles a esta fila o agrega otro goleador.';
    if (penal.title !== ayuda) penal.title = ayuda;

    var tapa = fila.querySelector('[data-penal-tope]');
    if (tapa) {
      var leyenda = (!enContra && cantidad > 1) ? 'de ' + tope : '';
      if (tapa.textContent !== leyenda) tapa.textContent = leyenda;
    }

    etiqueta.classList.toggle('campo-penal-bloqueado', enContra);
    penal.readOnly = enContra;

    etiqueta.toggleAttribute('data-activo', !enContra && numero(penal) > 0);
  }

  var recalculando = false;

  function recalcular() {
    if (recalculando) return;
    var f = form();
    if (!f) return;
    recalculando = true;
    try {
      actualizarContadores(f);
    } finally {
      recalculando = false;
    }
  }

  function actualizarContadores(f) {
    reindexar();

    var local = f.getAttribute('data-local');
    var visitante = f.getAttribute('data-visitante');
    var marcador = {};
    marcador[local] = numero(f.querySelector('[name="goles_local"]'));
    marcador[visitante] = numero(f.querySelector('[name="goles_visitante"]'));

    document.querySelectorAll('[data-seccion]').forEach(function (seccion) {
      var asignado = {};
      asignado[local] = 0;
      asignado[visitante] = 0;

      seccion.querySelectorAll('.fila-actuacion').forEach(function (fila) {
        var select = fila.querySelector('select');
        var opcion = select.selectedOptions[0];
        if (!opcion || !opcion.value) return;
        var equipo = opcion.getAttribute('data-equipo');
        var cantidad = numero(fila.querySelector('.cantidad-actuacion'));
        var enContra = fila.querySelector('input[name="gol_en_contra"]');

        if (enContra && enContra.checked) equipo = (equipo === local) ? visitante : local;
        asignado[equipo] += cantidad;
      });

      seccion.querySelectorAll('[data-contador-equipo]').forEach(function (contador) {
        var equipo = contador.getAttribute('data-contador-equipo');
        var meta = marcador[equipo];

        escribir(contador.querySelector('b'), asignado[equipo]);
        escribir(contador.querySelector('.meta'), meta);

        var ok = seccion.getAttribute('data-seccion') === 'gol'
          ? asignado[equipo] === meta
          : asignado[equipo] <= meta;
        contador.classList.toggle('contador-ok', ok && meta > 0);
        contador.classList.toggle('contador-mal', !ok);
      });
    });
  }

  function escribir(nodo, valor) {
    if (nodo && nodo.textContent !== String(valor)) nodo.textContent = valor;
  }

  function numero(campo) {
    var valor = campo ? parseInt(campo.value, 10) : 0;
    return isNaN(valor) ? 0 : valor;
  }

  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 && (nodo.matches('[data-seccion]') || nodo.querySelector('[data-seccion]'));
      });
    });
    if (aparecio) recalcular();
  }).observe(document.body, { childList: true, subtree: true });
})();
