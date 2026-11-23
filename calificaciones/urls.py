from django.urls import path

from . import views

app_name = "calificaciones"

urlpatterns = [
    path("", views.mantenedor, name="mantenedor"),
    path("ingresar/", views.ingresar, name="ingresar"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/modificar/", views.modificar, name="modificar"),
    path("<int:pk>/eliminar/", views.eliminar, name="eliminar"),
]
