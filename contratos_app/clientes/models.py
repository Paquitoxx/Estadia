from django.db import models

class ClienteLocal(models.Model):
    nombre = models.CharField(max_length=200)
    correo = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    identificador_externo = models.CharField(max_length=100, null=True, blank=True)  # ID desde la API
    direccion = models.TextField(null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    foto_ine = models.ImageField(upload_to='ines/', null=True, blank=True)
    firma_imagen = models.ImageField(upload_to='firmas/', null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.identificador_externo or self.id})"


class Contrato(models.Model):
    cliente = models.ForeignKey(ClienteLocal, on_delete=models.CASCADE, related_name='contratos')
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=100, default='Contrato de servicio')

    # Archivos exportados (Opcionales, por si usas PDF generator aparte)
    pdf = models.FileField(upload_to='contratos_pdf/', null=True, blank=True)
    excel = models.FileField(upload_to='contratos_xlsx/', null=True, blank=True)

    # Datos del contrato
    datos = models.JSONField(null=True, blank=True) # Guarda el JSON crudo de la API
    html_contenido = models.TextField(null=True, blank=True)  # 🔥 AQUÍ SE GUARDA LA CARÁTULA RENDERIZADA

    def __str__(self):
        return f"Contrato {self.id} - {self.cliente.nombre}"