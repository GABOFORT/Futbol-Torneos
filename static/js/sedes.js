

(function () {
  var ZOOM_VER = 16;
  var ZOOM_MARCAR = 15;
  var ZOOM_AL_BUSCAR = 17;

  function texto(elemento, mensaje) {
    if (elemento) elemento.textContent = mensaje || '';
  }

  function mostrarError(caja, mensaje) {
    if (!caja) return;
    caja.textContent = mensaje || '';
    caja.hidden = !mensaje;
  }

  function csrfDe(caja) {
    var campo = (caja.closest('form') || document).querySelector('[name="csrfmiddlewaretoken"]');
    return campo ? campo.value : '';
  }

  function sedeElegida(select) {
    var opcion = select.selectedOptions[0];
    if (!opcion || !opcion.value || !opcion.dataset.lat) return null;
    return {
      nombre: opcion.textContent.trim(),
      direccion: opcion.dataset.direccion || '',
      lat: parseFloat(opcion.dataset.lat),
      lng: parseFloat(opcion.dataset.lng),
    };
  }

  function armar(caja) {
    if (caja.dataset.sedeBound) return;
    caja.dataset.sedeBound = '1';

    var select = caja.querySelector('select');
    var contenedorMapa = caja.querySelector('[data-sede-mapa]');

    var resumen = caja.querySelector('[data-sede-resumen]');
    var resumenNombre = caja.querySelector('[data-sede-resumen-nombre]');
    var resumenDireccion = caja.querySelector('[data-sede-resumen-direccion]');

    var marcar = caja.querySelector('[data-sede-marcar]');
    var campoNombre = caja.querySelector('[data-sede-nombre]');
    var campoDireccion = caja.querySelector('[data-sede-direccion]');
    var campoBuscar = caja.querySelector('[data-sede-buscar]');
    var botonCancelar = caja.querySelector('[data-sede-cancelar]');
    var estado = caja.querySelector('[data-sede-estado]');
    var error = caja.querySelector('[data-sede-error]');

    var mapa = L.map(contenedorMapa).setView(
      [parseFloat(caja.dataset.centroLat), parseFloat(caja.dataset.centroLng)],
      ZOOM_MARCAR
    );
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© colaboradores de OpenStreetMap',
    }).addTo(mapa);

    var pin = L.marker(mapa.getCenter(), { draggable: true }).addTo(mapa);
    pin.on('dragend', completarDireccion);

    mapa.on('click', function (evento) {
      if (marcar.hidden) return;
      pin.setLatLng(evento.latlng);
      completarDireccion();
    });

    function coordenadas() {
      var punto = pin.getLatLng();
      return { lat: punto.lat.toFixed(6), lng: punto.lng.toFixed(6) };
    }

    function completarDireccion() {
      var punto = coordenadas();
      texto(estado, 'Buscando la dirección del punto…');
      fetch('https://nominatim.openstreetmap.org/reverse?format=json&zoom=18&lat=' +
            punto.lat + '&lon=' + punto.lng)
        .then(function (r) { return r.json(); })
        .then(function (datos) {
          texto(estado, '');
          if (datos && datos.display_name && !campoDireccion.dataset.tocado) {
            campoDireccion.value = datos.display_name;
          }
        })
        .catch(function () { texto(estado, ''); });
    }

    function modoVer(sede) {
      resumen.hidden = false;
      marcar.hidden = true;
      mostrarError(error, '');
      texto(estado, '');
      texto(resumenNombre, '' + sede.nombre);
      texto(resumenDireccion, sede.direccion || 'Sin dirección cargada');
      pin.setLatLng([sede.lat, sede.lng]);
      pin.dragging.disable();
      mapa.setView([sede.lat, sede.lng], ZOOM_VER);

      mapa.invalidateSize();
    }

    function modoMarcar() {
      resumen.hidden = true;
      marcar.hidden = false;
      mostrarError(error, '');
      pin.dragging.enable();

      botonCancelar.hidden = !select.value;
      mapa.invalidateSize();
      campoNombre.focus();
    }

    function refrescar() {
      var sede = sedeElegida(select);
      if (sede) {
        modoVer(sede);
      } else {
        modoMarcar();
      }
    }

    function buscar() {
      var consulta = (campoBuscar.value || '').trim();
      if (!consulta) return;
      texto(estado, 'Buscando…');
      fetch('https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' +
            encodeURIComponent(consulta))
        .then(function (r) { return r.json(); })
        .then(function (resultados) {
          if (!resultados.length) {
            texto(estado, 'No se encontró ese lugar. Prueba con la calle o la colonia, y después mueve el pin.');
            return;
          }
          texto(estado, 'Zona encontrada. Ahora arrastra el pin hasta la cancha.');
          var punto = [parseFloat(resultados[0].lat), parseFloat(resultados[0].lon)];
          mapa.setView(punto, ZOOM_AL_BUSCAR);
          pin.setLatLng(punto);
          if (!campoDireccion.dataset.tocado) {
            campoDireccion.value = resultados[0].display_name || '';
          }
        })
        .catch(function () {
          texto(estado, 'No se pudo buscar. Revisa la conexión a internet.');
        });
    }

    function guardar(boton) {
      var nombre = (campoNombre.value || '').trim();
      if (!nombre) {
        mostrarError(error, 'Ponle un nombre a la cancha para poder reconocerla después.');
        campoNombre.focus();
        return;
      }
      var punto = coordenadas();
      var datos = new FormData();
      datos.append('nombre', nombre);
      datos.append('direccion', (campoDireccion.value || '').trim());
      datos.append('latitud', punto.lat);
      datos.append('longitud', punto.lng);
      datos.append('csrfmiddlewaretoken', csrfDe(caja));

      boton.disabled = true;
      mostrarError(error, '');
      fetch(caja.dataset.urlGuardar, { method: 'POST', body: datos, cache: 'no-store' })
        .then(function (r) { return r.json(); })
        .then(function (respuesta) {
          boton.disabled = false;
          if (!respuesta.success) {
            mostrarError(error, respuesta.error || 'No se pudo guardar la cancha.');
            return;
          }

          var opcion = document.createElement('option');
          opcion.value = respuesta.id;
          opcion.textContent = respuesta.nombre;
          opcion.dataset.lat = punto.lat;
          opcion.dataset.lng = punto.lng;
          opcion.dataset.direccion = (campoDireccion.value || '').trim();
          select.appendChild(opcion);
          select.value = respuesta.id;
          campoNombre.value = '';
          campoDireccion.value = '';
          delete campoDireccion.dataset.tocado;
          refrescar();
        })
        .catch(function () {
          boton.disabled = false;
          mostrarError(error, 'No se pudo guardar la cancha. Revisa la conexión.');
        });
    }

    caja.querySelector('[data-sede-abrir]').addEventListener('click', modoMarcar);
    botonCancelar.addEventListener('click', refrescar);
    caja.querySelector('[data-sede-guardar]').addEventListener('click', function () {
      guardar(this);
    });
    caja.querySelector('[data-sede-buscar-btn]').addEventListener('click', buscar);

    select.addEventListener('change', refrescar);

    campoDireccion.addEventListener('input', function () {
      campoDireccion.dataset.tocado = '1';
    });

    campoBuscar.addEventListener('keydown', function (evento) {
      if (evento.key !== 'Enter') return;

      evento.preventDefault();
      buscar();
    });

    refrescar();
  }

  window.initSede = function (raiz) {
    raiz = raiz || document;
    if (typeof L === 'undefined') return;
    raiz.querySelectorAll('[data-selector-sede]').forEach(armar);
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.initSede(document);
  });
})();
