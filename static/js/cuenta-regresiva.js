

(function () {
  var UN_MINUTO = 60000;

  function texto(faltan) {
    if (faltan <= 0) return 'Se está jugando';

    var minutos = Math.floor(faltan / UN_MINUTO);
    var dias = Math.floor(minutos / 1440);
    var horas = Math.floor((minutos % 1440) / 60);
    var resto = minutos % 60;

    if (dias > 0) return 'Faltan ' + dias + 'd ' + horas + 'h';
    if (horas > 0) return 'Faltan ' + horas + 'h ' + resto + 'min';
    return 'Faltan ' + resto + ' min';
  }

  function actualizar() {
    var quedan = false;
    document.querySelectorAll('[data-cuenta]').forEach(function (nodo) {
      var cuando = new Date(nodo.getAttribute('data-cuenta'));
      if (isNaN(cuando)) return;
      var nuevo = texto(cuando - new Date());

      if (nodo.textContent.trim() !== nuevo) nodo.textContent = nuevo;
      quedan = true;
    });
    return quedan;
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!actualizar()) return;

    setInterval(actualizar, 30000);
  });
})();
