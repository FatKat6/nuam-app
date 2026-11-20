from django.db import migrations

ROLES = [
    ("OPERADOR", "Operador tributario"),
    ("SUPERVISOR", "Supervisor tributario"),
    ("ADMINISTRADOR", "Administrador"),
    ("AUDITOR", "Auditor"),
]


def cargar(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    for codigo, nombre in ROLES:
        Rol.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre})


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0001_initial")]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
