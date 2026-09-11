(function () {
  var SECCION = '[data-trofeos]';
  var FILA = '[data-trofeo-fila]';

  function secciones(raiz) {
    var lista = Array.prototype.slice.call((raiz || document).querySelectorAll(SECCION));
    if (raiz && raiz.matches && raiz.matches(SECCION)) lista.unshift(raiz);
    return lista;
  }

  function tope(seccion) {
    var valor = parseInt(seccion.getAttribute('data-trofeos-tope'), 10);
    return isNaN(valor) ? 20 : valor;
  }

  function filas(seccion) {
    return seccion.querySelectorAll(FILA);
  }

  function siguienteIndice(seccion) {
    var mayor = -1;
    filas(seccion).forEach(function (fila) {
      var campo = fila.querySelector('input[name="trofeo_indice"]');
      var valor = campo ? parseInt(campo.value, 10) : NaN;
      if (!isNaN(valor) && valor > mayor) mayor = valor;
    });
    return mayor + 1;
  }

  function agregar(seccion) {
    var plantilla = seccion.querySelector('[data-trofeos-plantilla]');
    var contenedor = seccion.querySelector('[data-trofeos-filas]');
    if (!plantilla || !contenedor || filas(seccion).length >= tope(seccion)) return;

    var indice = String(siguienteIndice(seccion));
    var fila = plantilla.content.cloneNode(true).querySelector(FILA);

    fila.querySelectorAll('[name]').forEach(function (campo) {
      campo.name = campo.name.split('__I__').join(indice);
    });
    var marca = fila.querySelector('input[name="trofeo_indice"]');
    if (marca) marca.value = indice;

    contenedor.appendChild(fila);
    refrescar(seccion);

    var titulo = fila.querySelector('.trofeo-titulo');
    if (titulo) titulo.focus();
  }

  function quitar(fila) {
    var seccion = fila.closest(SECCION);
    liberar(fila);
    fila.remove();
    if (seccion) refrescar(seccion);
  }

  function liberar(fila) {
    var vista = fila.querySelector('[data-trofeo-vista]');
    if (vista && vista.dataset.objeto) {
      URL.revokeObjectURL(vista.dataset.objeto);
      delete vista.dataset.objeto;
    }
  }

  function elegirFoto(archivo) {
    var fila = archivo.closest(FILA);
    if (!fila) return;

    var vista = fila.querySelector('[data-trofeo-vista]');
    var elegido = archivo.files && archivo.files[0];
    if (!vista) return;

    liberar(fila);

    if (elegido) {
      var url = URL.createObjectURL(elegido);
      vista.dataset.objeto = url;
      vista.src = url;
      marcarSinImagen(fila, false);
    }
    pintarFoto(fila, !!elegido || tieneFoto(fila));
    exigirNombre(fila);
  }

  function tieneFoto(fila) {
    var quitarFoto = fila.querySelector('[data-trofeo-foto-quitar]');
    return !!quitarFoto && !quitarFoto.hidden;
  }

  function quitarFoto(boton) {
    var fila = boton.closest(FILA);
    if (!fila) return;

    var archivo = fila.querySelector('[data-trofeo-archivo]');
    var vista = fila.querySelector('[data-trofeo-vista]');

    liberar(fila);
    if (archivo) archivo.value = '';
    if (vista) vista.src = vista.getAttribute('data-trofeo-neutra') || vista.src;

    marcarSinImagen(fila, true);
    pintarFoto(fila, false);
  }

  function marcarSinImagen(fila, sin) {
    var campo = fila.querySelector('[data-trofeo-sin-imagen]');
    if (campo) campo.value = sin ? '1' : '';
  }

  function pintarFoto(fila, cargada) {
    var etiqueta = fila.querySelector('[data-trofeo-foto]');
    var texto = fila.querySelector('[data-trofeo-foto-texto]');
    var boton = fila.querySelector('[data-trofeo-foto-quitar]');

    if (etiqueta) etiqueta.classList.toggle('trofeo-foto-cargada', cargada);
    if (texto) texto.textContent = cargada ? 'Cambiar' : 'Subir foto';
    if (boton) boton.hidden = !cargada;
  }

  function texto(campo) {
    return campo && campo.value ? campo.value.trim() : '';
  }

  function conContenido(fila) {
    var identificador = fila.querySelector('input[name="trofeo_id"]');
    var archivo = fila.querySelector('[data-trofeo-archivo]');
    return !!(texto(fila.querySelector('.trofeo-titulo')) ||
              texto(fila.querySelector('.trofeo-descripcion')) ||
              texto(identificador) ||
              (archivo && archivo.files && archivo.files.length) ||
              tieneFoto(fila));
  }

  function exigirNombre(fila) {
    var titulo = fila.querySelector('.trofeo-titulo');
    if (!titulo) return;
    var obligatorio = conContenido(fila);
    if (titulo.required !== obligatorio) titulo.required = obligatorio;
    if (!obligatorio || texto(titulo)) limpiarAviso(fila);
  }

  function limpiarAviso(fila) {
    var titulo = fila.querySelector('.trofeo-titulo');
    if (titulo) {
      titulo.classList.remove('campo-invalido');
      titulo.removeAttribute('aria-invalid');
    }
    fila.classList.remove('trofeo-fila-invalida');
    var aviso = fila.querySelector('.trofeo-datos .error-campo');
    if (aviso) aviso.remove();
  }

  function refrescar(seccion) {
    filas(seccion).forEach(exigirNombre);

    var cuantos = filas(seccion).length;
    var maximo = tope(seccion);

    var cuenta = seccion.querySelector('[data-trofeos-cuenta]');
    if (cuenta) cuenta.textContent = cuantos ? cuantos + ' de ' + maximo : '';

    var vacio = seccion.querySelector('[data-trofeos-vacio]');
    if (vacio) vacio.hidden = cuantos > 0;

    var lleno = seccion.querySelector('[data-trofeos-lleno]');
    if (lleno) lleno.hidden = cuantos < maximo;

    var boton = seccion.querySelector('[data-trofeos-agregar]');
    if (boton) boton.disabled = cuantos >= maximo;
  }

  document.addEventListener('click', function (evento) {
    var agregarBoton = evento.target.closest('[data-trofeos-agregar]');
    if (agregarBoton) {
      evento.preventDefault();
      agregar(agregarBoton.closest(SECCION));
      return;
    }

    var sinFoto = evento.target.closest('[data-trofeo-foto-quitar]');
    if (sinFoto) {
      evento.preventDefault();
      quitarFoto(sinFoto);
      return;
    }

    var quitarBoton = evento.target.closest('[data-trofeo-quitar]');
    if (quitarBoton) {
      evento.preventDefault();
      quitar(quitarBoton.closest(FILA));
    }
  });

  document.addEventListener('change', function (evento) {
    var archivo = evento.target.closest('[data-trofeo-archivo]');
    if (archivo) elegirFoto(archivo);
    vigilar(evento.target);
  });

  document.addEventListener('input', function (evento) {
    vigilar(evento.target);
  });

  function vigilar(destino) {
    var fila = destino.closest ? destino.closest(FILA) : null;
    if (fila) exigirNombre(fila);
  }

  window.initTrofeos = function (raiz) {
    secciones(raiz).forEach(refrescar);
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.initTrofeos(document);
  });
})();
