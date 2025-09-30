from django.core.management.base import BaseCommand
import requests
from clientes.models import Cliente

class Command(BaseCommand):
    help = 'Sincroniza clientes desde la API y los guarda en la base de datos local'

    def handle(self, *args, **kwargs):
        
        url = "https://api.empresa.com/clientes"  

        try:
            response = requests.get(url)
            response.raise_for_status()  # lanza error si la petición falla
            clientes_data = response.json()

            for data in clientes_data:
                # Guardamos o actualizamos los clientes
                cliente, created = Cliente.objects.update_or_create(
                    correo=data.get("correo"),  # 👈 campo único de referencia
                    defaults={
                        "nombre": data.get("nombre"),
                        "apellido": data.get("apellido"),
                        "telefono": data.get("telefono"),
                        "direccion": data.get("direccion"),
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Cliente creado: {cliente}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Cliente actualizado: {cliente}"))

            self.stdout.write(self.style.SUCCESS("✅ Sincronización completada."))

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Error al conectar con la API: {e}"))
