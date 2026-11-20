from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Corredor(models.Model):
    """Corredora de bolsa dueña de sus calificaciones."""

    rut = models.CharField("RUT", max_length=12, unique=True)
    nombre = models.CharField(max_length=120)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "corredores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Rol(models.Model):
    """Perfil de permisos (sección 5.1 del informe)."""

    OPERADOR = "OPERADOR"
    SUPERVISOR = "SUPERVISOR"
    ADMINISTRADOR = "ADMINISTRADOR"
    AUDITOR = "AUDITOR"
    CODIGOS = [
        (OPERADOR, "Operador tributario"),
        (SUPERVISOR, "Supervisor tributario"),
        (ADMINISTRADOR, "Administrador"),
        (AUDITOR, "Auditor"),
    ]

    codigo = models.CharField(max_length=20, choices=CODIGOS, unique=True)
    nombre = models.CharField(max_length=60)

    class Meta:
        verbose_name_plural = "roles"

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    """Persona que usa el sistema. Pertenece a un corredor y tiene un rol."""

    corredor = models.ForeignKey(Corredor, on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios")
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    @property
    def codigo_rol(self):
        return self.rol.codigo if self.rol else None

    def tiene_rol(self, *codigos):
        return self.is_active and self.codigo_rol in codigos

    def esta_bloqueado(self):
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > timezone.now()

    def registrar_fallo(self):
        """Suma un intento fallido. Devuelve True si la cuenta quedó bloqueada."""
        self.intentos_fallidos += 1
        bloqueada = self.intentos_fallidos >= settings.MAX_INTENTOS_FALLIDOS
        if bloqueada:
            self.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.MINUTOS_BLOQUEO)
            self.intentos_fallidos = 0
        self.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        return bloqueada

    def registrar_exito(self):
        if self.intentos_fallidos or self.bloqueado_hasta:
            self.intentos_fallidos = 0
            self.bloqueado_hasta = None
            self.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
