// Confirmación antes de enviar formularios marcados con data-confirmar="mensaje".
// Reemplaza el atributo onsubmit en línea, que la Content-Security-Policy bloquea.
document.addEventListener("submit", function (evento) {
  var mensaje = evento.target.getAttribute("data-confirmar");
  if (mensaje && !window.confirm(mensaje)) {
    evento.preventDefault();
  }
});
