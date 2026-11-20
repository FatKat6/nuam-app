import ipaddress

from .models import DetalleLog, LogAuditoria


def ip_cliente(request):
    """IP del cliente. Detrás de Nginx llega en X-Real-IP (lo fija Nginx, no el navegador).

    Se toma el primer valor y se valida; si no es una IP válida se guarda vacío en vez de fallar.
    """
    valor = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or ""
    valor = valor.split(",")[0].strip()
    try:
        return str(ipaddress.ip_address(valor))
    except ValueError:
        return None


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
