from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from auditoria.services import registrar
from usuarios.permisos import requiere_permiso

from .calculo import COLUMNAS, ErrorCalculo, calcular_factores, suma_base, validar_factores
from .forms import DatosBasicosForm, FactoresForm, FiltroForm, ModificarDatosBasicosForm, MontosForm
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


@requiere_permiso("modificar")
@require_http_methods(["GET", "POST"])
def modificar(request, pk):
    """Modificación de calificación tributaria por Operador o Supervisor (HU03)."""
    calificacion = get_object_or_404(
        calificaciones_del_corredor(request.user).select_related("instrumento__mercado"),
        pk=pk,
    )
    conceptos = list(ConceptoTributario.objects.all())
    detalles_dict = {d.concepto.columna: d for d in calificacion.detalles.select_related("concepto")}

    accion = request.POST.get("accion") if request.method == "POST" else None
    datos = ModificarDatosBasicosForm(request.POST or None, instance=calificacion)
    montos = MontosForm(
        request.POST or None,
        initial={
            f"monto_{c}": detalles_dict[c].monto
            for c in COLUMNAS
            if c in detalles_dict and detalles_dict[c].monto is not None
        },
        conceptos=conceptos,
    )
    factores = FactoresForm(
        request.POST or None,
        initial={
            f"factor_{c}": f"{detalles_dict[c].factor:.8f}"
            for c in COLUMNAS
            if c in detalles_dict and detalles_dict[c].factor is not None
        },
        conceptos=conceptos,
    )
    paso = "datos"
    suma = suma_base({c: detalles_dict[c].factor for c in COLUMNAS if c in detalles_dict})

    if request.method == "POST":
        if accion == "calcular":
            if not montos.is_valid():
                paso = "montos"
            else:
                try:
                    calculados = calcular_factores(montos.montos())
                    factores = FactoresForm(
                        initial={f"factor_{c}": f"{v:.8f}" for c, v in calculados.items()},
                        conceptos=conceptos,
                    )
                    suma = suma_base(calculados)
                    paso = "factores"
                except ErrorCalculo as error:
                    messages.error(request, str(error))
                    paso = "montos"
        elif accion == "grabar":
            paso = "factores"
            datos_ok = datos.is_valid()
            montos_ok = montos.is_valid()
            factores_ok = factores.is_valid()

            if not datos_ok:
                paso = "datos"
            elif not montos_ok:
                paso = "montos"
            elif not factores_ok:
                paso = "factores"
            else:
                try:
                    validar_factores(factores.factores())
                    version_enviada = datos.cleaned_data["version"]
                    if version_enviada != calificacion.version:
                        msg_concurrencia = (
                            "Conflicto de concurrencia: la calificación fue modificada por otro usuario. "
                            "Por favor, recargue la página e intente nuevamente."
                        )
                        datos.add_error(None, msg_concurrencia)
                        messages.error(request, msg_concurrencia)
                        paso = "datos"
                    else:
                        cal_modificada = _guardar_modificacion(
                            request, calificacion, datos, montos.montos(), factores.factores(), conceptos
                        )
                        messages.success(request, f"Calificación {cal_modificada} modificada con éxito.")
                        return redirect("calificaciones:detalle", pk=calificacion.pk)
                except (ErrorCalculo, ValueError) as error:
                    messages.error(request, str(error))

            if factores.is_valid():
                suma = suma_base(factores.factores())

    return render(
        request,
        "calificaciones/modificar.html",
        {
            "calificacion": calificacion,
            "datos": datos,
            "montos": montos,
            "factores": factores,
            "paso": paso,
            "suma": suma,
        },
    )


@transaction.atomic
def _guardar_modificacion(request, calificacion, datos, montos, factores, conceptos):
    calificacion_db = (
        Calificacion.objects.select_for_update()
        .filter(pk=calificacion.pk, corredor=request.user.corredor, estado=Calificacion.VIGENTE)
        .first()
    )
    if not calificacion_db:
        raise Http404("La calificación no existe o fue eliminada.")

    if calificacion_db.version != datos.cleaned_data["version"]:
        raise ValueError(
            "Conflicto de concurrencia: la calificación fue modificada por otro usuario. "
            "Por favor, recargue la página e intente nuevamente."
        )

    cambios = []
    nueva_fecha = datos.cleaned_data["fecha_pago"]
    nueva_desc = datos.cleaned_data.get("descripcion", "")

    if calificacion_db.fecha_pago != nueva_fecha:
        cambios.append(("fecha_pago", str(calificacion_db.fecha_pago), str(nueva_fecha)))
        calificacion_db.fecha_pago = nueva_fecha

    desc_ant = calificacion_db.descripcion or ""
    desc_nue = nueva_desc or ""
    if desc_ant != desc_nue:
        cambios.append(("descripcion", desc_ant, desc_nue))
        calificacion_db.descripcion = desc_nue

    calificacion_db.version += 1
    calificacion_db.save(update_fields=["fecha_pago", "descripcion", "version", "modificado_en"])

    detalles_existentes = {d.concepto.columna: d for d in calificacion_db.detalles.select_related("concepto")}
    por_columna = {c.columna: c for c in conceptos}

    detalles_a_actualizar = []
    detalles_a_crear = []

    for c in COLUMNAS:
        m_nuevo = montos.get(c)
        f_nuevo = factores[c]
        detalle = detalles_existentes.get(c)

        if detalle:
            m_viejo = detalle.monto
            if m_viejo != m_nuevo:
                cambios.append((
                    f"monto_{c}",
                    "" if m_viejo is None else str(m_viejo),
                    "" if m_nuevo is None else str(m_nuevo),
                ))
                detalle.monto = m_nuevo

            f_viejo = detalle.factor
            if f_viejo != f_nuevo:
                cambios.append((f"factor_{c}", f"{f_viejo:.8f}", f"{f_nuevo:.8f}"))
                detalle.factor = f_nuevo

            detalles_a_actualizar.append(detalle)
        else:
            detalles_a_crear.append(
                DetalleCalificacion(
                    calificacion=calificacion_db,
                    concepto=por_columna[c],
                    monto=m_nuevo,
                    factor=f_nuevo,
                )
            )
            if m_nuevo is not None:
                cambios.append((f"monto_{c}", "", str(m_nuevo)))
            if f_nuevo:
                cambios.append((f"factor_{c}", "", f"{f_nuevo:.8f}"))

    if detalles_a_actualizar:
        DetalleCalificacion.objects.bulk_update(detalles_a_actualizar, fields=["monto", "factor"])
    if detalles_a_crear:
        DetalleCalificacion.objects.bulk_create(detalles_a_crear)

    registrar(request, "MODIFICAR", calificacion=calificacion_db, origen="MANUAL", cambios=cambios)
    return calificacion_db


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
