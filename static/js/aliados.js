(function () {
  var ZOOM_PUNTO = 16;
  var ZOOM_ZONA = 15;
  var ZOOM_BUSQUEDA = 17;

  function texto(elemento, mensaje) {
    if (elemento) elemento.textContent = mensaje || '';
  }

  function armar(caja) {
    if (caja.dataset.listo) return;
    caja.dataset.listo = '1';

    var formulario = caja.closest('form') || document;
    var campoLat = formulario.querySelector('[name="latitud"]');
    var campoLng = formulario.querySelector('[name="longitud"]');
    var campoDireccion = caja.querySelector('[name="direccion"]');
    var campoBuscar = caja.querySelector('[data-aliado-buscar]');
    var estado = caja.querySelector('[data-aliado-estado]');
    var quitar = caja.querySelector('[data-aliado-quitar]');
    var contenedor = caja.querySelector('[data-aliado-mapa]');
    if (!campoLat || !campoLng || !contenedor) return;

    var marcado = campoLat.value !== '' && campoLng.value !== '';
    var centro = marcado
      ? [parseFloat(campoLat.value), parseFloat(campoLng.value)]
      : [parseFloat(caja.dataset.centroLat), parseFloat(caja.dataset.centroLng)];

    var mapa = L.map(contenedor).setView(centro, marcado ? ZOOM_PUNTO : ZOOM_ZONA);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© colaboradores de OpenStreetMap',
    }).addTo(mapa);

    var pin = null;

    function guardar(punto) {
      campoLat.value = punto.lat.toFixed(6);
      campoLng.value = punto.lng.toFixed(6);
      quitar.hidden = false;
    }

    function completarDireccion(punto) {
      if (campoDireccion.dataset.tocado) return;
      texto(estado, 'Buscando la dirección del punto…');
      fetch('https://nominatim.openstreetmap.org/reverse?format=json&zoom=18&lat=' +
            punto.lat.toFixed(6) + '&lon=' + punto.lng.toFixed(6))
        .then(function (r) { return r.json(); })
        .then(function (datos) {
          texto(estado, '');
          if (datos && datos.display_name && !campoDireccion.dataset.tocado) {
            campoDireccion.value = datos.display_name;
          }
        })
        .catch(function () { texto(estado, ''); });
    }

    function poner(punto, buscarDireccion) {
      if (pin) {
        pin.setLatLng(punto);
      } else {
        pin = L.marker(punto, { draggable: true }).addTo(mapa);
        pin.on('dragend', function () {
          var movido = pin.getLatLng();
          guardar(movido);
          completarDireccion(movido);
        });
      }
      guardar(L.latLng(punto));
      if (buscarDireccion) completarDireccion(L.latLng(punto));
    }

    if (marcado) poner(centro, false);
    quitar.hidden = !marcado;

    mapa.on('click', function (evento) { poner(evento.latlng, true); });

    quitar.addEventListener('click', function () {
      if (pin) { mapa.removeLayer(pin); pin = null; }
      campoLat.value = '';
      campoLng.value = '';
      quitar.hidden = true;
      texto(estado, 'Sin punto en el mapa. Se usará la dirección escrita.');
    });

    campoDireccion.addEventListener('input', function () {
      campoDireccion.dataset.tocado = '1';
    });

    function buscar() {
      var consulta = (campoBuscar.value || '').trim();
      if (!consulta) return;
      texto(estado, 'Buscando…');
      fetch('https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' +
            encodeURIComponent(consulta))
        .then(function (r) { return r.json(); })
        .then(function (resultados) {
          if (!resultados.length) {
            texto(estado, 'No se encontró ese lugar. Prueba con la calle o la colonia.');
            return;
          }
          var punto = L.latLng(parseFloat(resultados[0].lat), parseFloat(resultados[0].lon));
          mapa.setView(punto, ZOOM_BUSQUEDA);
          poner(punto, false);
          if (!campoDireccion.dataset.tocado) {
            campoDireccion.value = resultados[0].display_name || '';
          }
          texto(estado, 'Zona encontrada. Arrastra el pin hasta el negocio.');
        })
        .catch(function () {
          texto(estado, 'No se pudo buscar. Revisa la conexión a internet.');
        });
    }

    caja.querySelector('[data-aliado-buscar-btn]').addEventListener('click', buscar);
    campoBuscar.addEventListener('keydown', function (evento) {
      if (evento.key !== 'Enter') return;
      evento.preventDefault();
      buscar();
    });

    setTimeout(function () { mapa.invalidateSize(); }, 60);
  }

  window.initAliado = function (raiz) {
    if (typeof L === 'undefined') return;
    (raiz || document).querySelectorAll('[data-selector-aliado]').forEach(armar);
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.initAliado(document);
  });
})();
