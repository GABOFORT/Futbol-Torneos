(function () {
  var MARCO = '[data-llaves-por-ronda]';
  var PROPUESTA = '#siembra-propuesta';
  var LADOS = ['local', 'visitante'];
  var ZONAS = { liguilla: 'Liguilla', mini: 'Mini-liguilla', sin: 'Sin liguilla' };

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

  function resaltarElegidos(marco) {
    var vistos = equiposElegidos(marco);
    marco.querySelectorAll('[data-equipo]').forEach(function (renglon) {
      renglon.classList.toggle('siembra-elegido', !!vistos[renglon.getAttribute('data-equipo')]);
    });
  }

  function refrescar(marco) {
    marcarRepetidos(marco);
    resaltarElegidos(marco);
  }

  function propuestaDe(marco) {
    var fuente = marco.querySelector(PROPUESTA);
    if (!fuente) return null;
    try {
      return JSON.parse(fuente.textContent);
    } catch (error) {
      return null;
    }
  }

  function aplicarPropuesta(marco) {
    var elegida = marco.querySelector('input[name="ronda"]:checked');
    var propuesta = propuestaDe(marco);
    if (!elegida || !propuesta || !propuesta[elegida.value]) return;
    propuesta[elegida.value].forEach(function (cruce, numero) {
      LADOS.forEach(function (lado, indice) {
        var campo = marco.querySelector('select[name="' + lado + '_' + numero + '"]');
        if (campo) campo.value = String(cruce[indice]);
      });
    });
  }

  function puestosDeLiguilla(marco, tabla, miniDesde) {
    var armada = parseInt(tabla.getAttribute('data-liguilla-armada'), 10);
    if (!isNaN(armada)) return armada;
    var elegida = marco.querySelector('input[name="ronda"]:checked');
    if (elegida) return (cuantasLlaves(marco)[elegida.value] || 0) * 2;
    return miniDesde ? miniDesde - 1 : 0;
  }

  function zonaDe(puesto, liguilla, miniDesde, miniHasta) {
    if (puesto <= liguilla) return 'liguilla';
    if (miniDesde && puesto >= miniDesde && puesto <= miniHasta) return 'mini';
    return 'sin';
  }

  function marcarZonas(marco) {
    var tabla = marco.querySelector('[data-zonas]');
    if (!tabla) return;
    tabla.querySelectorAll('.siembra-zona').forEach(function (rotulo) { rotulo.remove(); });

    var miniDesde = parseInt(tabla.getAttribute('data-mini-desde'), 10) || 0;
    var miniHasta = parseInt(tabla.getAttribute('data-mini-hasta'), 10) || 0;
    var liguilla = puestosDeLiguilla(marco, tabla, miniDesde);
    var elegida = marco.querySelector('input[name="ronda"]:checked');
    if (miniDesde && elegida && tabla.hasAttribute('data-liguilla-armada')) {
      miniHasta = miniDesde - 1 + (cuantasLlaves(marco)[elegida.value] || 0) * 2;
    }
    if (!liguilla && !miniDesde) return;

    var anterior = null;
    tabla.querySelectorAll('li[data-puesto]').forEach(function (renglon) {
      var zona = zonaDe(parseInt(renglon.getAttribute('data-puesto'), 10), liguilla, miniDesde, miniHasta);
      if (zona === anterior) return;
      var rotulo = document.createElement('li');
      rotulo.className = 'siembra-zona siembra-zona-' + zona;
      rotulo.setAttribute('aria-hidden', 'true');
      rotulo.textContent = ZONAS[zona];
      renglon.parentNode.insertBefore(rotulo, renglon);
      anterior = zona;
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
    marcarZonas(marco);
    refrescar(marco);
  }

  function actualizarTodos() {
    document.querySelectorAll(MARCO).forEach(actualizar);
  }

  document.addEventListener('change', function (evento) {
    var marco = evento.target.closest && evento.target.closest(MARCO);
    if (!marco) return;
    if (evento.target.name === 'ronda') {
      actualizar(marco);
      aplicarPropuesta(marco);
      refrescar(marco);
    } else if (evento.target.tagName === 'SELECT') {
      refrescar(marco);
    }
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