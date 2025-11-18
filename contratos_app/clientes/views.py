import os
import re
import json
import base64
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from openpyxl import Workbook

# Modelos y Formularios
from .models import ClienteLocal, Contrato
from .forms import ClienteForm, ContratoForm


# ============================================================
# 🔹 FUNCIONES DE APOYO
# ============================================================

def consultar_api(endpoint, params=None):
    """
    Función central para consultar la API CWG usando variables de entorno.
    """
    base_url = os.getenv("API_URL")
    api_key = os.getenv("API_KEY")

    if not base_url or not api_key:
        return {'error': 'Faltan variables de entorno API_URL o API_KEY'}

    url = f"{base_url}{endpoint}"
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-App-Key': api_key
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=8)

        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get('results', data)

            return []

        return {'error': f"Error {response.status_code} al consultar API"}

    except requests.exceptions.Timeout:
        return {'error': "La solicitud tardó demasiado."}

    except Exception as e:
        return {'error': f"Error inesperado: {str(e)}"}


# ============================================================
# 🔹 VISTAS PRINCIPALES
# ============================================================

def home(request):
    return render(request, 'clientes/home.html')


def contratos_recientes(request):
    contratos = Contrato.objects.order_by('-fecha_generacion')[:10]
    return render(request, 'clientes/recientes.html', {'contratos': contratos})


def todos_contratos(request):
    contratos = Contrato.objects.order_by('-fecha_generacion')
    return render(request, 'clientes/todos.html', {'contratos': contratos})


def nuevo_contrato(request):
    form = ContratoForm()
    return render(request, 'clientes/nuevo.html', {'form': form})


# ============================================================
# 🔹 BÚSQUEDA DE CLIENTES VIA API
# ============================================================

def buscar_cliente(request):
    query = request.GET.get('q', '').strip()
    resultados = []

    if query:
        params = {'query': query, 'limit': 10}
        resultados = consultar_api("/clients", params=params)

    # Si la petición es AJAX, devolver JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'resultados': resultados})

    return render(request, 'clientes/busqueda_clientes.html', {
        'busqueda': query,
        'resultados': resultados
    })


# ============================================================
# 🔹 CARÁTULA EN HTML
# ============================================================

def caratula_cliente(request, cliente_id):
    datos = consultar_api(f"/clients/{cliente_id}")

    if "error" in datos:
        datos = {}

    cliente_data = datos[0] if isinstance(datos, list) and datos else {}

    cliente = {
        'first_name': cliente_data.get('firstName', ''),
        'last_name': cliente_data.get('lastName', ''),
        'domicilio': {
            'calle': cliente_data.get('street1', ''),
            'colonia': cliente_data.get('street1', ''),
            'municipio': cliente_data.get('city', ''),
            'cp': cliente_data.get('zipCode', '')
        },
        'telefono': cliente_data.get('contacts', [{}])[0].get('phone', 'N/A'),
        'email': cliente_data.get('contacts', [{}])[0].get('email', 'N/A')
    }

    empresa = {
        'nombre_comercial': cliente_data.get('organizationName', 'N/A'),
        'razon_social': cliente_data.get('companyName', 'N/A'),
        'rfc': cliente_data.get('companyTaxId', 'N/A'),
        'telefono': cliente['telefono'],
        'domicilio': cliente['domicilio']['calle']
    }

    # Datos fijos de ejemplo
    paquete = {
        'descripcion': 'Internet Fijo 100Mbps',
        'tarifa': 450.0,
        'fecha_pago': '2025-10-16',
        'indefinido': True,
        'plazo': 0,
        'folio_ift': 'IFT12345',
        'mensualidad': 450.0,
        'reconexion': 'si',
        'reconexion_costo': 50.0
    }

    equipo = {
        'modem': {'marca':'TP-Link','modelo':'Archer C6','serie':'M123456789','cantidad':1,'garantia':'12 meses'},
        'antena': {'marca':'Ubiquiti','modelo':'NanoStation M2','serie':'A987654321','cantidad':1,'garantia':'12 meses'}
    }

    instalacion = {'domicilio': cliente['domicilio']['calle'], 'fecha':'2025-10-20', 'hora':'10:00', 'costo':0.0}
    pago = {'efectivo': True,'domiciliado': False,'transferencia': False,'deposito': False,'detalles': 'Pago mensual en efectivo'}
    tarjeta = {'autorizado': False,'meses': 0,'banco': '','numero': ''}

    context = {
        'cliente': cliente,
        'empresa': empresa,
        'paquete': paquete,
        'equipo': equipo,
        'instalacion': instalacion,
        'pago': pago,
        'tarjeta': tarjeta,
        'ciudad': cliente['domicilio']['municipio'],
        'dia': '16',
        'mes': 'Octubre',
        'anio': '2025',
        'contrato': {'numero': 'CON-2025-001'},
        'proveedor': {'nombre': 'Computer World Guamúchil'},
        'servicios': [],
        'conceptos': []
    }

    return render(request, 'clientes/Caratula.html', context)


# ============================================================
# 🔹 CARÁTULA PDF (REPORTLAB)
# ============================================================

def caratula_pdf(request, cliente_id):
    datos = consultar_api(f"/clients/{cliente_id}")
    cliente_data = datos[0] if isinstance(datos, list) and datos else {}

    context = {
        "cliente_id": cliente_id,
        "nombre_completo": f"{cliente_data.get('firstName', '')} {cliente_data.get('lastName', '')}",
        "domicilio": f"{cliente_data.get('street1', '')}, {cliente_data.get('city', '')}, CP: {cliente_data.get('zipCode', '')}",
        "paquete_desc": "Internet Fijo 100Mbps",
        "paquete_tarifa": "450.00",
        "fecha_contrato": "16 de Octubre de 2025"
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=caratula_{cliente_id}.pdf'

    p = canvas.Canvas(response, pagesize=LETTER)

    y = 750
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "CARÁTULA DE CONTRATO DE SERVICIO")

    y -= 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "DATOS DEL CLIENTE")
    y -= 20
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Cliente ID: {context['cliente_id']}")
    y -= 15
    p.drawString(50, y, f"Nombre: {context['nombre_completo']}")
    y -= 15
    p.drawString(50, y, f"Domicilio: {context['domicilio']}")

    y -= 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "DATOS DEL PAQUETE")
    y -= 20
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Descripción: {context['paquete_desc']}")
    y -= 15
    p.drawString(50, y, f"Tarifa Mensual: ${context['paquete_tarifa']}")
    y -= 15
    p.drawString(50, y, f"Fecha de Contrato: {context['fecha_contrato']}")

    p.showPage()
    p.save()

    return response


# ============================================================
# 🔹 GUARDAR FIRMA (CAMPO BASE64)
# ============================================================

@csrf_exempt
def guardar_firma(request):
    data = json.loads(request.body)
    cliente_id = data.get('cliente_id')
    data_url = data.get('imagen')

    if not cliente_id or not data_url:
        return JsonResponse({'status': 'error', 'msg': 'Falta cliente o imagen'}, status=400)

    cliente = get_object_or_404(ClienteLocal, pk=cliente_id)

    img_str = re.sub(r'^data:image/.+;base64,', '', data_url)
    img_data = base64.b64decode(img_str)

    filename = f"firma_{cliente.id}.png"
    cliente.firma_imagen.save(filename, ContentFile(img_data), save=True)

    return JsonResponse({'status': 'ok'})


# ============================================================
# 🔹 SUBIR INE
# ============================================================

def subir_ine(request, cliente_id):
    cliente = get_object_or_404(ClienteLocal, pk=cliente_id)

    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('nuevo_contrato')

    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'clientes/subir_ine.html', {
        'form': form,
        'cliente': cliente
    })


# ============================================================
# 🔹 GENERAR PDF Y EXCEL DEL CONTRATO
# ============================================================

def generar_pdf_contrato(contrato: Contrato):
    cliente = contrato.cliente
    ruta = os.path.join(settings.MEDIA_ROOT, f'contratos_pdf/contrato_{contrato.id}.pdf')
    os.makedirs(os.path.dirname(ruta), exist_ok=True)

    c = canvas.Canvas(ruta, pagesize=LETTER)
    y = 750

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Contrato de Servicio")

    y -= 40
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Cliente: {cliente.nombre}")

    y -= 20
    c.drawString(50, y, f"Correo: {cliente.correo or ''}")

    y -= 20
    c.drawString(50, y, f"Teléfono: {cliente.telefono or ''}")

    y -= 150

    if cliente.firma_imagen:
        try:
            c.drawImage(cliente.firma_imagen.path, 50, y, width=200, height=60)
        except:
            pass

    if cliente.foto_ine:
        try:
            c.drawImage(cliente.foto_ine.path, 300, y + 100, width=200, height=120)
        except:
            pass

    c.showPage()
    c.save()

    with open(ruta, 'rb') as f:
        contrato.pdf.save(os.path.basename(ruta), ContentFile(f.read()), save=True)

    return contrato.pdf.url


def generar_excel_contrato(contrato: Contrato):
    cliente = contrato.cliente

    wb = Workbook()
    ws = wb.active
    ws.title = "Contrato"

    ws.append(["Campo", "Valor"])
    ws.append(["Cliente", cliente.nombre])
    ws.append(["Correo", cliente.correo])
    ws.append(["Telefono", cliente.telefono])

    ruta = os.path.join(settings.MEDIA_ROOT, f'contratos_xlsx/contrato_{contrato.id}.xlsx')
    os.makedirs(os.path.dirname(ruta), exist_ok=True)

    wb.save(ruta)

    with open(ruta, 'rb') as f:
        contrato.excel.save(os.path.basename(ruta), ContentFile(f.read()), save=True)

    return contrato.excel.url


# ============================================================
# 🔹 CREAR CONTRATO DESDE UN CLIENTE
# ============================================================

def crear_contrato_desde_cliente(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'msg': 'POST requerido'}, status=400)

    cliente_id = request.POST.get('cliente_id')
    cliente = get_object_or_404(ClienteLocal, pk=cliente_id)

    contrato = Contrato.objects.create(
        cliente=cliente,
        tipo=request.POST.get('tipo', 'Contrato de servicio'),
        datos={}
    )

    generar_pdf_contrato(contrato)
    generar_excel_contrato(contrato)

    return JsonResponse({'status': 'ok', 'contrato_id': contrato.id})


# ============================================================
# 🔹 DETALLE DE CONTRATO
# ============================================================

def detalle_contrato(request, cliente_id, cliente_nombre):
    contrato = get_object_or_404(Contrato, pk=cliente_id)
    return render(request, 'clientes/detalle.html', {
        'contrato': contrato,
        'nombre_url': cliente_nombre
    })
