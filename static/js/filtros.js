// Filtrado instantaneo de los listados: al escribir, cambiar un desplegable o
// elegir una jornada se reemplaza solo lo que cambio, sin recargar la pagina.
//
// Sin este archivo la barra sigue funcionando: es un formulario GET y las
// jornadas son enlaces normales. Esto solo lo vuelve mas comodo.
(function () {
  var ESPERA_MS = 300;   // pausa tras la ultima tecla antes de consultar
  var temporizador = null;
  var enCurso = null;    // para descartar una consulta que quedo vieja

  function init() {
    var form = document.querySelector('[data-filtros]');
    var resultados = document.querySelector('[data-resultados]');
    if (!resultados) return;

    if (form) {
      form.addEventListener('submit', function (evento) {
        // Con JS el envio normal recargaria todo y se perderia el foco.
        evento.preventDefault();
        traer(urlDelFormulario(form), form, resultados);
      });

      form.querySelectorAll('input[type="search"]').forEach(function (campo) {
        campo.addEventListener('input', function () {
          clearTimeout(temporizador);
          // Se espera a que deje de teclear: si no, se consultaria letra por letra.
          temporizador = setTimeout(function () {
            traer(urlDelFormulario(form), form, resultados);
          }, ESPERA_MS);
        });
      });

      form.addEventListener('change', function (evento) {
        if (evento.target.tagName !== 'SELECT') return;
        // Al cambiar un nivel de la cascada, los de abajo dejan de valer.
        limpiarDependientes(form, evento.target);
        traer(urlDelFormulario(form), form, resultados);
      });
    }

    // Las jornadas son enlaces: se interceptan para no recargar la pagina.
    document.addEventListener('click', function (evento) {
      var pastilla = evento.target.closest('[data-jornada]');
      if (!pastilla) return;
      evento.preventDefault();
      traer(pastilla.getAttribute('href'), form, resultados);
    });
  }

  // Orden de la cascada: cambiar uno invalida los siguientes.
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
    // Los vacios no aportan y ensucian la URL.
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
        // Los desplegables se rearman porque dependen unos de otros: al elegir
        // una liga, Categoria y Equipo tienen que traer solo lo de esa liga.
        // El campo de texto no se toca, para no perder lo que se esta escribiendo.
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
          // Contador y boton Limpiar juntos: los decide el servidor segun los
          // filtros puestos, asi que se reemplaza el bloque entero.
          reemplazar(nuevo, '[data-filtro-estado]');
        }
        // La URL acompana lo que se ve, asi se puede copiar o recargar.
        history.replaceState(null, '', url);
      })
      .catch(function (error) {
        // Abortar una consulta vieja es lo esperado, no es una falla.
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
