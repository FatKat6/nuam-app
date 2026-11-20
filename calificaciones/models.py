from django.conf import settings
from django.db import models
from django.db.models import Q


class Mercado(models.Model):
    codigo = models.CharField(max_length=3, unique=True)
    nombre = models.CharField(max_length=60)

    def __str__(self):
        return self.nombre


class Instrumento(models.Model):
    """Instrumento financiero que paga el dividendo."""

    mercado = models.ForeignKey(Mercado, on_delete=models.PROTECT, related_name="instrumentos")
    nemotecnico = models.CharField(max_length=20)
    nombre = models.CharField(max_length=120, blank=True)
    no_inscrito = models.BooleanField(default=False)

    class Meta:
        ordering = ["nemotecnico"]
        constraints = [models.UniqueConstraint(fields=["mercado", "nemotecnico"], name="uq_instrumento_mercado")]

    def __str__(self):
        return self.nemotecnico


class ConceptoTributario(models.Model):
    """Catálogo de las 30 columnas tributarias del certificado (8 a 37)."""

    columna = models.PositiveSmallIntegerField(unique=True)
    nombre = models.CharField(max_length=200)
    es_base_calculo = models.BooleanField(default=False, help_text="Forma parte de la suma de las columnas 8 a 19.")

    class Meta:
        ordering = ["columna"]
        constraints = [models.CheckConstraint(condition=Q(columna__gte=8) & Q(columna__lte=37), name="ck_concepto_columna")]

    def __str__(self):
        return f"{self.columna} · {self.nombre}"


class Calificacion(models.Model):
    """Calificación tributaria de un evento de capital."""

    ORIGEN_MANUAL, ORIGEN_CARGA, ORIGEN_SISTEMA = "MANUAL", "CARGA", "SISTEMA"
    ORIGENES = [(ORIGEN_MANUAL, "Ingreso manual"), (ORIGEN_CARGA, "Carga masiva"), (ORIGEN_SISTEMA, "Sistema")]
    VIGENTE, ELIMINADA = "VIGENTE", "ELIMINADA"
    ESTADOS = [(VIGENTE, "Vigente"), (ELIMINADA, "Eliminada")]

    corredor = models.ForeignKey("usuarios.Corredor", on_delete=models.PROTECT, related_name="calificaciones")
    instrumento = models.ForeignKey(Instrumento, on_delete=models.PROTECT, related_name="calificaciones")
    ejercicio = models.PositiveSmallIntegerField()
    fecha_pago = models.DateField("fecha de pago")
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    secuencia = models.PositiveIntegerField("secuencia del evento")
    origen = models.CharField(max_length=10, choices=ORIGENES, default=ORIGEN_MANUAL)
    estado = models.CharField(max_length=10, choices=ESTADOS, default=VIGENTE)
    version = models.PositiveIntegerField(default=1, help_text="Para detectar ediciones simultáneas (Sprint 4).")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ejercicio", "-fecha_pago", "instrumento__nemotecnico"]
        verbose_name_plural = "calificaciones"
        constraints = [
            models.UniqueConstraint(fields=["corredor", "ejercicio", "instrumento", "secuencia"], name="uq_calificacion_negocio"),
            models.CheckConstraint(condition=Q(secuencia__gt=10000), name="ck_calificacion_secuencia"),
            models.CheckConstraint(condition=Q(ejercicio__gte=1000) & Q(ejercicio__lte=9999), name="ck_calificacion_ejercicio"),
        ]

    def __str__(self):
        return f"{self.ejercicio} · {self.instrumento} · {self.secuencia}"

    def factores(self):
        return {d.concepto.columna: d.factor for d in self.detalles.select_related("concepto")}


class DetalleCalificacion(models.Model):
    """Monto y factor de una columna tributaria para una calificación."""

    calificacion = models.ForeignKey(Calificacion, on_delete=models.PROTECT, related_name="detalles")
    concepto = models.ForeignKey(ConceptoTributario, on_delete=models.PROTECT, related_name="+")
    monto = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    factor = models.DecimalField(max_digits=9, decimal_places=8)

    class Meta:
        ordering = ["concepto__columna"]
        constraints = [
            models.UniqueConstraint(fields=["calificacion", "concepto"], name="uq_detalle_concepto"),
            models.CheckConstraint(condition=Q(factor__gte=0) & Q(factor__lte=1), name="ck_detalle_factor"),
        ]
