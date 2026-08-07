// Partido ganado por default: cuando uno de los dos equipos no se presenta, el
// rival gana 3-0 y no hay nada que cargar.
//
// El formulario se simplifica solo en vez de pedir el marcador y despues
// rechazarlo: si no se jugo, no hay goles que repartir ni goleadores que
// nombrar, y dejar esos campos a la vista invita a llenarlos.
//
// Este script NO crea ni borra nodos: el aviso ya viene en la plantilla y aca
// solo se muestra o se esconde. Crearlo desde el JS despertaba al observador del
// DOM en cada cambio y la pagina se trababa al usar el desplegable.
//
// Los eventos van en el documento porque el formulario llega despues, inyectado
// en el modal.
(function () {
  // El marcador y todo lo que dependa de el. Se ocultan juntos: ninguno tiene
  // sentido en un partido que no se jugo.
  var CAMPOS = [
    '[data-campo="goles_local"]',
    '[data-campo="goles_visitante"]',
    '[data-campo="ganador_penales"]',
    '[data-campo="penales_local"]',
    '[data-campo="penales_visitante"]',
  ];

  // Lo consulta penales.js: con un equipo ausente no se patean penales, asi que
  // no tiene que volver a mostrar los campos que este script escondio. Sin esto
  // los dos scripts se peleaban por el mismo `hidden`.
  window.hayEquipoAusente = function (contenedor) {
    var select = (contenedor || document).querySelector('[data-ausente]');
    return !!(select && select.value);
  };

  function actualizar(contenedor) {
    var select = contenedor.querySelector('[data-ausente]');
    if (!select) return;

    var hayAusente = !!select.value;

    CAMPOS.forEach(function (selector) {
      // En las rondas sin penales esos campos directamente no existen.
      var bloque = contenedor.querySelector(selector);
      if (bloque) bloque.hidden = hayAusente;
    });

    // Sin goles que cargar, las secciones de goleadores y asistentes sobran.
    contenedor.querySelectorAll('.seccion-actuaciones').forEach(function (seccion) {
      seccion.hidden = hayAusente;
    });

    avisar(contenedor, select, hayAusente);

    // Los penales dependen del marcador, que acaba de cambiar de visibilidad.
    // Se le avisa a penales.js para que recalcule con la regla nueva.
    if (!hayAusente && typeof window.revisarPenales === 'function') {
      window.revisarPenales(contenedor);
    }
  }

  // El aviso reemplaza a los campos que se ocultaron: sin el, el formulario se
  // queda casi vacio y no queda claro con que marcador se va a guardar.
  function avisar(contenedor, select, hayAusente) {
    var aviso = contenedor.querySelector('[data-aviso-default]');
    if (!aviso) return;

    aviso.hidden = !hayAusente;
    if (!hayAusente) return;

    // El ganador es la otra opcion del mismo desplegable: no hace falta pasar
    // los nombres por separado.
    var ganador = '';
    Array.prototype.forEach.call(select.options, function (opcion) {
      if (opcion.value && opcion.value !== select.value) ganador = opcion.textContent.trim();
    });

    // Solo se escribe si cambio: asignar el mismo texto igual reemplaza los
    // nodos hijos y despierta al observador para nada.
    var texto = ganador + ' gana 3-0 por default. No se cargan goleadores ni asistencias.';
    if (aviso.textContent !== texto) aviso.textContent = texto;
  }

  document.addEventListener('change', function (evento) {
    var campo = evento.target;
    if (!campo.hasAttribute || !campo.hasAttribute('data-ausente')) return;
    actualizar(campo.closest('form') || document);
  });

  // Al corregir un resultado el formulario ya llega con el ausente elegido, asi
  // que hay que evaluarlo apenas aparece. Se vigila solo la aparicion del
  // desplegable: este script ya no muta la lista de nodos, asi que no puede
  // despertarse a si mismo.
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
