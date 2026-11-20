from datetime import date

from django.test import TestCase

from calificaciones.models import Instrumento, Mercado
from usuarios.models import Corredor, Rol, Usuario

CLAVE = "Prueba.Nuam.2026"


class DatosPrueba(TestCase):
    """Crea dos corredoras y un usuario por rol para las pruebas."""

    @classmethod
    def setUpTestData(cls):
        cls.corredor_a = Corredor.objects.create(rut="76.111.111-1", nombre="Corredora A")
        cls.corredor_b = Corredor.objects.create(rut="76.222.222-2", nombre="Corredora B")
        cls.operador_a = cls.crear("operador_a", Rol.OPERADOR, cls.corredor_a)
        cls.supervisor_a = cls.crear("supervisor_a", Rol.SUPERVISOR, cls.corredor_a)
        cls.auditor_a = cls.crear("auditor_a", Rol.AUDITOR, cls.corredor_a)
        cls.operador_b = cls.crear("operador_b", Rol.OPERADOR, cls.corredor_b)
        cls.admin = cls.crear("admin_nuam", Rol.ADMINISTRADOR, None)
        cls.mercado = Mercado.objects.get(codigo="ACN")
        cls.instrumento = Instrumento.objects.create(mercado=cls.mercado, nemotecnico="FALABELLA")

    @staticmethod
    def crear(nombre, codigo_rol, corredor):
        return Usuario.objects.create_user(nombre, password=CLAVE, rol=Rol.objects.get(codigo=codigo_rol), corredor=corredor)

    def datos_basicos(self, **cambios):
        datos = {
            "mercado": self.mercado.pk, "ejercicio": 2025, "instrumento": self.instrumento.pk,
            "fecha_pago": date(2025, 5, 15).isoformat(), "secuencia": 10001, "descripcion": "Dividendo definitivo",
        }
        datos.update(cambios)
        return datos
