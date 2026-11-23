"""
Pruebas de la funcionalidad de Modificar Calificación Tributaria (HU03).

Verifica:
1. Edición exitosa por Operador y Supervisor con incremento de version y auditoría append-only (LogAuditoria + DetalleLog).
2. Rechazo (403 Forbidden) para roles Auditor y Administrador.
3. Aislamiento multitenant (404 Not Found) entre distintas corredoras y calificaciones eliminadas lógicamente.
4. Rechazo si la suma de factores 8 al 19 supera 1.
5. Control de concurrencia optimista rechazando ediciones si la version no coincide.
6. Recálculo automático de factores al modificar montos con accion="calcular".
7. Control de visualización del botón "Modificar" en el frontend según rol y vigencia.
"""
from datetime import date
from decimal import Decimal as D

from django.urls import reverse

from auditoria.models import DetalleLog, LogAuditoria
from calificaciones.models import Calificacion, ConceptoTributario, DetalleCalificacion

from .base import CLAVE, DatosPrueba


class ModificacionTests(DatosPrueba):
    def setUp(self):
        super().setUp()
        self.calificacion_a = self._crear_calificacion_con_detalles(self.corredor_a, self.operador_a)

    def _crear_calificacion_con_detalles(self, corredor, usuario, version=1, estado=Calificacion.VIGENTE):
        cal = Calificacion.objects.create(
            corredor=corredor,
            instrumento=self.instrumento,
            ejercicio=2025,
            fecha_pago=date(2025, 5, 15),
            secuencia=10001,
            descripcion="Dividendo inicial",
            origen=Calificacion.ORIGEN_MANUAL,
            estado=estado,
            version=version,
            creado_por=usuario,
        )
        conceptos = ConceptoTributario.objects.all()
        detalles = []
        for c in conceptos:
            if c.columna == 8:
                monto = D("600000.00")
                factor = D("0.60000000")
            elif c.columna == 9:
                monto = D("400000.00")
                factor = D("0.40000000")
            else:
                monto = D("0.00")
                factor = D("0.00000000")
            detalles.append(DetalleCalificacion(calificacion=cal, concepto=c, monto=monto, factor=factor))
        DetalleCalificacion.objects.bulk_create(detalles)
        return cal

    def _payload_base(self, cal, **modificaciones):
        """Genera un payload POST completo precargado con los datos actuales de la calificación."""
        payload = {
            "version": str(cal.version),
            "fecha_pago": cal.fecha_pago.isoformat(),
            "descripcion": cal.descripcion,
            "accion": "grabar",
        }
        for d in cal.detalles.select_related("concepto"):
            c = d.concepto.columna
            payload[f"monto_{c}"] = "" if d.monto is None else str(d.monto)
            payload[f"factor_{c}"] = f"{d.factor:.8f}"
        payload.update(modificaciones)
        return payload

    def test_01_edicion_exitosa_por_operador_y_supervisor(self):
        """1. Edición exitosa por Operador y Supervisor con incremento de version y DetalleLog."""
        url = reverse("calificaciones:modificar", args=[self.calificacion_a.pk])

        # Edición por Operador tributario
        self.client.login(username="operador_a", password=CLAVE)
        payload_op = self._payload_base(
            self.calificacion_a,
            fecha_pago="2025-05-20",
            descripcion="Dividendo editado por operador",
            monto_8="700000.00",
            monto_9="300000.00",
            factor_8="0.70000000",
            factor_9="0.30000000",
            accion="grabar",
        )
        r = self.client.post(url, payload_op)
        self.assertRedirects(r, reverse("calificaciones:detalle", args=[self.calificacion_a.pk]))

        self.calificacion_a.refresh_from_db()
        self.assertEqual(self.calificacion_a.version, 2)
        self.assertEqual(self.calificacion_a.fecha_pago, date(2025, 5, 20))
        self.assertEqual(self.calificacion_a.descripcion, "Dividendo editado por operador")
        detalles = {d.concepto.columna: d for d in self.calificacion_a.detalles.select_related("concepto")}
        self.assertEqual(detalles[8].factor, D("0.70000000"))
        self.assertEqual(detalles[9].factor, D("0.30000000"))

        # Verificar LogAuditoria y DetalleLog para el operador
        log_op = LogAuditoria.objects.filter(accion="MODIFICAR", calificacion=self.calificacion_a).latest("fecha")
        self.assertEqual(log_op.usuario, self.operador_a)
        self.assertEqual(log_op.corredor, self.corredor_a)
        self.assertEqual(log_op.origen, "MANUAL")
        cambios_op = {d.campo: (d.valor_anterior, d.valor_nuevo) for d in log_op.detalles.all()}
        self.assertEqual(cambios_op["fecha_pago"], ("2025-05-15", "2025-05-20"))
        self.assertEqual(cambios_op["descripcion"], ("Dividendo inicial", "Dividendo editado por operador"))
        self.assertEqual(cambios_op["factor_8"], ("0.60000000", "0.70000000"))
        self.assertEqual(cambios_op["factor_9"], ("0.40000000", "0.30000000"))
        self.assertEqual(cambios_op["monto_8"], ("600000.00", "700000.00"))
        self.assertEqual(cambios_op["monto_9"], ("400000.00", "300000.00"))

        # Edición posterior por Supervisor tributario
        self.client.logout()
        self.client.login(username="supervisor_a", password=CLAVE)
        payload_sup = self._payload_base(
            self.calificacion_a,
            fecha_pago="2025-05-25",
            descripcion="Dividendo visado por supervisor",
            factor_8="0.50000000",
            factor_9="0.50000000",
            accion="grabar",
        )
        r = self.client.post(url, payload_sup)
        self.assertRedirects(r, reverse("calificaciones:detalle", args=[self.calificacion_a.pk]))

        self.calificacion_a.refresh_from_db()
        self.assertEqual(self.calificacion_a.version, 3)
        self.assertEqual(self.calificacion_a.fecha_pago, date(2025, 5, 25))
        self.assertEqual(self.calificacion_a.descripcion, "Dividendo visado por supervisor")

        log_sup = LogAuditoria.objects.filter(accion="MODIFICAR", calificacion=self.calificacion_a).latest("fecha")
        self.assertEqual(log_sup.usuario, self.supervisor_a)
        cambios_sup = {d.campo: (d.valor_anterior, d.valor_nuevo) for d in log_sup.detalles.all()}
        self.assertIn("fecha_pago", cambios_sup)
        self.assertIn("factor_8", cambios_sup)

    def test_02_rechazo_403_auditor_y_administrador(self):
        """2. Rechazo (403) si un Auditor o Administrador intenta enviar GET o POST a la ruta de edición."""
        url = reverse("calificaciones:modificar", args=[self.calificacion_a.pk])
        payload = self._payload_base(self.calificacion_a, descripcion="Intento no autorizado")

        # Auditor de la misma corredora
        self.client.login(username="auditor_a", password=CLAVE)
        r_get = self.client.get(url)
        self.assertEqual(r_get.status_code, 403)
        r_post = self.client.post(url, payload)
        self.assertEqual(r_post.status_code, 403)

        # Administrador del sistema
        self.client.logout()
        self.client.login(username="admin_nuam", password=CLAVE)
        r_get_adm = self.client.get(url)
        self.assertEqual(r_get_adm.status_code, 403)
        r_post_adm = self.client.post(url, payload)
        self.assertEqual(r_post_adm.status_code, 403)

        # La calificación no debe haber sido modificada
        self.calificacion_a.refresh_from_db()
        self.assertEqual(self.calificacion_a.version, 1)
        self.assertEqual(self.calificacion_a.descripcion, "Dividendo inicial")
        self.assertFalse(LogAuditoria.objects.filter(accion="MODIFICAR").exists())

    def test_03_aislamiento_multitenant_404(self):
        """3. Aislamiento multitenant (404) si un usuario de la Corredora B intenta editar calificación de Corredora A."""
        url = reverse("calificaciones:modificar", args=[self.calificacion_a.pk])
        self.client.login(username="operador_b", password=CLAVE)

        # Operador de otra corredora debe recibir 404
        r_get = self.client.get(url)
        self.assertEqual(r_get.status_code, 404)

        payload = self._payload_base(self.calificacion_a, descripcion="Ataque cross-tenant")
        r_post = self.client.post(url, payload)
        self.assertEqual(r_post.status_code, 404)

        self.calificacion_a.refresh_from_db()
        self.assertEqual(self.calificacion_a.version, 1)

        # Calificación eliminada lógicamente también debe dar 404 para usuarios de la misma corredora
        self.calificacion_a.estado = Calificacion.ELIMINADA
        self.calificacion_a.save()

        self.client.logout()
        self.client.login(username="operador_a", password=CLAVE)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, payload).status_code, 404)

    def test_04_rechazo_suma_factores_supera_1(self):
        """4. Rechazo de guardado si la suma de factores 8 al 19 editados manualmente supera 1."""
        url = reverse("calificaciones:modificar", args=[self.calificacion_a.pk])
        self.client.login(username="operador_a", password=CLAVE)

        payload = self._payload_base(
            self.calificacion_a,
            factor_8="0.70000000",
            factor_9="0.45000000",  # 0.70 + 0.45 = 1.15 > 1
            accion="grabar",
        )
        r = self.client.post(url, payload)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no puede superar 1")

        self.calificacion_a.refresh_from_db()
        self.assertEqual(self.calificacion_a.version, 1)
        self.assertFalse(LogAuditoria.objects.filter(accion="MODIFICAR").exists())

    def test_05_rechazo_conflicto_concurrencia_optimista(self):
        """5. Rechazo por conflicto de concurrencia si version no coincide con la BD."""
        url = reverse("calificaciones:modificar", args=[self.calificacion_a.pk])
        self.client.login(username="operador_a", password=CLAVE)

        # Simular que otro usuario ya incrementó la versión a 2 en la base de datos
        self.calificacion_a.version = 2
        self.calificacion_a.save()

        # El formulario envía la versión antigua (1)
        payload = self._payload_base(
            self.calificacion_a,
            version="1",
            descripcion="Intento con versión desactualizada",
            accion="grabar",
        )
        r = self.client.post(url, payload)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "recargue la página")

        self.calificacion_a.refresh_from_db()
        self.assertEqual(self.calificacion_a.version, 2)
        self.assertEqual(self.calificacion_a.descripcion, "Dividendo inicial")
        self.assertFalse(LogAuditoria.objects.filter(accion="MODIFICAR").exists())

    def test_06_recalcular_factores_desde_montos(self):
        """6. Recálculo automático de factores al modificar montos con accion='calcular'."""
        url = reverse("calificaciones:modificar", args=[self.calificacion_a.pk])
        self.client.login(username="operador_a", password=CLAVE)

        payload = self._payload_base(
            self.calificacion_a,
            monto_8="500000.00",
            monto_9="500000.00",
            accion="calcular",
        )
        r = self.client.post(url, payload)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["paso"], "factores")
        factores_calculados = r.context["factores"].initial
        self.assertEqual(factores_calculados["factor_8"], "0.50000000")
        self.assertEqual(factores_calculados["factor_9"], "0.50000000")
        self.assertEqual(r.context["suma"], D("1.00000000"))

    def test_07_visibilidad_boton_modificar_en_detalle(self):
        """7. Botón 'Modificar' visible en detalle solo para Operador y Supervisor con calificación vigente."""
        url = reverse("calificaciones:detalle", args=[self.calificacion_a.pk])
        url_modificar = reverse("calificaciones:modificar", args=[self.calificacion_a.pk])

        # Operador ve el botón
        self.client.login(username="operador_a", password=CLAVE)
        r_op = self.client.get(url)
        self.assertContains(r_op, url_modificar)

        # Supervisor ve el botón
        self.client.logout()
        self.client.login(username="supervisor_a", password=CLAVE)
        r_sup = self.client.get(url)
        self.assertContains(r_sup, url_modificar)

        # Auditor NO ve el botón
        self.client.logout()
        self.client.login(username="auditor_a", password=CLAVE)
        r_aud = self.client.get(url)
        self.assertNotContains(r_aud, url_modificar)
