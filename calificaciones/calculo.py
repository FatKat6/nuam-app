"""
Servicio único de cálculo y validación de factores (HU02).

Lo usan el ingreso manual y, más adelante, la modificación y la carga masiva,
para que la regla de negocio exista en un solo lugar.

Regla definida por el equipo:
- Cada factor = monto de su columna / suma de los montos de las columnas 8 a 19,
  redondeado al octavo decimal.
- La suma de los factores 8 al 19 no puede superar 1.
- Si por redondeo esa suma supera 1, la diferencia se descuenta del factor mayor.
"""
from decimal import ROUND_HALF_UP, Decimal

COLUMNAS = range(8, 38)          # columnas tributarias 8 a 37
COLUMNAS_BASE = range(8, 20)     # base de cálculo: columnas 8 a 19
ULTIMA_COLUMNA_VALIDACION = 19
OCHO_DECIMALES = Decimal("0.00000001")
UNO = Decimal("1")
CERO = Decimal("0")


class ErrorCalculo(ValueError):
    """Error de negocio que se muestra al usuario."""


def _decimal(valor):
    if valor in (None, ""):
        return CERO
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def calcular_factores(montos):
    """Recibe {columna: monto} y devuelve {columna: factor} para las columnas 8 a 37."""
    montos = {c: _decimal(montos.get(c)) for c in COLUMNAS}
    if any(m < 0 for m in montos.values()):
        raise ErrorCalculo("Los montos no pueden ser negativos.")

    base = sum(montos[c] for c in COLUMNAS_BASE)
    if base == 0:
        raise ErrorCalculo("No hay montos en las columnas 8 a 19: no existe base para calcular los factores.")

    factores = {c: (montos[c] / base).quantize(OCHO_DECIMALES, rounding=ROUND_HALF_UP) for c in COLUMNAS}

    exceso = suma_base(factores) - UNO
    if exceso > 0:
        mayor = max(COLUMNAS_BASE, key=lambda c: factores[c])
        factores[mayor] -= exceso
    return factores


def suma_base(factores):
    return sum(_decimal(factores.get(c)) for c in COLUMNAS_BASE)


def validar_factores(factores):
    """Valida factores calculados o editados a mano. Lanza ErrorCalculo si no cumplen."""
    for c in COLUMNAS:
        f = _decimal(factores.get(c))
        if f < 0 or f > 1:
            raise ErrorCalculo(f"El factor de la columna {c} debe estar entre 0 y 1.")
    total = suma_base(factores)
    if total > UNO:
        raise ErrorCalculo(f"La suma de los factores 8 al {ULTIMA_COLUMNA_VALIDACION} es {total} y no puede superar 1.")
    return total
