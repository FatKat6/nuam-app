"""
Crea datos de prueba para la revisión del docente:
dos corredoras, un usuario por rol, instrumentos y una calificación de ejemplo
(el ejemplo del cliente del HDU).

Uso:  python manage.py cargar_demo --clave "UnaClaveSegura2026"
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from calificaciones.calculo import calcular_factores
from calificaciones.models import Calificacion, ConceptoTributario, DetalleCalificacion, Instrumento, Mercado
from usuarios.models import Corredor, Rol, Usuario

USUARIOS = [
    ("operador_a", "Ana", "Operadora", "A", Rol.OPERADOR),
    ("supervisor_a", "Sergio", "Supervisor", "A", Rol.SUPERVISOR),
    ("auditor_a", "Andrea", "Auditora", "A", Rol.AUDITOR),
    ("operador_b", "Bruno", "Operador", "B", Rol.OPERADOR),
    ("admin_nuam", "Admin", "nuam", None, Rol.ADMINISTRADOR),
]

INSTRUMENTOS = [("ACN", "FALABELLA"), ("ACN", "COPEC"), ("ACN", "SQM-B"), ("CFI", "CFIMLDL"), ("FMU", "BCI-AHORRO")]

MONTOS_EJEMPLO = {8: Decimal("192770580"), 9: Decimal("64161878"), 10: Decimal("0"), 11: Decimal("111812860"),
                  25: Decimal("71298705"), 30: Decimal("15837333")}


class Command(BaseCommand):
    help = "Carga corredoras, usuarios de prueba (uno por rol) y una calificación de ejemplo."

    def add_arguments(self, parser):
        parser.add_argument("--clave", required=True, help="Contraseña común para los usuarios de prueba.")

    @transaction.atomic
    def handle(self, *args, clave, **opciones):
        try:
            validate_password(clave)
        except Exception as error:
            raise CommandError(f"La contraseña no cumple la política: {error}")

        corredores = {
            "A": Corredor.objects.get_or_create(rut="76.111.111-1", defaults={"nombre": "Corredora Andes S.A."})[0],
            "B": Corredor.objects.get_or_create(rut="76.222.222-2", defaults={"nombre": "Corredora Bío Bío S.A."})[0],
        }
        for nombre, nombre_pila, apellido, letra, codigo in USUARIOS:
            usuario, _ = Usuario.objects.get_or_create(username=nombre)
            usuario.first_name, usuario.last_name = nombre_pila, apellido
            usuario.corredor = corredores.get(letra)
            usuario.rol = Rol.objects.get(codigo=codigo)
            usuario.set_password(clave)
            usuario.is_staff = codigo == Rol.ADMINISTRADOR
            usuario.save()
            if codigo == Rol.ADMINISTRADOR:
                # El administrador gestiona usuarios en /admin/, sin acceso a calificaciones.
                permisos = Permission.objects.filter(content_type__app_label="usuarios",
                                                     codename__in=["view_usuario", "add_usuario", "change_usuario", "view_corredor", "view_rol"])
                usuario.user_permissions.set(permisos)

        for mercado, nemo in INSTRUMENTOS:
            Instrumento.objects.get_or_create(mercado=Mercado.objects.get(codigo=mercado), nemotecnico=nemo)

        operador = Usuario.objects.get(username="operador_a")
        cal, creada = Calificacion.objects.get_or_create(
            corredor=corredores["A"], ejercicio=2025, instrumento=Instrumento.objects.get(nemotecnico="FALABELLA"), secuencia=10001,
            defaults={"fecha_pago": date(2025, 5, 15), "descripcion": "Dividendo definitivo (ejemplo del cliente)", "creado_por": operador},
        )
        if creada:
            factores = calcular_factores(MONTOS_EJEMPLO)
            conceptos = {c.columna: c for c in ConceptoTributario.objects.all()}
            DetalleCalificacion.objects.bulk_create(
                DetalleCalificacion(calificacion=cal, concepto=conceptos[c], monto=MONTOS_EJEMPLO.get(c), factor=f)
                for c, f in factores.items()
            )

        self.stdout.write(self.style.SUCCESS("Datos de prueba cargados:"))
        for nombre, *_ , letra, codigo in USUARIOS:
            self.stdout.write(f"  {nombre:<14} {codigo:<14} corredora {letra or '-'}")
