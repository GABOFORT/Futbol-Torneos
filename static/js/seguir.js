

(function () {
  var CLAVE = 'buho:equipos-seguidos';
  var MAXIMO = 20;

  function leer() {
    try {
      var crudo = JSON.parse(localStorage.getItem(CLAVE));
      return Array.isArray(crudo) ? crudo.filter(function (x) { return /^\d+$/.test(String(x)); }) : [];
    } catch (error) {

      return [];
    }
  }

  function guardar(ids) {
    try {
      localStorage.setItem(CLAVE, JSON.stringify(ids.slice(0, MAXIMO)));
    } catch (error) {  }
  }

  function sigue(id) {
    return leer().indexOf(String(id)) !== -1;
  }

  function alternar(id) {
    var ids = leer();
    var lugar = ids.indexOf(String(id));
    if (lugar === -1) {
      ids.push(String(id));
    } else {
      ids.splice(lugar, 1);
    }
    guardar(ids);
    return lugar === -1;
  }

  function pintar() {
    document.querySelectorAll('[data-seguir]').forEach(function (boton) {
      var activo = sigue(boton.getAttribute('data-seguir'));
      boton.classList.toggle('seguido', activo);
      boton.setAttribute('aria-pressed', activo ? 'true' : 'false');
      var etiqueta = boton.getAttribute('data-nombre');
      if (etiqueta) {
        boton.setAttribute('title', (activo ? 'Dejar de seguir a ' : 'Seguir a ') + etiqueta);
      }
    });
  }

  function refrescar() {
    var caja = document.getElementById('mis-equipos');
    if (!caja) return;

    var ids = leer();
    if (!ids.length) {
      caja.innerHTML = '';
      return;
    }
    fetch('/mis-equipos/?ids=' + encodeURIComponent(ids.join(',')), { cache: 'no-store' })
      .then(function (respuesta) { return respuesta.text(); })
      .then(function (html) {
        caja.innerHTML = html;
        pintar();
      })
      .catch(function () { caja.innerHTML = ''; });
  }

  document.addEventListener('click', function (evento) {
    var boton = evento.target.closest('[data-seguir]');
    if (!boton) return;
    evento.preventDefault();
    evento.stopPropagation();
    alternar(boton.getAttribute('data-seguir'));
    pintar();
    refrescar();
  });

  document.addEventListener('DOMContentLoaded', function () {
    pintar();
    refrescar();
  });
})();
