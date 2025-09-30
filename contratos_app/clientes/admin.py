from django.contrib import admin
from .models import ClienteLocal, Contrato

@admin.register(ClienteLocal)
class ClienteLocalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'correo', 'telefono', 'identificador_externo')  # quitar fecha_registro
    search_fields = ('nombre', 'correo', 'telefono', 'identificador_externo')

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'tipo', 'fecha_generacion')
    search_fields = ('cliente__nombre', 'tipo')
