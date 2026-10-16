(function () {
  var SIN_CATEGORIA = 'Categoría';
  var SIN_LIGA = 'Nombre de la liga';

  function pintarLiga(formulario, ligaId) {
    var datos = ligaId ? formulario.querySelector('[data-credencial-ligas] [data-id="' + ligaId + '"]') : null;
    var nombre = datos ? datos.dataset.nombre : SIN_LIGA;
    var temporada = datos ? datos.dataset.temporada : String(new Date().getFullYear());

    formulario.querySelectorAll('[data-credencial-liga]').forEach(function (texto) {
      texto.textContent = nombre;
    });
    formulario.querySelectorAll('[data-credencial-temporada]').forEach(function (texto) {
      texto.textContent = temporada;
    });
    formulario.querySelectorAll('[data-credencial-logo]').forEach(function (caja) {
      caja.replaceChildren();
      if (datos && datos.dataset.logo) {
        var imagen = document.createElement('img');
        imagen.src = datos.dataset.logo;
        imagen.alt = 'Logo de ' + nombre;
        caja.append(imagen);
      } else if (datos) {
        caja.textContent = datos.dataset.iniciales;
      }
    });
  }

  function actualizarSeleccion(zona) {
    var casillas = Array.prototype.slice.call(zona.querySelectorAll('[data-credencial-jugador]'));
    var marcadas = casillas.filter(function (casilla) { return casilla.checked; }).length;
    var elegibles = casillas.filter(function (casilla) { return !casilla.hasAttribute('data-baja'); });

    zona.querySelector('[data-credenciales-cuenta]').textContent =
      marcadas === 1 ? '1 seleccionado' : marcadas + ' seleccionados';
    zona.querySelector('[data-credenciales-imprimir]').disabled = marcadas === 0;
    zona.querySelector('[data-credenciales-todos]').checked =
      elegibles.length > 0 && elegibles.every(function (casilla) { return casilla.checked; });
  }

  function ampliadaAbierta() {
    return document.querySelector('dialog.credencial-ampliada[open]');
  }

  document.addEventListener('click', function (event) {
    var activar = event.target.closest('[data-credenciales-activar]');
    if (activar) {
      var zona = activar.closest('[data-credenciales]');
      var activo = zona.toggleAttribute('data-seleccionando');
      zona.querySelector('[data-credenciales-barra]').hidden = !activo;
      activar.setAttribute('aria-expanded', String(activo));
      return;
    }
    if (event.target.closest('[data-credencial-imprimir]')) {
      window.print();
      return;
    }
    var ampliar = event.target.closest('[data-credencial-ampliar]');
    if (ampliar && !ampliar.closest('dialog')) {
      ampliar.closest('[data-credencial-selector]').querySelector('dialog.credencial-ampliada').showModal();
      return;
    }
    var ampliada = ampliadaAbierta();
    if (ampliada && (event.target === ampliada || event.target.closest('[data-credencial-cerrar]'))) {
      ampliada.close();
    }
  });

  window.addEventListener('keydown', function (event) {
    var ampliada = ampliadaAbierta();
    if (!ampliada || (event.key !== 'Escape' && event.key !== 'Tab')) return;
    event.stopPropagation();
    if (event.key === 'Escape') {
      event.preventDefault();
      ampliada.close();
    }
  }, true);

  document.addEventListener('change', function (event) {
    var objetivo = event.target;
    if (objetivo.matches('[data-credenciales-todos]')) {
      var zona = objetivo.closest('[data-credenciales]');
      zona.querySelectorAll('[data-credencial-jugador]:not([data-baja])').forEach(function (casilla) {
        casilla.checked = objetivo.checked;
      });
      actualizarSeleccion(zona);
      return;
    }
    if (objetivo.matches('[data-credencial-jugador]')) {
      actualizarSeleccion(objetivo.closest('[data-credenciales]'));
      return;
    }
    if (objetivo.matches('[data-credencial-selector] input[type="radio"]')) {
      objetivo.closest('[data-credencial-selector]').querySelectorAll('[data-credencial-vista]').forEach(function (vista) {
        vista.dataset.tema = objetivo.value;
      });
      return;
    }
    if (objetivo.name === 'liga' && objetivo.form && objetivo.form.querySelector('[data-credencial-ligas]')) {
      pintarLiga(objetivo.form, objetivo.value);
    }
  });

  document.addEventListener('input', function (event) {
    var objetivo = event.target;
    if (objetivo.name !== 'nombre' || !objetivo.form) return;
    var texto = objetivo.value.trim() || SIN_CATEGORIA;
    objetivo.form.querySelectorAll('[data-credencial-categoria]').forEach(function (celda) {
      celda.textContent = texto;
    });
  });
})();
