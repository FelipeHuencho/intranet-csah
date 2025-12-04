from django import forms

class LoginForm(forms.Form):
    """
    Formulario de inicio de sesión.
    Se usa autocomplete="new-password" para evitar que el navegador
    reinyecte valores anteriores y genere problemas visuales o de cache.
    """

    rut = forms.CharField(
        label="",
        max_length=20,
        widget=forms.TextInput(attrs={
            # No usar "off" porque algunos navegadores lo ignoran
            "autocomplete": "new-password",
            "class": "input-field",
            "id": "id_rut",
            "placeholder": "",  
        }),
    )

    password = forms.CharField(
        label="",
        required=True,
        min_length=1,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "class": "input-field",
            "id": "id_password",
            "placeholder": "",
        }),
    )

    remember = forms.BooleanField(
        label="Recordarme",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "checkbox-field"
        }),
    )
