from .permisos import PERMISOS, puede


def permisos(request):
    """Expone a las plantillas qué acciones puede ver el usuario (solo para mostrar u ocultar botones)."""
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {"puede": {}}
    return {"puede": {accion: puede(usuario, accion) for accion in PERMISOS}}
