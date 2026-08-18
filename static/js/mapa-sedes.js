

(function () {
  var ZOOM_MAXIMO = 15;

  document.addEventListener('DOMContentLoaded', function () {
    var caja = document.getElementById('mapa-sedes');
    if (!caja || typeof L === 'undefined') return;

    var fichas = Array.prototype.slice.call(document.querySelectorAll('.sede'));
    if (!fichas.length) return;

    var mapa = L.map(caja, { scrollWheelZoom: false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(mapa);

    var puntos = [];
    var pines = {};

    fichas.forEach(function (ficha, indice) {
      var lat = parseFloat(ficha.getAttribute('data-lat'));
      var lon = parseFloat(ficha.getAttribute('data-lon'));
      if (isNaN(lat) || isNaN(lon)) return;

      var contenido = document.createElement('div');
      var nombre = document.createElement('strong');
      nombre.textContent = ficha.getAttribute('data-nombre');
      contenido.appendChild(nombre);
      contenido.appendChild(document.createElement('br'));
      contenido.appendChild(document.createTextNode(ficha.getAttribute('data-liga')));

      var pin = L.marker([lat, lon]).addTo(mapa);
      pin.bindPopup(contenido);
      puntos.push([lat, lon]);
      pines[indice] = pin;

      ficha.addEventListener('click', function (evento) {

        if (evento.target.closest('a')) return;
        mapa.setView([lat, lon], ZOOM_MAXIMO + 1);
        pin.openPopup();
        caja.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    });

    if (!puntos.length) return;

    mapa.fitBounds(L.latLngBounds(puntos).pad(0.15), { maxZoom: ZOOM_MAXIMO });
  });
})();
