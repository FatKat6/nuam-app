from decimal import Decimal

from django import forms

from .calculo import COLUMNAS
from .models import Calificacion, Instrumento, Mercado

ATTR = {"class": "form-control form-control-sm"}


class DatosBasicosForm(forms.ModelForm):
    mercado = forms.ModelChoiceField(queryset=Mercado.objects.all(), widget=forms.Select(attrs={"class": "form-select form-select-sm"}))

    class Meta:
        model = Calificacion
        fields = ["mercado", "ejercicio", "instrumento", "fecha_pago", "secuencia", "descripcion"]
        widgets = {
            "ejercicio": forms.NumberInput(attrs=ATTR),
            "instrumento": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "fecha_pago": forms.DateInput(attrs={**ATTR, "type": "date"}, format="%Y-%m-%d"),
            "secuencia": forms.NumberInput(attrs=ATTR),
            "descripcion": forms.TextInput(attrs=ATTR),
        }

    def __init__(self, *args, corredor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.corredor = corredor
        self.fields["instrumento"].queryset = Instrumento.objects.select_related("mercado")

    def clean_ejercicio(self):
        ejercicio = self.cleaned_data["ejercicio"]
        if not 1000 <= ejercicio <= 9999:
            raise forms.ValidationError("El ejercicio debe tener cuatro dígitos.")
        return ejercicio

    def clean_secuencia(self):
        secuencia = self.cleaned_data["secuencia"]
        if secuencia <= 10000:
            raise forms.ValidationError("La secuencia del evento debe ser mayor a 10.000.")
        return secuencia

    def clean(self):
        datos = super().clean()
        mercado, instrumento = datos.get("mercado"), datos.get("instrumento")
        if mercado and instrumento and instrumento.mercado_id != mercado.id:
            self.add_error("instrumento", "El instrumento no pertenece al mercado seleccionado.")
        if self.corredor and instrumento and datos.get("ejercicio") and datos.get("secuencia"):
            existe = Calificacion.objects.filter(
                corredor=self.corredor, ejercicio=datos["ejercicio"], instrumento=instrumento, secuencia=datos["secuencia"]
            ).exists()
            if existe:
                raise forms.ValidationError("Ya existe una calificación con ese ejercicio, instrumento y secuencia del evento.")
        return datos


class MontosForm(forms.Form):
    """Montos de las columnas 8 a 37 tal como figuran en el certificado."""

    def __init__(self, *args, conceptos=None, **kwargs):
        super().__init__(*args, **kwargs)
        nombres = {c.columna: c.nombre for c in (conceptos or [])}
        for c in COLUMNAS:
            self.fields[f"monto_{c}"] = forms.DecimalField(
                label=f"{c}. {nombres.get(c, '')}", required=False, max_digits=18, decimal_places=2,
                min_value=Decimal("0"), widget=forms.TextInput(attrs={**ATTR, "inputmode": "decimal"}),
            )

    def montos(self):
        return {c: self.cleaned_data.get(f"monto_{c}") for c in COLUMNAS}


class FactoresForm(forms.Form):
    """Factores calculados, editables antes de grabar."""

    def __init__(self, *args, conceptos=None, **kwargs):
        super().__init__(*args, **kwargs)
        nombres = {c.columna: c.nombre for c in (conceptos or [])}
        for c in COLUMNAS:
            self.fields[f"factor_{c}"] = forms.DecimalField(
                label=f"{c}. {nombres.get(c, '')}", max_digits=9, decimal_places=8,
                min_value=Decimal("0"), max_value=Decimal("1"),
                widget=forms.TextInput(attrs={**ATTR, "inputmode": "decimal"}),
            )

    def factores(self):
        return {c: self.cleaned_data.get(f"factor_{c}") for c in COLUMNAS}


class FiltroForm(forms.Form):
    mercado = forms.ModelChoiceField(queryset=Mercado.objects.all(), required=False, empty_label="Todos",
                                     widget=forms.Select(attrs={"class": "form-select form-select-sm"}))
    origen = forms.ChoiceField(choices=[("", "Todos")] + Calificacion.ORIGENES, required=False,
                               widget=forms.Select(attrs={"class": "form-select form-select-sm"}))
    ejercicio = forms.IntegerField(label="Período comercial", required=False, min_value=1000, max_value=9999,
                                   widget=forms.NumberInput(attrs=ATTR))
