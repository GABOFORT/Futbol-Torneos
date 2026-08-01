// Mapa para elegir y marcar la cancha donde se juega un partido.
//
// Se llama con initSede(contenedor) despues de inyectar el modal, igual que
// initFormulario. Usa Leaflet con mosaicos de OpenStreetMap: no necesita llave
// de API ni cuenta de nadie.
//
// El mapa esta siempre a la vista y tiene dos modos:
//   ver     - hay una cancha elegida: se muestra con el pin fijo y sus datos
//             debajo, sin que haya que pulsar nada para verla.
//   marcar  - no hay cancha, o se pidio cambiarla: el pin se arrastra y salen
//             el buscador y los campos para darla de alta.
//
// El buscador va contra Nominatim, el geocodificador de OpenStreetMap. Su
// politica de uso pide como maximo una consulta por segundo, asi que solo se
// consulta al apretar Buscar y al soltar el pin, nunca mientras se arrastra.
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

  // El token viaja en el formulario que envuelve a este selector.
  function csrfDe(caja) {
    var campo = (caja.closest('form') || document).querySelector('[name="csrfmiddlewaretoken"]');
    return campo ? campo.value : '';
  }

  // Los datos de la cancha elegida salen de su propia <option>, que los trae en
  // data-lat, data-lng y data-direccion (los pone SelectDeSedes, en forms.py).
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
    // Tocar el mapa mueve el pin: en el celular arrastrar es incomodo.
    mapa.on('click', function (evento) {
      if (marcar.hidden) return;  // en modo ver el pin no se toca
      pin.setLatLng(evento.latlng);
      completarDireccion();
    });

    function coordenadas() {
      var punto = pin.getLatLng();
      return { lat: punto.lat.toFixed(6), lng: punto.lng.toFixed(6) };
    }

    // Nominatim devuelve la direccion del punto donde quedo el pin. Si falla no
    // se avisa nada: la direccion es opcional y se puede escribir a mano.
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
      // Leaflet mide mal el contenedor si estaba oculto al crearse.
      mapa.invalidateSize();
    }

    function modoMarcar() {
      resumen.hidden = true;
      marcar.hidden = false;
      mostrarError(error, '');
      pin.dragging.enable();
      // Cancelar solo si hay una cancha a la que volver.
      botonCancelar.hidden = !select.value;
      mapa.invalidateSize();
      campoNombre.focus();
    }

    // Lo que corresponde segun lo que este elegido en el desplegable.
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
          // La cancha nueva entra al desplegable ya elegida, con sus
          // coordenadas puestas igual que las que vinieron del servidor: asi el
          // modo ver la puede mostrar sin recargar la pagina.
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

    // Elegir otra cancha del desplegable mueve el mapa a esa cancha.
    select.addEventListener('change', refrescar);

    // Si la direccion se escribio a mano, el reverse de Nominatim no la pisa:
    // lo que escribio una persona vale mas que lo que adivina el mapa.
    campoDireccion.addEventListener('input', function () {
      campoDireccion.dataset.tocado = '1';
    });

    campoBuscar.addEventListener('keydown', function (evento) {
      if (evento.key !== 'Enter') return;
      // Sin esto Enter en la busqueda envia el formulario del partido entero.
      evento.preventDefault();
      buscar();
    });

    refrescar();
  }

  window.initSede = function (raiz) {
    raiz = raiz || document;
    if (typeof L === 'undefined') return;  // la pantalla no cargo Leaflet
    raiz.querySelectorAll('[data-selector-sede]').forEach(armar);
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.initSede(document);
  });
})();
