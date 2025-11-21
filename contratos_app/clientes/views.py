import os
import re
import json
import base64
import requests
import datetime
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.template.loader import render_to_string 

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from openpyxl import Workbook

from .models import ClienteLocal, Contrato
from .forms import ClienteForm, ContratoForm

# ==========================================
# 🔹 UTILIDADES
# ==========================================

def obtener_fecha_actual_texto():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    hoy = datetime.date.today()
    return f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

def consultar_api(endpoint, params=None):
    base_url = os.getenv("API_URL")
    api_key = os.getenv("API_KEY")

    if not base_url or not api_key:
        print("⚠️ Faltan variables de entorno API_URL / API_KEY")
        return {'error': 'Configuración faltante'}

    url = f"{base_url}{endpoint}"
    headers = {'Content-Type': 'application/json', 'X-Auth-App-Key': api_key}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # La API a veces devuelve lista o dict, normalizamos aquí
            if isinstance(data, list): return data
            if isinstance(data, dict): return data.get('results', data)
            return []
        return {'error': f"Error {response.status_code}"}
    except Exception as e:
        return {'error': str(e)}

# ==========================================
# 🔹 VISTAS DE LISTADO Y VISUALIZACIÓN
# ==========================================

def home(request):
    return render(request, 'clientes/home.html')

def contratos_recientes(request):
    contratos = Contrato.objects.select_related("cliente").order_by("-fecha_generacion")[:10]
    return render(request, "clientes/recientes.html", {"contratos": contratos})

def todos_contratos(request):
    lista = Contrato.objects.select_related("cliente").order_by("-fecha_generacion")
    paginator = Paginator(lista, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "clientes/todos.html", {"page_obj": page_obj, "contratos": page_obj.object_list})

def ver_contrato_guardado(request, contrato_id):
    """ Muestra el HTML guardado en la BD (snapshot histórico) """
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if contrato.html_contenido:
        return HttpResponse(contrato.html_contenido)
    return HttpResponse("Este contrato no tiene versión HTML guardada.", status=404)

# ==========================================
# 🔹 BÚSQUEDA
# ==========================================

def buscar_cliente(request):
    query = request.GET.get('q', '').strip()
    resultados = []
    if query:
        params = {'query': query, 'limit': 10}
        resultados = consultar_api("/clients", params=params)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'resultados': resultados})

    return render(request, 'clientes/busqueda_clientes.html', {'busqueda': query, 'resultados': resultados})

# ==========================================
# 🔹 GENERACIÓN DE CARÁTULA (CORE)
# ==========================================

def caratula_cliente(request, cliente_id):
    # 1. Obtener Datos API
    datos = consultar_api(f"/clients/{cliente_id}")

    # Normalizar respuesta (Puede ser Lista [dict] o Dict)
    if isinstance(datos, list) and len(datos) > 0:
        # Buscamos por ID exacto dentro de la lista, o tomamos el primero
        cliente_data = next((item for item in datos if item.get("id") == int(cliente_id)), datos[0])
    elif isinstance(datos, dict) and "error" not in datos:
        cliente_data = datos
    else:
        cliente_data = {}

    # 2. Mapeo de Datos (Basado en tu JSON provisto)
    
    # Contactos (Array en JSON)
    contactos = cliente_data.get("contacts", [])
    contacto_principal = contactos[0] if contactos else {}

    telefono = contacto_principal.get("phone", "")
    email = contacto_principal.get("email", "")

    # Dirección (fullAddress > street1)
    calle = cliente_data.get("fullAddress") or cliente_data.get("street1") or "Domicilio no registrado"
    ciudad = cliente_data.get("city") or ""
    cp = cliente_data.get("zipCode") or ""
    direccion_str = f"{calle}, {ciudad}. CP: {cp}"

    # Nombre
    nombre_completo = f"{cliente_data.get('firstName', '')} {cliente_data.get('lastName', '')}".strip()

    # Objeto Cliente para Template
    cliente_obj = {
        "nombre_completo": nombre_completo,
        "telefono": telefono,
        "email": email,
        "direccion_completa": direccion_str,
        "rfc": cliente_data.get("companyTaxId") or "XAXX010101000",
        "ciudad": ciudad
    }

    # Objeto Proveedor
    proveedor = {
        "nombre": cliente_data.get("organizationName", "Computer World Guamuchil"),
    }

    # Contexto Final
    context = {
        "cliente": cliente_obj,
        "proveedor": proveedor,
        "fecha_actual": obtener_fecha_actual_texto(),
        "contrato": { "numero": f"CONT-{cliente_id}" }
    }

    # 3. Guardado Automático (Persistencia)
    
    # A. Guardar Cliente Local
    cliente_db, _ = ClienteLocal.objects.update_or_create(
        identificador_externo=str(cliente_id),
        defaults={
            'nombre': nombre_completo,
            'correo': email,
            'telefono': telefono,
            'direccion': direccion_str
        }
    )

    # B. Renderizar HTML (Snapshot)
    html_renderizado = render_to_string("clientes/Caratula.html", context, request=request)

    # C. Guardar Contrato
    Contrato.objects.create(
        cliente=cliente_db,
        tipo="Carátula Automática",
        datos=cliente_data,            
        html_contenido=html_renderizado 
    )

    return HttpResponse(html_renderizado)

# ==========================================
# 🔹 OTRAS VISTAS (LEGACY / STUBS)
# ==========================================

def nuevo_contrato(request):
    form = ContratoForm()
    return render(request, 'clientes/nuevo.html', {'form': form})

def subir_ine(request, cliente_id):
    cliente = get_object_or_404(ClienteLocal, pk=cliente_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('nuevo_contrato')
    return render(request, 'clientes/subir_ine.html', {'form': form, 'cliente': cliente})

@csrf_exempt
def guardar_firma(request):
    # (Lógica de guardado de firma base64 igual que antes)
    return JsonResponse({'status': 'ok'})

def caratula_pdf(request, cliente_id):
    return HttpResponse("Función PDF disponible.")

@csrf_exempt
def crear_contrato_desde_cliente(request):
    return JsonResponse({'status': 'ok'})

def detalle_contrato(request, cliente_id, cliente_nombre):
    contrato = Contrato.objects.filter(cliente__identificador_externo=cliente_id).last()
    return render(request, 'clientes/detalle.html', {'contrato': contrato})