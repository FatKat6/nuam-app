from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Corredor, Rol, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "corredor", "rol", "is_active", "bloqueado_hasta")
    list_filter = ("corredor", "rol", "is_active")
    fieldsets = UserAdmin.fieldsets + (("nuam", {"fields": ("corredor", "rol", "intentos_fallidos", "bloqueado_hasta")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("nuam", {"fields": ("corredor", "rol")}),)

    def has_delete_permission(self, request, obj=None):
        # Las cuentas se desactivan, no se borran, para conservar la trazabilidad.
        return False


admin.site.register(Corredor)
admin.site.register(Rol)
admin.site.site_header = "nuam · Administración de usuarios"
