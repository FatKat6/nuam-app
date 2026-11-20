from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from auditoria.services import registrar
from usuarios.permisos import requiere_permiso

from .calculo import COLUMNAS, ErrorCalculo, calcular_factores, suma_base, validar_factores
from .forms import DatosBasicosForm, FactoresForm, FiltroForm, MontosForm
from .models import Calificacion, ConceptoTributario, DetalleCalificacion


def calificaciones_del_corredor(usuario):
    """Filtro común por corredor: se aplica en el servidor y nunca depende de datos del navegador."""
    return Calificacion.objects.filter(corredor_id=usuario.corredor_id, estado=Calificacion.VIGENTE)


@requiere_permiso("buscar")
def mantenedor(request):
    filtro = FiltroForm(request.GET or None)
    qs = calificaciones_del_corredor(request.user).select_related("instrumento__mercado").prefetch_related("detalles__concepto")
    if filtro.is_valid():
        if filtro.cleaned_data["mercado"]:
            qs = qs.filter(instrumento__mercado=filtro.cleaned_data["mercado"])
        if filtro.cleaned_data["origen"]:
            qs = qs.filter(origen=filtro.cleaned_data["origen"])
        if filtro.cleaned_data["ejercicio"]:
            qs = qs.filter(ejercicio=filtro.cleaned_data["ejercicio"])
    pagina = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "calificaciones/mantenedor.html", {
        "filtro": filtro, "pagina": pagina, "columnas_grilla": range(8, 12),
    })


@requiere_permiso("ingresar")
@require_http_methods(["GET", "POST"])
def ingresar(request):
    """Ingreso por montos en tres pasos: datos básicos, montos y factores (HU02)."""
    conceptos = list(ConceptoTributario.objects.all())
    corredor = request.user.corredor
    accion = request.POST.get("accion")
    datos = DatosBasicosForm(request.POST or None, corredor=corredor)
    montos = MontosForm(request.POST or None, conceptos=conceptos)
    factores = FactoresForm(conceptos=conceptos)
    paso = "datos"
    suma = None

    if request.method == "POST":
        datos_ok, montos_ok = datos.is_valid(), montos.is_valid()
        if not datos_ok:
            paso = "datos"
        elif not montos_ok:
            paso = "montos"
        elif accion == "calcular":
            paso = "montos"
            try:
                calculados = calcular_factores(montos.montos())
                factores = FactoresForm(initial={f"factor_{c}": f"{v:.8f}" for c, v in calculados.items()}, conceptos=conceptos)
                suma = suma_base(calculados)
                paso = "factores"
            except ErrorCalculo as error:
                messages.error(request, str(error))
        elif accion == "grabar":
            factores = FactoresForm(request.POST, conceptos=conceptos)
            paso = "factores"
            if factores.is_valid():
                try:
                    validar_factores(factores.factores())
                    calificacion = _grabar(request, datos, montos.montos(), factores.factores(), conceptos)
                    messages.success(request, f"Calificación {calificacion} grabada.")
                    return redirect("calificaciones:mantenedor")
                except ErrorCalculo as error:
                    messages.error(request, str(error))
                suma = suma_base(factores.factores())

    return render(request, "calificaciones/ingresar.html", {
        "datos": datos, "montos": montos, "factores": factores, "paso": paso, "suma": suma,
    })


@transaction.atomic
def _grabar(request, datos, montos, factores, conceptos):
    calificacion = datos.save(commit=False)
    calificacion.corredor = request.user.corredor
    calificacion.creado_por = request.user
    calificacion.origen = Calificacion.ORIGEN_MANUAL
    calificacion.save()
    por_columna = {c.columna: c for c in conceptos}
    DetalleCalificacion.objects.bulk_create(
        DetalleCalificacion(calificacion=calificacion, concepto=por_columna[c], monto=montos.get(c), factor=factores[c])
        for c in COLUMNAS
    )
    cambios = [(f"factor_{c}", "", factores[c]) for c in COLUMNAS if factores[c]]
    registrar(request, "INGRESO", calificacion=calificacion, origen="MANUAL", cambios=cambios)
    return calificacion


@requiere_permiso("buscar")
def detalle(request, pk):
    # Si la calificación es de otro corredor, se responde como si no existiera (404).
    calificacion = get_object_or_404(calificaciones_del_corredor(request.user).select_related("instrumento__mercado"), pk=pk)
    detalles = calificacion.detalles.select_related("concepto")
    return render(request, "calificaciones/detalle.html", {
        "calificacion": calificacion, "detalles": detalles, "suma": suma_base(calificacion.factores()),
    })


@requiere_permiso("eliminar")
@require_POST
def eliminar(request, pk):
    """Eliminación lógica (versión básica; HU03 se completa en el Sprint 4)."""
    calificacion = get_object_or_404(calificaciones_del_corredor(request.user), pk=pk)
    calificacion.estado = Calificacion.ELIMINADA
    calificacion.version += 1
    calificacion.save(update_fields=["estado", "version", "modificado_en"])
    registrar(request, "ELIMINACION", calificacion=calificacion, origen="MANUAL",
              cambios=[("estado", Calificacion.VIGENTE, Calificacion.ELIMINADA)])
    messages.success(request, f"Calificación {calificacion} eliminada.")
    return redirect("calificaciones:mantenedor")
