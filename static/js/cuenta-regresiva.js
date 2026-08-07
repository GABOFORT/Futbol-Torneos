// Cuenta regresiva hasta el proximo partido destacado de la portada.
//
// La fecha viaja en el atributo `data-cuenta` en formato ISO, y el HTML ya
// llega con la fecha y la hora escritas. Si este script no corre —JS apagado,
// error de red— la tarjeta sigue diciendo cuando se juega: lo que se pierde es
// el conteo, no el dato.
//
// Se calcula contra el reloj del visitante, asi que un celular con la hora mal
// puesta va a ver un numero raro. Es preferible a no mostrar nada: la fecha
// exacta esta en la ficha del partido.
(function () {
  var UN_MINUTO = 60000;

  function texto(faltan) {
    if (faltan <= 0) return 'Se está jugando';

    var minutos = Math.floor(faltan / UN_MINUTO);
    var dias = Math.floor(minutos / 1440);
    var horas = Math.floor((minutos % 1440) / 60);
    var resto = minutos % 60;

    // Con mas de un dia por delante los minutos no le importan a nadie.
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
      // Solo se escribe si cambio: asignar el mismo texto igual reemplaza el
      // nodo hijo y despierta a los observadores del DOM para nada.
      if (nodo.textContent.trim() !== nuevo) nodo.textContent = nuevo;
      quedan = true;
    });
    return quedan;
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!actualizar()) return;   // no hay ninguna cuenta en esta pagina
    // Cada medio minuto alcanza: lo mas fino que se muestra son minutos.
    setInterval(actualizar, 30000);
  });
})();
