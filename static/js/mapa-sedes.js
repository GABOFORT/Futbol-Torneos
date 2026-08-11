// El mapa de todas las canchas, en la pantalla pública de sedes.
//
// Los datos NO vienen en un JSON aparte: se leen del listado que ya está en la
// página, donde cada cancha trae su lat/lon en atributos. Así hay una sola
// fuente —si el listado dice una cosa y el mapa otra, no puede pasar— y la
// página sigue sirviendo con el JS apagado: la lista tiene el enlace a Google
// Maps de cada cancha.
//
// Leaflet se carga sólo acá (ver el bloque `cabecera_extra` de sedes.html), no
// en base.html.
(function () {
  var ZOOM_MAXIMO = 15;   // con una sola cancha, no acercarse tanto que se pierda el contexto

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

      // Nombre y liga van como nodos de texto, no como string armado a mano:
      // "nombre" lo escribe el Admin de Liga y viaja de vuelta al DOM ya
      // decodificado (getAttribute deshace el escape que hizo el template),
      // asi que si se concatenara como HTML, algo como <img onerror=...>
      // se ejecutaria en el navegador de cualquiera que abra el popup.
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

      // Tocar la tarjeta lleva el mapa a esa cancha: con 87 pines encontrar el
      // que uno busca a ojo es imposible.
      ficha.addEventListener('click', function (evento) {
        // El enlace "Cómo llegar" tiene que seguir abriendo Google Maps.
        if (evento.target.closest('a')) return;
        mapa.setView([lat, lon], ZOOM_MAXIMO + 1);
        pin.openPopup();
        caja.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    });

    if (!puntos.length) return;
    // Encuadre que entre todas las canchas. Con una sola, `fitBounds` se
    // acercaría al máximo, por eso el tope.
    mapa.fitBounds(L.latLngBounds(puntos).pad(0.15), { maxZoom: ZOOM_MAXIMO });
  });
})();
