from django.contrib import admin

from .models import ConceptoTributario, Instrumento, Mercado

# Solo catálogos. Las calificaciones no se administran desde aquí: el administrador
# no puede ver ni modificar datos tributarios (sección 5.1 del informe).
admin.site.register(Mercado)
admin.site.register(Instrumento)
admin.site.register(ConceptoTributario)
