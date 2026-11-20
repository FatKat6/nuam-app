from django.contrib import admin

from .models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "corredor", "accion", "origen", "ip")
    list_filter = ("accion", "origen", "corredor")

    # Solo lectura: el log no se edita ni se borra.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
