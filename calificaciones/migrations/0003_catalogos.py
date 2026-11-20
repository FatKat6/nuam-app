"""Catálogos fijos: mercados y las 30 columnas tributarias del certificado N° 70 (HDU, hoja 3)."""
from django.db import migrations

MERCADOS = [("ACN", "Acciones"), ("CFI", "Cuotas de fondos de inversión"), ("FMU", "Fondos mutuos")]

CONCEPTOS = {
    8: "Con crédito por IDPC generados a contar del 01.01.2017",
    9: "Con crédito por IDPC acumulados hasta el 31.12.2016",
    10: "Con derecho a crédito por pago de IDPC voluntario",
    11: "Sin derecho a crédito",
    12: "Rentas provenientes del registro RAP y diferencia inicial de sociedad acogida al ex Art. 14 TER A",
    13: "Otras rentas percibidas sin prioridad en su orden de imputación",
    14: "Exceso distribuciones desproporcionadas (N° 9 Art. 14 A)",
    15: "Utilidades afectadas con impuesto sustitutivo al FUT (ISFUT) Ley N° 20.780",
    16: "Rentas generadas hasta el 31.12.1983 y/o utilidades afectadas con impuesto sustitutivo",
    17: "Rentas exentas de IGC (Art. 11, Ley 18.401), afectas a impuesto adicional",
    18: "Rentas exentas de IGC y/o impuesto adicional (IA)",
    19: "Ingresos no constitutivos de renta",
    20: "No sujetos a restitución generados hasta el 31.12.2019, sin derecho a devolución",
    21: "No sujetos a restitución generados hasta el 31.12.2019, con derecho a devolución",
    22: "No sujetos a restitución generados a contar del 01.01.2020, sin derecho a devolución",
    23: "No sujetos a restitución generados a contar del 01.01.2020, con derecho a devolución",
    24: "Sujetos a restitución, sin derecho a devolución",
    25: "Sujetos a restitución, con derecho a devolución",
    26: "Sujetos a restitución (2), sin derecho a devolución",
    27: "Sujetos a restitución (2), con derecho a devolución",
    28: "Crédito por IPE",
    29: "Asociados a rentas afectas, sin derecho a devolución",
    30: "Asociados a rentas afectas, con derecho a devolución",
    31: "Asociados a rentas exentas (Art. 11, Ley 18.401), sin derecho a devolución",
    32: "Asociados a rentas exentas (Art. 11, Ley 18.401), con derecho a devolución",
    33: "Crédito por IPE (rentas exentas)",
    34: "Tasa efectiva del crédito del FUT (TEF)",
    35: "Tasa efectiva del crédito del FUNT (TEX)",
    36: "Devolución de capital Art. 17 N° 7 LIR",
    37: "Crédito por impuesto tasa adicional, ex Art. 21 LIR",
}


def cargar(apps, schema_editor):
    Mercado = apps.get_model("calificaciones", "Mercado")
    Concepto = apps.get_model("calificaciones", "ConceptoTributario")
    for codigo, nombre in MERCADOS:
        Mercado.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre})
    for columna, nombre in CONCEPTOS.items():
        Concepto.objects.update_or_create(columna=columna, defaults={"nombre": nombre, "es_base_calculo": 8 <= columna <= 19})


class Migration(migrations.Migration):
    dependencies = [("calificaciones", "0002_initial")]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
