from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from auditoria.services import registrar

from .forms import LoginForm
from .models import Usuario

MENSAJE_GENERICO = "Usuario o contraseña incorrectos."


@require_http_methods(["GET", "POST"])
def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        nombre = form.cleaned_data["usuario"]
        clave = form.cleaned_data["clave"]
        cuenta = Usuario.objects.filter(username=nombre).first()

        if cuenta and cuenta.esta_bloqueado():
            registrar(request, "LOGIN_RECHAZADO_BLOQUEO", usuario=cuenta)
            messages.error(request, "La cuenta está bloqueada temporalmente. Intente más tarde.")
            return render(request, "usuarios/login.html", {"form": form})

        usuario = authenticate(request, username=nombre, password=clave)
        # Solo entran cuentas con rol asignado; los roles de negocio además deben tener corredor.
        habilitado = usuario is not None and usuario.rol_id and (usuario.corredor_id or usuario.tiene_rol("ADMINISTRADOR"))
        if habilitado:
            usuario.registrar_exito()
            login(request, usuario)
            registrar(request, "LOGIN", usuario=usuario)
            return redirect("inicio")

        if cuenta:
            if cuenta.registrar_fallo():
                registrar(request, "BLOQUEO_CUENTA", usuario=cuenta)
            else:
                registrar(request, "LOGIN_FALLIDO", usuario=cuenta)
        messages.error(request, MENSAJE_GENERICO)

    return render(request, "usuarios/login.html", {"form": form})


def inicio(request):
    """Página de entrada según el rol: el administrador no ve calificaciones."""
    if not request.user.is_authenticated:
        return redirect("usuarios:login")
    if request.user.tiene_rol("ADMINISTRADOR"):
        return redirect("auditoria:historial")
    return redirect("calificaciones:mantenedor")


@require_POST
def cerrar_sesion(request):
    if request.user.is_authenticated:
        registrar(request, "LOGOUT")
    logout(request)
    return redirect("usuarios:login")
