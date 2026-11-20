from django.contrib import admin
from django.urls import include, path

from usuarios.views import inicio

urlpatterns = [
    path("", inicio, name="inicio"),
    path("cuenta/", include("usuarios.urls")),
    path("calificaciones/", include("calificaciones.urls")),
    path("historial/", include("auditoria.urls")),
    path("admin/", admin.site.urls),
]
