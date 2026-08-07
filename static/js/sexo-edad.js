// El limite de edad depende del sexo del jugador.
//
// Las mujeres entran con un año mas que la categoria: en U17 juega una jugadora
// de 18. Como el sexo se elige en el mismo formulario que la fecha de
// nacimiento, el tope del selector no se puede calcular una sola vez al abrir:
// tiene que correrse al cambiar la opcion.
//
// Los dos topes ya vienen puestos en el campo de fecha (data-min-masculino y
// data-min-femenino), calculados por el servidor. Aca solo se elige cual de los
// dos aplica: la regla de cuantos años son vive en Categoria, no en el JS.
//
// Esto es comodidad, no seguridad. El `clean` del formulario revalida la edad
// contra el sexo que llego, porque un POST armado a mano ignora cualquier tope
// que ponga esta pagina.
//
// Este script NO crea ni borra nodos: crear nodos desde el JS despierta al
// observador del DOM y termina trabando la pagina.
//
// Los eventos van en el documento porque el formulario llega despues, inyectado
// en el modal.
(function () {
  function actualizar(contenedor) {
    var fecha = contenedor.querySelector('[data-min-masculino]');
    if (!fecha) return;

    var elegido = contenedor.querySelector('[data-sexo]:checked');
    // Sin nada marcado se usa el limite estricto: ante la duda no se regala el
    // año de tolerancia.
    var sexo = elegido ? elegido.value : 'masculino';

    var minimo = fecha.getAttribute('data-min-' + sexo);
    if (minimo && fecha.getAttribute('min') !== minimo) {
      fecha.setAttribute('min', minimo);
    }
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute || !campo.hasAttribute('data-sexo')) return;
    actualizar(campo.closest('form') || document);
  });

  // Al editar un jugador el formulario ya llega con su sexo cargado, asi que hay
  // que evaluarlo apenas aparece. Se vigila solo la aparicion del campo de
  // fecha: este script no muta la lista de nodos, asi que no puede despertarse
  // a si mismo.
  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 &&
          (nodo.matches('[data-min-masculino]') || nodo.querySelector('[data-min-masculino]'));
      });
    });
    if (aparecio) document.querySelectorAll('form').forEach(actualizar);
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(actualizar);
  });
})();
