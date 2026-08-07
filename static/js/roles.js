// El limite de ligas solo existe para el Administrador de Liga.
//
// Un Administrador General no tiene cuota (crea las que quiera) y un Entrenador
// no crea ligas: para esos dos el campo desaparece en vez de quedar pidiendo un
// numero que no se va a usar.
//
// Esconder el campo es solo la mitad: el `clean` del formulario repite la regla
// en el servidor, porque un POST armado a mano igual puede mandarlo.
//
// Este script NO crea ni borra nodos, solo alterna `hidden`: crear nodos desde
// el JS despierta al observador del DOM y termina trabando la pagina.
(function () {
  function actualizar(contenedor) {
    var rol = contenedor.querySelector('[data-rol]');
    if (!rol) return;

    contenedor.querySelectorAll('[data-solo-rol]').forEach(function (campo) {
      var bloque = campo.closest('[data-campo]');
      if (!bloque) return;
      bloque.hidden = campo.getAttribute('data-solo-rol') !== rol.value;
    });
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute || !campo.hasAttribute('data-rol')) return;
    actualizar(campo.closest('form') || document);
  });

  // Al editar un usuario el formulario ya llega con su rol cargado, asi que hay
  // que evaluarlo apenas aparece. Se vigila solo la aparicion del selector de rol.
  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 &&
          (nodo.matches('[data-rol]') || nodo.querySelector('[data-rol]'));
      });
    });
    if (aparecio) document.querySelectorAll('form').forEach(actualizar);
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(actualizar);
  });
})();
