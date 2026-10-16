(function () {
  function dialogoAbierto() {
    return document.querySelector('dialog.aliado-video[open]');
  }

  document.addEventListener('click', function (event) {
    const abrir = event.target.closest('[data-aliado-video-abrir]');
    if (abrir) {
      const dialogo = abrir.nextElementSibling;
      dialogo.showModal();
      dialogo.querySelector('video').play().catch(function () {});
      return;
    }
    const dialogo = dialogoAbierto();
    if (dialogo && (event.target === dialogo || event.target.closest('[data-aliado-video-cerrar]'))) {
      dialogo.close();
    }
  });

  document.addEventListener('close', function (event) {
    if (event.target.matches('dialog.aliado-video')) event.target.querySelector('video').pause();
  }, true);

  window.addEventListener('keydown', function (event) {
    const dialogo = dialogoAbierto();
    if (!dialogo || (event.key !== 'Escape' && event.key !== 'Tab')) return;
    event.stopPropagation();
    if (event.key === 'Escape') {
      event.preventDefault();
      dialogo.close();
    }
  }, true);
})();
