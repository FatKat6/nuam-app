from django.conf import settings
from django.db import models


class LogAuditoria(models.Model):
    """Registro de cada acción. Solo admite inserciones (ver save y delete)."""

    ORIGENES = [("MANUAL", "Ingreso manual"), ("CARGA", "Carga masiva"), ("SISTEMA", "Sistema")]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+")
    corredor = models.ForeignKey("usuarios.Corredor", on_delete=models.PROTECT, null=True, related_name="+")
    accion = models.CharField(max_length=40)
    origen = models.CharField(max_length=10, choices=ORIGENES, default="SISTEMA")
    calificacion = models.ForeignKey("calificaciones.Calificacion", on_delete=models.PROTECT, null=True, blank=True, related_name="logs")
    fecha = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d %H:%M} {self.accion}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("El log de auditoría no se puede modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("El log de auditoría no se puede borrar.")


class DetalleLog(models.Model):
    """Campo modificado en una acción, con su valor anterior y nuevo."""

    log = models.ForeignKey(LogAuditoria, on_delete=models.PROTECT, related_name="detalles")
    campo = models.CharField(max_length=80)
    valor_anterior = models.CharField(max_length=255, blank=True)
    valor_nuevo = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.campo
