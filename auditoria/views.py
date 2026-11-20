from django.core.paginator import Paginator
from django.shortcuts import render

from usuarios.permisos import requiere_permiso

from .models import LogAuditoria


@requiere_permiso("historial")
def historial(request):
    """Historial de cambios (versión básica; HU05 se completa en el Sprint 4)."""
    registros = LogAuditoria.objects.select_related("usuario", "calificacion__instrumento").prefetch_related("detalles")
    # El administrador no pertenece necesariamente a un corredor; el resto ve solo el suyo.
    if request.user.corredor_id:
        registros = registros.filter(corredor_id=request.user.corredor_id)
    pagina = Paginator(registros, 25).get_page(request.GET.get("page"))
    return render(request, "auditoria/historial.html", {"pagina": pagina})
