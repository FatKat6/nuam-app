from .models import DetalleLog, LogAuditoria


def ip_cliente(request):
    # Detrás de Nginx la IP real llega en X-Real-IP (lo fija Nginx, no el navegador).
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def registrar(request, accion, usuario=None, calificacion=None, origen="SISTEMA", cambios=None):
    """Inserta un registro en el log. `cambios` es una lista de (campo, anterior, nuevo)."""
    if usuario is None and getattr(request, "user", None) is not None and request.user.is_authenticated:
        usuario = request.user
    log = LogAuditoria.objects.create(
        usuario=usuario,
        corredor=getattr(usuario, "corredor", None),
        accion=accion,
        origen=origen,
        calificacion=calificacion,
        ip=ip_cliente(request),
    )
    if cambios:
        DetalleLog.objects.bulk_create(
            DetalleLog(log=log, campo=campo, valor_anterior=str(antes)[:255], valor_nuevo=str(despues)[:255])
            for campo, antes, despues in cambios
        )
    return log
