"""
Pruebas de rendimiento PR-01 y PR-02 (sección 6.2 del informe).

Ejecución contra el servidor (20 usuarios durante 5 minutos):
  locust -f pruebas/locustfile.py --host https://3.17.230.66 --headless -u 20 -r 0.3 -t 6m \
         --csv resultados/locust --html resultados/locust.html

Variables de entorno: NUAM_USUARIO y NUAM_CLAVE (usuario operador de prueba).
NUAM_VERIFICAR_SSL=0 acepta el certificado autofirmado del prototipo.

La tasa de llegada (-r 0.3, un usuario cada ~3 s) respeta el límite de Nginx en el
inicio de sesión (30 peticiones por minuto por IP), así los 20 usuarios entran en
~1 minuto y luego quedan 5 minutos de carga completa.
"""
import os
import random
import re

import urllib3
from locust import HttpUser, between, task

USUARIO = os.environ.get("NUAM_USUARIO", "operador_a")
CLAVE = os.environ.get("NUAM_CLAVE", "")
VERIFICAR_SSL = os.environ.get("NUAM_VERIFICAR_SSL", "1") != "0"
if not VERIFICAR_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
MONTOS = {"monto_8": "192770580", "monto_9": "64161878", "monto_10": "0", "monto_11": "111812860",
          "monto_25": "71298705", "monto_30": "15837333"}


def token(html):
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    return m.group(1) if m else ""


class Operador(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.verify = VERIFICAR_SSL
        # En HTTPS, Django exige que los POST traigan Referer del mismo sitio (protección CSRF).
        self.client.headers["Referer"] = self.host.rstrip("/") + "/"
        r = self.client.get("/cuenta/ingresar/", name="PR-01 login (GET)")
        with self.client.post("/cuenta/ingresar/", {"csrfmiddlewaretoken": token(r.text), "usuario": USUARIO, "clave": CLAVE},
                              name="PR-01 login (POST)", catch_response=True) as resp:
            if "/cuenta/ingresar/" in resp.url:
                resp.failure("No inició sesión (revise NUAM_CLAVE o si la cuenta quedó bloqueada)")
        r = self.client.get("/calificaciones/ingresar/", name="PR-02 formulario")
        m = re.search(r'<option value="(\d+)"[^>]*>FALABELLA', r.text)
        self.instrumento = m.group(1) if m else "1"
        m = re.search(r'<option value="(\d+)"[^>]*>Acciones', r.text)
        self.mercado = m.group(1) if m else "1"

    @task(3)
    def pr01_mantenedor(self):
        self.client.get("/calificaciones/", name="PR-01 mantenedor")

    @task(1)
    def pr02_calcular_y_grabar(self):
        r = self.client.get("/calificaciones/ingresar/", name="PR-02 formulario")
        datos = {"csrfmiddlewaretoken": token(r.text), "mercado": self.mercado, "ejercicio": "2026",
                 "instrumento": self.instrumento, "fecha_pago": "2026-05-15",
                 "secuencia": str(random.randint(10_001, 99_999_999)), "descripcion": "Prueba de carga", **MONTOS}
        r = self.client.post("/calificaciones/ingresar/", {**datos, "accion": "calcular"}, name="PR-02 calcular")
        factores = dict(re.findall(r'name="(factor_\d+)" value="([^"]*)"', r.text))
        if len(factores) == 30:
            self.client.post("/calificaciones/ingresar/", {**datos, **factores, "csrfmiddlewaretoken": token(r.text), "accion": "grabar"},
                             name="PR-02 grabar")
