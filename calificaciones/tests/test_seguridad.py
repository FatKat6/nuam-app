"""Pruebas de seguridad automatizadas (sección 6.2 del informe: PS-01 a PS-07)."""
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from auditoria.models import LogAuditoria
from calificaciones.models import Calificacion

from .base import CLAVE, DatosPrueba


class SeguridadTests(DatosPrueba):
    def login(self, usuario, clave):
        return self.client.post(reverse("usuarios:login"), {"usuario": usuario, "clave": clave})

    def test_ps01_bloqueo_tras_5_intentos(self):
        for _ in range(5):
            r = self.login("operador_a", "incorrecta")
            self.assertContains(r, "Usuario o contraseña incorrectos.")
        # Sexto intento, incluso con la contraseña correcta: bloqueada
        r = self.login("operador_a", CLAVE)
        self.assertContains(r, "bloqueada")
        self.operador_a.refresh_from_db()
        self.assertTrue(self.operador_a.esta_bloqueado())
        self.assertTrue(LogAuditoria.objects.filter(accion="BLOQUEO_CUENTA", usuario=self.operador_a).exists())

    def test_ps01_desbloqueo_tras_15_minutos(self):
        self.operador_a.bloqueado_hasta = timezone.now() - timedelta(seconds=1)
        self.operador_a.save()
        r = self.login("operador_a", CLAVE)
        self.assertRedirects(r, reverse("inicio"), fetch_redirect_response=False)

    def test_mensaje_no_revela_si_el_usuario_existe(self):
        r1 = self.login("no_existe", "x")
        r2 = self.login("operador_a", "x")
        self.assertContains(r1, "Usuario o contraseña incorrectos.")
        self.assertContains(r2, "Usuario o contraseña incorrectos.")

    def test_ps02_acceso_sin_sesion(self):
        for nombre in ["calificaciones:mantenedor", "calificaciones:ingresar", "auditoria:historial"]:
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 302)
            self.assertIn(reverse("usuarios:login"), r["Location"])

    def test_ps03_accion_sin_permiso(self):
        cal = Calificacion.objects.create(corredor=self.corredor_a, instrumento=self.instrumento, ejercicio=2025,
                                          fecha_pago="2025-05-15", secuencia=10001, creado_por=self.operador_a)
        self.client.login(username="operador_a", password=CLAVE)
        r = self.client.post(reverse("calificaciones:eliminar", args=[cal.pk]))
        self.assertEqual(r.status_code, 403)
        cal.refresh_from_db()
        self.assertEqual(cal.estado, Calificacion.VIGENTE)

    def test_ps03_auditor_no_puede_ingresar_y_admin_no_ve_calificaciones(self):
        self.client.login(username="auditor_a", password=CLAVE)
        self.assertEqual(self.client.get(reverse("calificaciones:ingresar")).status_code, 403)
        self.client.login(username="admin_nuam", password=CLAVE)
        self.assertEqual(self.client.get(reverse("calificaciones:mantenedor")).status_code, 403)

    def test_ps04_inyeccion_sql(self):
        r = self.login("' OR 1=1 --", "' OR 1=1 --")
        self.assertContains(r, "Usuario o contraseña incorrectos.")
        self.client.login(username="operador_a", password=CLAVE)
        r = self.client.get(reverse("calificaciones:mantenedor"), {"ejercicio": "2025 OR 1=1", "origen": "' OR 1=1 --"})
        self.assertEqual(r.status_code, 200)

    def test_ps05_xss(self):
        Calificacion.objects.create(corredor=self.corredor_a, instrumento=self.instrumento, ejercicio=2025, fecha_pago="2025-05-15",
                                    secuencia=10001, creado_por=self.operador_a, descripcion="<script>alert(1)</script>")
        self.client.login(username="operador_a", password=CLAVE)
        r = self.client.get(reverse("calificaciones:mantenedor"))
        self.assertNotContains(r, "<script>alert(1)</script>")
        self.assertContains(r, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_ps06_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.login(username="operador_a", password=CLAVE)
        r = cliente.post(reverse("calificaciones:ingresar"), {**self.datos_basicos(), "accion": "calcular"})
        self.assertEqual(r.status_code, 403)

    def test_ps07_expiracion_de_sesion(self):
        self.client.login(username="operador_a", password=CLAVE)
        self.assertEqual(self.client.get(reverse("calificaciones:mantenedor")).status_code, 200)
        Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))
        r = self.client.get(reverse("calificaciones:mantenedor"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("usuarios:login"), r["Location"])

    def test_log_no_se_modifica_ni_se_borra(self):
        self.login("operador_a", CLAVE)
        log = LogAuditoria.objects.first()
        with self.assertRaises(PermissionError):
            log.accion = "OTRA"
            log.save()
        with self.assertRaises(PermissionError):
            log.delete()
