// Filtrado instantaneo de los listados: al escribir o cambiar un desplegable
// se reemplaza solo el bloque de resultados, sin recargar la pagina.
//
// Sin este archivo la barra sigue funcionando: es un formulario GET normal y
// Enter lo envia. Esto solo la vuelve mas comoda.
(function () {
  var ESPERA_MS = 300;   // pausa tras la ultima tecla antes de consultar
  var temporizador = null;
  var enCurso = null;    // para cancelar una consulta que quedo vieja

  function init() {
    var form = document.querySelector('[data-filtros]');
    var resultados = document.querySelector('[data-resultados]');
    if (!form || !resultados) return;

    form.addEventListener('submit', function (evento) {
      // Con JS el envio normal recargaria toda la pagina y se perderia el foco.
      evento.preventDefault();
      pedir(form, resultados);
    });

    form.querySelectorAll('input[type="search"]').forEach(function (campo) {
      campo.addEventListener('input', function () {
        clearTimeout(temporizador);
        // Se espera a que deje de teclear: si no, se consultaria letra por letra.
        temporizador = setTimeout(function () { pedir(form, resultados); }, ESPERA_MS);
      });
    });

    form.querySelectorAll('select').forEach(function (campo) {
      // Elegir una opcion es una decision cerrada, no hace falta esperar.
      campo.addEventListener('change', function () { pedir(form, resultados); });
    });
  }

  function pedir(form, resultados) {
    var parametros = new URLSearchParams(new FormData(form));
    // Los vacios no aportan y ensucian la URL.
    Array.from(parametros.keys()).forEach(function (clave) {
      if (!parametros.get(clave)) parametros.delete(clave);
    });
    var consulta = parametros.toString();
    var url = location.pathname + (consulta ? '?' + consulta : '');

    if (enCurso) enCurso.abort();
    enCurso = new AbortController();
    form.classList.add('cargando');
    resultados.classList.add('cargando');

    fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      cache: 'no-store',
      signal: enCurso.signal,
    })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var nuevo = new DOMParser().parseFromString(html, 'text/html');
        var bloque = nuevo.querySelector('[data-resultados]');
        if (bloque) resultados.innerHTML = bloque.innerHTML;

        var contador = nuevo.querySelector('[data-contador]');
        var actual = form.querySelector('[data-contador]');
        if (bloque && contador && actual) actual.textContent = contador.textContent;

        // La URL acompana lo que se ve, asi se puede copiar o recargar.
        history.replaceState(null, '', url);
      })
      .catch(function (error) {
        // Abortar una consulta vieja es lo esperado, no es una falla.
        if (error.name !== 'AbortError') console.error('Error al filtrar:', error);
      })
      .finally(function () {
        form.classList.remove('cargando');
        resultados.classList.remove('cargando');
      });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
