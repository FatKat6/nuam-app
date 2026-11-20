"""Pruebas unitarias del servicio de cálculo (sección 6.2 del informe, PU-01 a PU-06)."""
from decimal import Decimal as D

from django.test import SimpleTestCase

from calificaciones.calculo import ErrorCalculo, calcular_factores, suma_base, validar_factores
from calificaciones.forms import DatosBasicosForm

# Ejemplo del cliente (HDU, hoja "3.2 Homologación columnas")
MONTOS_CLIENTE = {8: D("192770580"), 9: D("64161878"), 10: D("0"), 11: D("111812860"), 25: D("71298705"), 30: D("15837333")}


class CalculoTests(SimpleTestCase):
    def test_pu01_ejemplo_del_cliente(self):
        f = calcular_factores(MONTOS_CLIENTE)
        self.assertEqual(f[8], D("0.52277431"))
        self.assertEqual(f[9], D("0.17400052"))
        self.assertEqual(f[10], D("0.00000000"))
        self.assertEqual(f[11], D("0.30322517"))
        self.assertEqual(suma_base(f), D("1.00000000"))

    def test_pu02_creditos_sobre_la_misma_base(self):
        f = calcular_factores(MONTOS_CLIENTE)
        self.assertEqual(f[25], D("0.19335488"))
        self.assertEqual(f[30], D("0.04294924"))

    def test_pu03_division_por_cero(self):
        with self.assertRaisesMessage(ErrorCalculo, "No hay montos en las columnas 8 a 19"):
            calcular_factores({c: D("0") for c in range(8, 20)})

    def test_pu04_suma_mayor_que_1(self):
        factores = {c: D("0") for c in range(8, 38)}
        factores.update({8: D("0.60000000"), 9: D("0.50000000")})
        with self.assertRaisesMessage(ErrorCalculo, "no puede superar 1"):
            validar_factores(factores)

    def test_pu05_redondeo(self):
        f = calcular_factores({8: D("100"), 9: D("100"), 10: D("100")})
        self.assertEqual([f[8], f[9], f[10]], [D("0.33333333")] * 3)
        self.assertEqual(validar_factores(f), D("0.99999999"))

    def test_pu06_secuencia_invalida(self):
        form = DatosBasicosForm(data={"secuencia": 9999})
        form.is_valid()
        self.assertIn("mayor a 10.000", str(form.errors["secuencia"]))

    def test_redondeo_que_supera_1_se_descuenta_del_mayor(self):
        # 2/3 y 1/3 redondeados dan 0,66666667 + 0,33333333 = 1,00000000 (no hay exceso);
        # con 6 montos iguales a 1/6 cada factor redondea a 0,16666667 y la suma excede en 0,00000002.
        f = calcular_factores({c: D("1") for c in range(8, 14)})
        self.assertEqual(suma_base(f), D("1.00000000"))
        self.assertEqual(f[8], D("0.16666665"))

    def test_montos_negativos(self):
        with self.assertRaises(ErrorCalculo):
            calcular_factores({8: D("-1"), 9: D("10")})

    def test_columnas_fuera_de_la_base_no_entran_en_la_suma(self):
        f = {c: D("0") for c in range(8, 38)}
        f.update({8: D("1"), 20: D("0.9")})
        self.assertEqual(validar_factores(f), D("1"))
