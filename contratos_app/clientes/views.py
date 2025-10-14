# Create your views here.

import base64, re, os
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from .models import ClienteLocal, Contrato
from .forms import ClienteForm, ContratoForm
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from openpyxl import Workbook
from django.core.files.base import ContentFile


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

import requests
from django.http import JsonResponse
from django.shortcuts import render

def buscar_cliente(request):
    query = request.GET.get('q', '')
    resultados = []

    if query:
        URL = "https://cwg.org.mx/crm/api/v1.0/clients"
        headers = {
            'Content-Type': 'application/json',
            'X-Auth-App-Key': ''  # ← Coloca aquí tu API key real
        }
        params = {
            'query': query,
            'limit': 10
        }

        try:
            respuesta = requests.get(URL, headers=headers, params=params, timeout=10)
            if respuesta.status_code == 200:
                datos = respuesta.json()

                # ✅ La API puede devolver lista o diccionario
                if isinstance(datos, list):
                    resultados = datos
                elif isinstance(datos, dict):
                    resultados = datos.get('results', [])
                else:
                    resultados = []
            else:
                resultados = [{'error': f'Error {respuesta.status_code} al consultar la API'}]
        except Exception as e:
            resultados = [{'error': str(e)}]

    # ✅ Si es una solicitud AJAX (fetch desde JS), devolvemos JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'resultados': resultados})

    # ✅ Si no es AJAX, renderizamos la plantilla completa
    return render(request, 'clientes/busqueda_clientes.html', {
        'busqueda': query,
        'resultados': resultados
    })


@csrf_exempt
def guardar_firma(request):
    # Recibe JSON con {cliente_id, imagen: dataURL}
    import json
    data = json.loads(request.body)
    cliente_id = data.get('cliente_id')
    data_url = data.get('imagen')
    if not cliente_id or not data_url:
        return JsonResponse({'status':'error','msg':'Falta cliente o imagen'}, status=400)
    cliente = get_object_or_404(ClienteLocal, pk=cliente_id)
    imgstr = re.sub(r'^data:image/.+;base64,', '', data_url)
    imgdata = base64.b64decode(imgstr)
    filename = f'firma_{cliente.id}.png'
    cliente.firma_imagen.save(filename, ContentFile(imgdata), save=True)
    return JsonResponse({'status':'ok'})

def subir_ine(request, cliente_id):
    cliente = get_object_or_404(ClienteLocal, pk=cliente_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('nuevo_contrato')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'clientes/subir_ine.html', {'form': form, 'cliente': cliente})

def generar_pdf_contrato(contrato: Contrato):
    cliente = contrato.cliente
    ruta = os.path.join(settings.MEDIA_ROOT, f'contratos_pdf/contrato_{contrato.id}.pdf')
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    c = canvas.Canvas(ruta, pagesize=LETTER)
    y = 750
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Contrato de Servicio")
    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Cliente: {cliente.nombre}")
    y -= 20
    c.drawString(50, y, f"Correo: {cliente.correo or ''}")
    y -= 20
    c.drawString(50, y, f"Teléfono: {cliente.telefono or ''}")
    y -= 40
    c.drawString(50, y, "Contenido del contrato (ejemplo)")
    y -= 120
    # Firma
    if cliente.firma_imagen:
        try:
            c.drawImage(cliente.firma_imagen.path, 50, y - 50, width=200, height=60)
            y -= 80
        except Exception:
            pass
    # INE
    if cliente.foto_ine:
        try:
            c.drawImage(cliente.foto_ine.path, 300, y + 100, width=200, height=120)
        except Exception:
            pass
    c.showPage()
    c.save()
    # Guardar en modelo
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
    # Guardar archivo
    path = os.path.join(settings.MEDIA_ROOT, f'contratos_xlsx/contrato_{contrato.id}.xlsx')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)
    with open(path, 'rb') as f:
        contrato.excel.save(os.path.basename(path), ContentFile(f.read()), save=True)
    return contrato.excel.url

def crear_contrato_desde_cliente(request):
    # Endpoint que crea un Contrato usando cliente_id y datos opcionales
    if request.method != 'POST':
        return JsonResponse({'status':'error','msg':'POST required'}, status=400)
    cliente_id = request.POST.get('cliente_id')
    tipo = request.POST.get('tipo','Contrato de servicio')
    cliente = get_object_or_404(ClienteLocal, pk=cliente_id)
    contrato = Contrato.objects.create(cliente=cliente, tipo=tipo, datos={})
    # Generar PDF y Excel
    generar_pdf_contrato(contrato)
    generar_excel_contrato(contrato)
    return JsonResponse({'status':'ok','contrato_id': contrato.id})

def detalle_contrato(request, id, cliente_nombre):
    contrato = get_object_or_404(Contrato, pk=id)
    return render(request, 'clientes/detalle.html', {
        'contrato': contrato,
        'nombre_url': cliente_nombre
    })

