

(function () {
  var ABIERTO = 'desplegable-abierto';

  function opcionesDe(select) {
    return Array.prototype.map.call(select.options, function (o) {
      return { valor: o.value, texto: o.text };
    });
  }

  function construir(select) {
    if (select.dataset.montado) return;
    select.dataset.montado = '1';

    var caja = document.createElement('div');
    caja.className = 'desplegable';

    var boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'desplegable-boton';
    boton.setAttribute('aria-haspopup', 'listbox');
    boton.setAttribute('aria-expanded', 'false');

    var panel = document.createElement('div');
    panel.className = 'desplegable-panel';
    panel.setAttribute('role', 'listbox');
    panel.hidden = true;

    opcionesDe(select).forEach(function (opcion, i) {
      var fila = document.createElement('button');
      fila.type = 'button';
      fila.className = 'desplegable-opcion';
      fila.setAttribute('role', 'option');
      fila.dataset.valor = opcion.valor;
      fila.dataset.indice = i;
      fila.textContent = opcion.texto;
      panel.appendChild(fila);
    });

    select.parentNode.insertBefore(caja, select);
    caja.appendChild(boton);
    caja.appendChild(panel);
    caja.appendChild(select);
    select.classList.add('desplegable-real');

    if (select.id) {
      boton.id = select.id;
      select.id = select.id + '-real';
    }

    sincronizar(select, boton, panel);
    conectar(select, caja, boton, panel);
  }

  function sincronizar(select, boton, panel) {
    var elegida = select.options[select.selectedIndex];
    boton.textContent = elegida ? elegida.text : '';
    boton.classList.toggle('sin-elegir', !select.value);
    Array.prototype.forEach.call(panel.children, function (fila) {
      var activa = fila.dataset.valor === select.value;
      fila.classList.toggle('elegida', activa);
      fila.setAttribute('aria-selected', activa ? 'true' : 'false');
    });
  }

  function abrir(caja, boton, panel, select) {
    cerrarTodos();
    caja.classList.add(ABIERTO);
    panel.hidden = false;
    boton.setAttribute('aria-expanded', 'true');
    var elegida = panel.querySelector('.elegida') || panel.firstChild;
    if (elegida) {

      panel.scrollTop = elegida.offsetTop - panel.clientHeight / 2 + elegida.offsetHeight / 2;
      elegida.focus();
    }
  }

  function cerrar(caja) {
    var boton = caja.querySelector('.desplegable-boton');
    var panel = caja.querySelector('.desplegable-panel');
    caja.classList.remove(ABIERTO);
    panel.hidden = true;
    boton.setAttribute('aria-expanded', 'false');
  }

  function cerrarTodos() {
    document.querySelectorAll('.' + ABIERTO).forEach(cerrar);
  }

  function conectar(select, caja, boton, panel) {
    boton.addEventListener('click', function () {
      if (caja.classList.contains(ABIERTO)) cerrar(caja);
      else abrir(caja, boton, panel, select);
    });

    panel.addEventListener('click', function (evento) {
      var fila = evento.target.closest('.desplegable-opcion');
      if (!fila) return;
      select.value = fila.dataset.valor;

      select.dispatchEvent(new Event('change', { bubbles: true }));
      sincronizar(select, boton, panel);
      cerrar(caja);
      boton.focus();
    });

    caja.addEventListener('keydown', function (evento) {
      var abierto = caja.classList.contains(ABIERTO);
      if (evento.key === 'Escape' && abierto) {
        cerrar(caja);
        boton.focus();
        return;
      }
      if ((evento.key === 'ArrowDown' || evento.key === 'ArrowUp')) {
        evento.preventDefault();
        if (!abierto) return abrir(caja, boton, panel, select);
        var filas = Array.prototype.slice.call(panel.children);
        var i = filas.indexOf(document.activeElement);
        var siguiente = filas[i + (evento.key === 'ArrowDown' ? 1 : -1)];
        if (siguiente) siguiente.focus();
      }
    });

    select.addEventListener('change', function () {
      sincronizar(select, boton, panel);
    });
  }

  function montarTodos() {
    document.querySelectorAll('select[data-desplegable]').forEach(construir);
  }

  document.addEventListener('click', function (evento) {
    if (!evento.target.closest('.desplegable')) cerrarTodos();
  });

  new MutationObserver(function (cambios) {
    var aparecio = cambios.some(function (cambio) {
      return Array.prototype.some.call(cambio.addedNodes, function (nodo) {
        return nodo.nodeType === 1 && (
          nodo.matches && (nodo.matches('select[data-desplegable]') ||
                           nodo.querySelector('select[data-desplegable]'))
        );
      });
    });
    if (aparecio) montarTodos();
  }).observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', montarTodos);
})();
