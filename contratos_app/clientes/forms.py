from django import forms
from .models import ClienteLocal, Contrato

class ClienteForm(forms.ModelForm):
    class Meta:
        model = ClienteLocal
        fields = ['nombre', 'correo', 'telefono', 'direccion', 'foto_ine', 'firma_imagen']

class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['tipo']
