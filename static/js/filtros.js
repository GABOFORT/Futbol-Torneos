

(function () {
  var ESPERA_MS = 300;
  var temporizador = null;
  var enCurso = null;

  function init() {
    var form = document.querySelector('[data-filtros]');
    var resultados = document.querySelector('[data-resultados]');
    if (!resultados) return;

    if (form) {
      form.addEventListener('submit', function (evento) {

        evento.preventDefault();
        traer(urlDelFormulario(form), form, resultados);
      });

      form.querySelectorAll('input[type="search"]').forEach(function (campo) {
        campo.addEventListener('input', function () {
          clearTimeout(temporizador);

          temporizador = setTimeout(function () {
            traer(urlDelFormulario(form), form, resultados);
          }, ESPERA_MS);
        });
      });

      form.addEventListener('change', function (evento) {
        if (evento.target.tagName !== 'SELECT') return;

        limpiarDependientes(form, evento.target);
        traer(urlDelFormulario(form), form, resultados);
      });
    }

    document.addEventListener('click', function (evento) {
      var pastilla = evento.target.closest('[data-jornada]');
      if (!pastilla) return;
      evento.preventDefault();
      traer(pastilla.getAttribute('href'), form, resultados);
    });
  }

  var CASCADA = ['liga', 'categoria', 'equipo'];

  function limpiarDependientes(form, campoCambiado) {
    var posicion = CASCADA.indexOf(campoCambiado.name);
    if (posicion === -1) return;
    CASCADA.slice(posicion + 1).forEach(function (nombre) {
      var hijo = form.querySelector('[name="' + nombre + '"]');
      if (hijo) hijo.value = '';
    });
  }

  function urlDelFormulario(form) {
    var parametros = new URLSearchParams(new FormData(form));

    Array.from(parametros.keys()).forEach(function (clave) {
      if (!parametros.get(clave)) parametros.delete(clave);
    });
    var consulta = parametros.toString();
    return location.pathname + (consulta ? '?' + consulta : '');
  }

  function traer(url, form, resultados) {
    if (enCurso) enCurso.abort();
    enCurso = new AbortController();
    if (form) form.classList.add('cargando');
    resultados.classList.add('cargando');

    fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      cache: 'no-store',
      signal: enCurso.signal,
    })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var nuevo = new DOMParser().parseFromString(html, 'text/html');
        reemplazar(nuevo, '[data-resultados]');
        reemplazar(nuevo, '[data-jornadas]');

        if (form) {
          form.querySelectorAll('select').forEach(function (select) {
            var reemplazo = nuevo.querySelector('[data-filtros] select[name="' + select.name + '"]');
            if (reemplazo) {
              select.innerHTML = reemplazo.innerHTML;
              select.value = reemplazo.value;
            }
          });
          form.querySelectorAll('input[type="hidden"]').forEach(function (oculto) {
            var reemplazo = nuevo.querySelector('[data-filtros] input[name="' + oculto.name + '"]');
            if (reemplazo) oculto.value = reemplazo.value;
          });

          reemplazar(nuevo, '[data-filtro-estado]');
        }

        history.replaceState(null, '', url);
      })
      .catch(function (error) {

        if (error.name !== 'AbortError') console.error('Error al filtrar:', error);
      })
      .finally(function () {
        if (form) form.classList.remove('cargando');
        resultados.classList.remove('cargando');
      });
  }

  function reemplazar(documentoNuevo, selector) {
    var actual = document.querySelector(selector);
    var reemplazo = documentoNuevo.querySelector(selector);
    if (actual && reemplazo) actual.innerHTML = reemplazo.innerHTML;
  }

  document.addEventListener('DOMContentLoaded', init);
})();
