"""Pruebas de integración (sección 6.2 del informe: PI-01, PI-02 y PI-06)."""
from decimal import Decimal as D

from django.urls import reverse

from auditoria.models import LogAuditoria
from calificaciones.models import Calificacion

from .base import CLAVE, DatosPrueba


class IngresoTests(DatosPrueba):
    def montos_cliente(self):
        return {"monto_8": "192770580", "monto_9": "64161878", "monto_10": "0", "monto_11": "111812860",
                "monto_25": "71298705", "monto_30": "15837333"}

    def test_pi01_ingreso_completo(self):
        self.client.login(username="operador_a", password=CLAVE)
        url = reverse("calificaciones:ingresar")

        # Paso 2: calcular
        r = self.client.post(url, {**self.datos_basicos(), **self.montos_cliente(), "accion": "calcular"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["paso"], "factores")
        self.assertEqual(r.context["suma"], D("1.00000000"))
        factores = {k: v for k, v in r.context["factores"].initial.items()}

        # Paso 3: grabar
        r = self.client.post(url, {**self.datos_basicos(), **self.montos_cliente(),
                                   **{k: str(v) for k, v in factores.items()}, "accion": "grabar"})
        self.assertRedirects(r, reverse("calificaciones:mantenedor"))

        cal = Calificacion.objects.get()
        self.assertEqual(cal.corredor, self.corredor_a)
        self.assertEqual(cal.origen, Calificacion.ORIGEN_MANUAL)
        self.assertEqual(cal.detalles.count(), 30)
        self.assertEqual(cal.factores()[8], D("0.52277431"))
        log = LogAuditoria.objects.get(accion="INGRESO")
        self.assertEqual((log.usuario, log.calificacion, log.origen), (self.operador_a, cal, "MANUAL"))
        self.assertTrue(log.detalles.exists())

    def test_grabar_con_suma_mayor_a_1_se_rechaza(self):
        self.client.login(username="operador_a", password=CLAVE)
        factores = {f"factor_{c}": "0" for c in range(8, 38)}
        factores.update({"factor_8": "0.6", "factor_9": "0.5"})
        r = self.client.post(reverse("calificaciones:ingresar"),
                             {**self.datos_basicos(), **self.montos_cliente(), **factores, "accion": "grabar"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no puede superar 1")
        self.assertFalse(Calificacion.objects.exists())

    def test_calificacion_duplicada_se_rechaza(self):
        self.client.login(username="operador_a", password=CLAVE)
        url = reverse("calificaciones:ingresar")
        r = self.client.post(url, {**self.datos_basicos(), **self.montos_cliente(), "accion": "calcular"})
        datos = {**self.datos_basicos(), **self.montos_cliente(), **{k: str(v) for k, v in r.context["factores"].initial.items()}, "accion": "grabar"}
        self.client.post(url, datos)
        r = self.client.post(url, datos)
        self.assertContains(r, "Ya existe una calificación")
        self.assertEqual(Calificacion.objects.count(), 1)

    def _crear_calificacion(self, corredor, usuario):
        return Calificacion.objects.create(corredor=corredor, instrumento=self.instrumento, ejercicio=2025,
                                           fecha_pago="2025-05-15", secuencia=10001, creado_por=usuario)

    def test_pi02_aislamiento_entre_corredores(self):
        cal = self._crear_calificacion(self.corredor_a, self.operador_a)
        self.client.login(username="operador_b", password=CLAVE)
        r = self.client.get(reverse("calificaciones:mantenedor"))
        self.assertEqual(r.context["pagina"].paginator.count, 0)
        r = self.client.get(reverse("calificaciones:detalle", args=[cal.pk]))
        self.assertEqual(r.status_code, 404)

    def test_pi06_eliminacion_logica(self):
        cal = self._crear_calificacion(self.corredor_a, self.operador_a)
        self.client.login(username="supervisor_a", password=CLAVE)
        r = self.client.post(reverse("calificaciones:eliminar", args=[cal.pk]))
        self.assertRedirects(r, reverse("calificaciones:mantenedor"))
        cal.refresh_from_db()
        self.assertEqual(cal.estado, Calificacion.ELIMINADA)
        r = self.client.get(reverse("calificaciones:mantenedor"))
        self.assertEqual(r.context["pagina"].paginator.count, 0)
        self.assertTrue(LogAuditoria.objects.filter(accion="ELIMINACION", calificacion=cal).exists())

    def test_filtros_del_mantenedor(self):
        self._crear_calificacion(self.corredor_a, self.operador_a)
        self.client.login(username="operador_a", password=CLAVE)
        url = reverse("calificaciones:mantenedor")
        self.assertEqual(self.client.get(url, {"ejercicio": 2025}).context["pagina"].paginator.count, 1)
        self.assertEqual(self.client.get(url, {"ejercicio": 2024}).context["pagina"].paginator.count, 0)
        self.assertEqual(self.client.get(url, {"origen": "CARGA"}).context["pagina"].paginator.count, 0)
