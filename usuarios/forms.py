from django import forms


class LoginForm(forms.Form):
    usuario = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control", "autofocus": True, "autocomplete": "username"}))
    clave = forms.CharField(label="Contraseña", max_length=128, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"}))
