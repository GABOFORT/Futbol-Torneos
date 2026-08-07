// Seguir equipos, guardado en el navegador del visitante.
//
// El visitante no tiene cuenta: el sistema no sabe quién es ni cuál es su
// equipo. Así que la lista de equipos que sigue se guarda en SU dispositivo con
// localStorage, igual que una página recuerda el modo oscuro. **No viaja al
// servidor y no se guarda nada de nadie**, que en un sitio con datos de menores
// es una ventaja y no una limitación.
//
// Lo que sí hace el servidor es dibujar la sección: el navegador le manda los
// ids y recibe HTML ya armado. Así el estilo, el formato de las fechas y el
// filtro por ligas públicas quedan en un solo lugar, en vez de repetirse acá.
//
// Se pierde si borra el caché o cambia de teléfono. Es el precio de no pedir
// registro, y está dicho en pantalla ("Guardado en este dispositivo").
(function () {
  var CLAVE = 'buho:equipos-seguidos';
  var MAXIMO = 20;

  function leer() {
    try {
      var crudo = JSON.parse(localStorage.getItem(CLAVE));
      return Array.isArray(crudo) ? crudo.filter(function (x) { return /^\d+$/.test(String(x)); }) : [];
    } catch (error) {
      // localStorage puede fallar en modo privado de algunos navegadores. Que
      // no ande el "seguir" no puede romper el resto de la página.
      return [];
    }
  }

  function guardar(ids) {
    try {
      localStorage.setItem(CLAVE, JSON.stringify(ids.slice(0, MAXIMO)));
    } catch (error) { /* sin espacio o sin permiso: se sigue sin guardar */ }
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

  // Pinta todas las estrellas de la página según lo guardado. Se llama al
  // cargar y cada vez que algo cambia, para que si el mismo equipo aparece dos
  // veces —en la lista y en la sección de arriba— las dos se actualicen.
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

  // Trae del servidor la sección "Tus equipos" ya dibujada.
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
        pintar();   // la sección trae sus propias estrellas
      })
      .catch(function () { caja.innerHTML = ''; });
  }

  document.addEventListener('click', function (evento) {
    var boton = evento.target.closest('[data-seguir]');
    if (!boton) return;
    evento.preventDefault();
    evento.stopPropagation();   // la estrella suele estar dentro de una tarjeta que es un enlace
    alternar(boton.getAttribute('data-seguir'));
    pintar();
    refrescar();
  });

  document.addEventListener('DOMContentLoaded', function () {
    pintar();
    refrescar();
  });
})();
