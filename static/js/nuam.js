// Confirmación antes de enviar formularios marcados con data-confirmar="mensaje".
// Reemplaza el atributo onsubmit en línea, que la Content-Security-Policy bloquea.
document.addEventListener("submit", function (evento) {
  var mensaje = evento.target.getAttribute("data-confirmar");
  if (mensaje && !window.confirm(mensaje)) {
    evento.preventDefault();
  }
});

// Botones «Siguiente» fuera de la barra de pestañas: data-ir-a="#id-del-panel".
// Bootstrap solo activa pestañas desde botones que están dentro de la barra (.nav),
// así que el botón activa la pestaña correspondiente de la barra (validación 3.7).
document.addEventListener("click", function (evento) {
  var boton = evento.target.closest("[data-ir-a]");
  if (!boton || !window.bootstrap) {
    return;
  }
  var pestana = document.querySelector('.nav-link[data-bs-target="' + boton.getAttribute("data-ir-a") + '"]');
  if (pestana) {
    window.bootstrap.Tab.getOrCreateInstance(pestana).show();
    window.scrollTo(0, 0);
  }
});
