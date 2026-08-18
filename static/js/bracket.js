

(function () {
  var MARCO = '[data-bracket-marco]';

  function revisar(marco) {
    var desborda = marco.scrollWidth > marco.clientWidth + 1;
    if (desborda) marco.setAttribute('data-desplazable', '');
    else marco.removeAttribute('data-desplazable');
  }

  function revisarTodos() {
    document.querySelectorAll(MARCO).forEach(revisar);
  }

  function centrar(marco) {
    if (marco.scrollWidth > marco.clientWidth) {
      marco.scrollLeft = (marco.scrollWidth - marco.clientWidth) / 2;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll(MARCO).forEach(function (marco) {
      revisar(marco);
      centrar(marco);
    });
  });

  window.addEventListener('resize', revisarTodos);
})();
