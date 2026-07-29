// Comportamientos compartidos de los formularios: ojo de contrasena,
// capitalizacion automatica y marcado en rojo de los campos obligatorios.
// Se llama con initFormulario(contenedor) tanto en la pagina completa como
// sobre el HTML que se inyecta en el modal.
(function () {
  var ICONO_OJO_ABIERTO = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>';
  var ICONO_OJO_CERRADO = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" /></svg>';

  function aTitulo(texto) {
    return texto.toLowerCase().replace(/(^|\s)(\S)/g, function (_, separador, letra) {
      return separador + letra.toUpperCase();
    });
  }

  function ponerOjos(raiz) {
    raiz.querySelectorAll('input[type="password"]').forEach(function (input) {
      if (input.dataset.ojoBound) return;
      input.dataset.ojoBound = '1';
      input.style.paddingRight = '2.75rem';
      var wrapper = document.createElement('div');
      wrapper.dataset.wrapperPassword = '1';
      wrapper.style.position = 'relative';
      wrapper.style.display = 'flex';
      wrapper.style.alignItems = 'center';
      // El margen superior del input debe vivir en el wrapper: si no, el wrapper
      // queda mas alto que el campo y el ojo se centra desplazado hacia arriba.
      wrapper.style.marginTop = window.getComputedStyle(input).marginTop;
      input.style.marginTop = '0';
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.innerHTML = ICONO_OJO_ABIERTO;
      btn.setAttribute('aria-label', 'Mostrar contraseña');
      btn.className = 'absolute inset-y-0 right-3 flex items-center justify-center text-gray-400 hover:text-gray-700';
      btn.addEventListener('click', function () {
        var visible = input.type === 'text';
        input.type = visible ? 'password' : 'text';
        btn.innerHTML = visible ? ICONO_OJO_ABIERTO : ICONO_OJO_CERRADO;
      });
      wrapper.appendChild(btn);
    });
  }

  function ponerCapitalizacion(raiz) {
    raiz.querySelectorAll('[data-capitalizar]').forEach(function (input) {
      if (input.dataset.capitalizarBound) return;
      input.dataset.capitalizarBound = '1';
      input.addEventListener('input', function () {
        var corregido = aTitulo(input.value);
        if (corregido === input.value) return;
        // Reescribir el value manda el cursor al final, asi que lo devolvemos a
        // su lugar. Calza exacto porque solo cambia el caso, no el largo.
        var cursor = input.selectionStart;
        input.value = corregido;
        input.setSelectionRange(cursor, cursor);
      });
    });
  }

  function ponerSoloNumeros(raiz) {
    raiz.querySelectorAll('[data-solo-numeros]').forEach(function (input) {
      if (input.dataset.numerosBound) return;
      input.dataset.numerosBound = '1';
      input.addEventListener('input', function () {
        var maximo = parseInt(input.getAttribute('maxlength'), 10);
        var limpio = input.value.replace(/\D/g, '');
        if (maximo > 0) limpio = limpio.slice(0, maximo);
        if (limpio === input.value) return;
        // Aca si cambia el largo, asi que el cursor no se puede devolver a la
        // misma posicion: se cuenta cuantos digitos quedaron a su izquierda.
        var digitosAntes = input.value.slice(0, input.selectionStart).replace(/\D/g, '').length;
        input.value = limpio;
        var posicion = Math.min(digitosAntes, limpio.length);
        input.setSelectionRange(posicion, posicion);
      });
    });
  }

  // Donde colgar el aviso de obligatorio. El ojo de contrasena envuelve el
  // input en un div, y los radios viven dentro de un grupo: en ambos casos el
  // aviso va despues del bloque entero y no pegado al campo.
  function anclaDe(campo) {
    var grupo = campo.type === 'radio' ? campo.closest('.grupo-opciones') : null;
    if (grupo) return grupo;
    var padre = campo.parentNode;
    return padre && padre.dataset && padre.dataset.wrapperPassword ? padre : campo;
  }

  function vacio(campo) {
    // Un radio se evalua por grupo: basta con que alguno del mismo name este marcado.
    if (campo.type === 'radio') {
      return !campo.form.querySelector('input[name="' + campo.name + '"]:checked');
    }
    if (campo.type === 'checkbox') return !campo.checked;
    return !campo.value || !campo.value.trim();
  }

  // Django pone required en todos los radios del grupo; se revisa uno solo para
  // no repetir el mismo aviso siete veces.
  function requeridosDe(form) {
    var gruposVistos = {};
    var campos = [];
    form.querySelectorAll('[required]').forEach(function (campo) {
      if (campo.type === 'radio') {
        if (gruposVistos[campo.name]) return;
        gruposVistos[campo.name] = true;
      }
      campos.push(campo);
    });
    return campos;
  }

  function limpiarError(campo) {
    campo.classList.remove('campo-invalido');
    var siguiente = anclaDe(campo).nextElementSibling;
    if (siguiente && siguiente.classList.contains('error-campo')) siguiente.remove();
  }

  function marcarError(campo, mensaje) {
    // En un grupo de radios pintar de rojo un solo circulito confunde: alcanza
    // con el aviso debajo del grupo.
    if (campo.type !== 'radio') campo.classList.add('campo-invalido');
    var ancla = anclaDe(campo);
    var aviso = document.createElement('p');
    aviso.className = 'error-campo';
    aviso.textContent = mensaje || 'Este campo es obligatorio.';
    ancla.parentNode.insertBefore(aviso, ancla.nextSibling);
  }

  function aFechaLocal(iso) {
    var p = iso.split('-');
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  // Las fechas del navegador viajan como yyyy-mm-dd, asi que comparar los
  // strings alcanza y evita depender de como parsea Date cada navegador.
  function fueraDeRango(campo) {
    if (!campo.value) return '';
    var minimo = campo.getAttribute('min');
    var maximo = campo.getAttribute('max');
    if (minimo && campo.value < minimo) {
      return 'La fecha no puede ser anterior al ' + aFechaLocal(minimo) + '.';
    }
    if (maximo && campo.value > maximo) {
      return 'La fecha no puede ser posterior al ' + aFechaLocal(maximo) + '.';
    }
    return '';
  }

  function ponerValidacion(raiz) {
    raiz.querySelectorAll('form').forEach(function (form) {
      if (form.dataset.validacionBound) return;
      form.dataset.validacionBound = '1';
      form.addEventListener('submit', function (evento) {
        var faltantes = [];
        requeridosDe(form).forEach(function (campo) {
          limpiarError(campo);
          if (vacio(campo)) {
            marcarError(campo);
            faltantes.push(campo);
          }
        });
        // El form va con novalidate, asi que el min/max de las fechas no lo
        // frena el navegador: hay que revisarlo aca.
        form.querySelectorAll('input[type="date"]').forEach(function (campo) {
          if (faltantes.indexOf(campo) !== -1) return;
          limpiarError(campo);
          var problema = fueraDeRango(campo);
          if (problema) {
            marcarError(campo, problema);
            faltantes.push(campo);
          }
        });
        if (!faltantes.length) return;
        evento.preventDefault();
        // Corta tambien el handler que envia el modal por fetch.
        evento.stopImmediatePropagation();
        faltantes[0].focus();
      });

      form.querySelectorAll('[required], input[type="date"]').forEach(function (campo) {
        if (campo.dataset.limpiezaBound) return;
        campo.dataset.limpiezaBound = '1';
        campo.addEventListener('input', function () { limpiarError(campo); });
        campo.addEventListener('change', function () { limpiarError(campo); });
      });
    });
  }

  window.initFormulario = function (raiz) {
    raiz = raiz || document;
    ponerOjos(raiz);
    ponerCapitalizacion(raiz);
    ponerSoloNumeros(raiz);
    ponerValidacion(raiz);
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.initFormulario(document);
  });
})();
