(function () {
  var EXITO_MS = 2000;

  function aviso(texto, tono) {
    var raiz = document.getElementById('toast-root');
    if (!raiz) {
      raiz = document.createElement('div');
      raiz.id = 'toast-root';
      raiz.setAttribute('role', 'status');
      raiz.setAttribute('aria-live', 'polite');
      raiz.className = 'fixed top-4 right-4 z-[60] flex w-full max-w-sm flex-col gap-2 px-4 sm:px-0';
      document.body.appendChild(raiz);
    }

    var caja = document.createElement('div');
    caja.className = 'toast-message flex items-start gap-3 rounded-2xl border p-4 shadow-lg ' +
      (tono === 'error'
        ? 'bg-red-50 border-red-200 text-red-800'
        : 'bg-green-50 border-green-200 text-green-800');

    var parrafo = document.createElement('p');
    parrafo.className = 'flex-1 text-sm font-medium';
    parrafo.textContent = texto;

    var cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.setAttribute('data-cerrar-toast', '');
    cerrar.setAttribute('aria-label', 'Cerrar aviso');
    cerrar.className = 'text-current opacity-60 hover:opacity-100';
    cerrar.textContent = '✕';
    cerrar.addEventListener('click', function () {
      if (caja.parentNode) caja.parentNode.removeChild(caja);
    });

    caja.appendChild(parrafo);
    caja.appendChild(cerrar);
    raiz.appendChild(caja);

    window.setTimeout(function () {
      if (caja.parentNode) caja.parentNode.removeChild(caja);
    }, 4000);
  }

  function marcarExito(boton) {
    if (boton.dataset.exito) return;
    boton.dataset.exito = '1';
    boton.classList.add('compartir-listo');
    window.setTimeout(function () {
      boton.classList.remove('compartir-listo');
      delete boton.dataset.exito;
    }, EXITO_MS);
  }

  function alPortapapeles(texto) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(texto);
    }
    return new Promise(function (resolver, rechazar) {
      var campo = document.createElement('textarea');
      campo.value = texto;
      campo.setAttribute('readonly', '');
      campo.style.position = 'fixed';
      campo.style.opacity = '0';
      document.body.appendChild(campo);
      campo.select();
      var listo = false;
      try { listo = document.execCommand('copy'); } catch (e) { listo = false; }
      document.body.removeChild(campo);
      listo ? resolver() : rechazar();
    });
  }

  function copiar(boton, url) {
    alPortapapeles(url).then(function () {
      marcarExito(boton);
      aviso('Link copiado');
    }).catch(function () {
      aviso('No se pudo copiar el link', 'error');
    });
  }

  document.addEventListener('click', function (evento) {
    var boton = evento.target.closest('[data-compartir]');
    if (!boton) return;
    evento.preventDefault();

    var url = boton.dataset.url || window.location.href;
    var titulo = boton.dataset.titulo || document.title;

    if (navigator.share) {
      navigator.share({ title: titulo, url: url }).then(function () {
        marcarExito(boton);
      }).catch(function (error) {
        if (error && error.name === 'AbortError') return;
        copiar(boton, url);
      });
      return;
    }

    copiar(boton, url);
  });
})();
