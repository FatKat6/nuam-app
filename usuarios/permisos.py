"""Matriz de permisos por rol (sección 5.1 del informe) y decorador para las vistas."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Rol

OP, SUP, ADM, AUD = Rol.OPERADOR, Rol.SUPERVISOR, Rol.ADMINISTRADOR, Rol.AUDITOR

PERMISOS = {
    "buscar": {OP, SUP, AUD},
    "ingresar": {OP, SUP},
    "modificar": {OP, SUP},
    "eliminar": {SUP},
    "cargar": {OP, SUP},
    "historial": {SUP, ADM, AUD},
    "usuarios": {ADM},
}


def puede(usuario, accion):
    return bool(usuario.is_authenticated and usuario.is_active and usuario.codigo_rol in PERMISOS[accion])


def requiere_permiso(accion):
    """Exige sesión iniciada y que el rol tenga el permiso. Se verifica en el servidor en cada petición."""

    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not puede(request.user, accion):
                raise PermissionDenied
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
