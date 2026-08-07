// Goles y asistencias en el formulario de resultado: agregar y quitar filas, y
// un contador que compara lo asignado contra el marcador.
//
// Los eventos van en el documento porque el formulario llega despues, inyectado
// en el modal.
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
    // "En contra" y "de penal" solo aplican a goles; en asistencias no tienen sentido.
    if (seccion !== 'gol') {
      fila.querySelectorAll('[data-solo-goles]').forEach(function (nodo) { nodo.remove(); });
    }

    contenedor.appendChild(fila);
    reindexar();
    fila.querySelector('select').focus();
  }

  // El checkbox viaja con el numero de su fila como valor: es lo que permite al
  // servidor saber cual de los goleadores fue en contra.
  function reindexar() {
    var filas = document.querySelectorAll('[data-seccion="gol"] .fila-actuacion');
    filas.forEach(function (fila, indice) {
      var check = fila.querySelector('input[name="gol_en_contra"]');
      if (check) check.value = indice;
      ajustarPenal(fila, check);
    });
  }

  // El campo "de penal" no puede pasarse de los goles de su fila, y no aplica a
  // un gol en contra: al penal lo patea el rival.
  //
  // Se bloquea con readonly y no con disabled a proposito: un campo disabled no
  // viaja en el POST, y el servidor empareja estas listas por indice, asi que
  // faltando uno se le asignaria el penal a otro goleador.
  function ajustarPenal(fila, check) {
    var etiqueta = fila.querySelector('.campo-penal');
    var penal = fila.querySelector('.penal-actuacion');
    if (!etiqueta || !penal) return;

    var cantidad = numero(fila.querySelector('.cantidad-actuacion'));
    var enContra = !!(check && check.checked);
    var tope = enContra ? 0 : Math.max(cantidad, 0);

    if (penal.max !== String(tope)) penal.max = tope;
    if (numero(penal) > tope) penal.value = tope;

    // El tope se explica en el campo: antes recortaba el numero en silencio y
    // parecia que el formulario no dejaba cargar mas de N penales en todo el
    // partido, cuando el limite es por goleador. Para mas penales hay que subir
    // los goles de esa fila, o agregar otra fila con otro goleador.
    var ayuda = enContra
      ? 'Un gol en contra no puede ser de penal: al penal lo patea el rival.'
      : 'Cuántos de esos ' + cantidad + ' gol(es) fueron de penal. Máximo ' + tope +
        '. Si necesitas más, súbele los goles a esta fila o agrega otro goleador.';
    if (penal.title !== ayuda) penal.title = ayuda;

    // "de 3" al lado del campo. Con un solo gol no se muestra: el tope es obvio
    // y el renglon ya va cargado de controles.
    var tapa = fila.querySelector('[data-penal-tope]');
    if (tapa) {
      var leyenda = (!enContra && cantidad > 1) ? 'de ' + tope : '';
      if (tapa.textContent !== leyenda) tapa.textContent = leyenda;
    }

    etiqueta.classList.toggle('campo-penal-bloqueado', enContra);
    penal.readOnly = enContra;
    // Marca visual: el campo se resalta solo cuando hay un penal cargado, para
    // que no compita con el resto de la fila cuando esta en cero.
    etiqueta.toggleAttribute('data-activo', !enContra && numero(penal) > 0);
  }

  // El observador vigila el DOM y recalcular escribe en el DOM, asi que sin este
  // candado se llamarian entre si sin parar y la pestana se congela.
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
        // Un gol en contra suma al marcador del rival, no al del equipo del jugador.
        if (enContra && enContra.checked) equipo = (equipo === local) ? visitante : local;
        asignado[equipo] += cantidad;
      });

      seccion.querySelectorAll('[data-contador-equipo]').forEach(function (contador) {
        var equipo = contador.getAttribute('data-contador-equipo');
        var meta = marcador[equipo];
        // Solo se escribe si cambio: escribir el mismo valor igual muta el DOM
        // y despierta al observador para nada.
        escribir(contador.querySelector('b'), asignado[equipo]);
        escribir(contador.querySelector('.meta'), meta);
        // Las asistencias no tienen que igualar al marcador, solo no pasarlo.
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

  // El formulario llega despues, cuando se abre el modal. Se vigila solo la
  // aparicion del formulario y no cualquier cambio, para no reaccionar a lo que
  // el propio script escribe.
  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 && (nodo.matches('[data-seccion]') || nodo.querySelector('[data-seccion]'));
      });
    });
    if (aparecio) recalcular();
  }).observe(document.body, { childList: true, subtree: true });
})();
