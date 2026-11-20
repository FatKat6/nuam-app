from django.conf import settings
from django.db import models


class CargaArchivo(models.Model):
    """Archivo CSV de una carga masiva (HU04, Sprint 5).

    El archivo se guarda fuera de la base; aquí se conserva su ubicación y su huella
    SHA-256 para relacionar cada calificación con el archivo exacto del que provino.
    """

    ESTADOS = [("VALIDANDO", "Validando"), ("RECHAZADA", "Rechazada"), ("GRABADA", "Grabada")]

    corredor = models.ForeignKey("usuarios.Corredor", on_delete=models.PROTECT, related_name="cargas")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cargas")
    nombre = models.CharField(max_length=255)
    ubicacion = models.CharField(max_length=500)
    sha256 = models.CharField(max_length=64)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="VALIDANDO")
    total_filas = models.PositiveIntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return self.nombre
