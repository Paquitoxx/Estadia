import os
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

# Modelos y Formularios
from .models import ClienteLocal, Contrato
from .forms import ClienteForm, ContratoForm

# ==========================================
# 🔹 1. UTILIDADES
# ==========================================

def obtener_fecha_actual_texto():
    """Retorna la fecha actual en formato texto (ej. 24 de Noviembre de 2025)."""
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    hoy = datetime.date.today()
    return f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

def consultar_api(endpoint, params=None):
    """Consulta la API externa y maneja errores básicos."""
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
            # Normalización de respuesta (Lista vs Diccionario)
            if isinstance(data, list): return data
            if isinstance(data, dict): return data.get('results', data)
            return []
        return {'error': f"Error {response.status_code}"}
    except Exception as e:
        return {'error': str(e)}


# ==========================================
# 🔹 2. NAVEGACIÓN Y LISTADOS
# ==========================================

def home(request):
    return render(request, 'clientes/home.html')

def contratos_recientes(request):
    """ Muestra los últimos 20 contratos generados. """
    contratos = Contrato.objects.select_related("cliente").order_by("-fecha_generacion")[:20]
    return render(request, "clientes/recientes.html", {"contratos": contratos})

def todos_contratos(request):
    """ Listado paginado de todos los contratos. """
    lista = Contrato.objects.select_related("cliente").order_by("-fecha_generacion")
    paginator = Paginator(lista, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "clientes/todos.html", {"page_obj": page_obj, "contratos": page_obj.object_list})

def ver_contrato_guardado(request, contrato_id):
    """ Recupera el HTML histórico guardado en la BD para visualización. """
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if contrato.html_contenido:
        return HttpResponse(contrato.html_contenido)
    return HttpResponse("Este contrato no tiene versión HTML guardada.", status=404)


# ==========================================
# 🔹 3. GESTIÓN DE CONTRATOS (GUARDAR / ELIMINAR)
# ==========================================

@csrf_exempt
def guardar_contrato_confirmado(request):
    """
    NUEVO: Recibe el HTML final (con ediciones manuales y firmas) y lo guarda en la BD.
    Esta vista es llamada por el botón 'Guardar Contrato' en la carátula.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cliente_id_ext = data.get('cliente_id')
            html_content = data.get('html')
            datos_json = data.get('datos_extra', {})

            if not cliente_id_ext or not html_content:
                return JsonResponse({'status': 'error', 'msg': 'Faltan datos críticos'})

            # Aseguramos que el cliente exista localmente para vincularlo
            cliente_local, _ = ClienteLocal.objects.get_or_create(
                identificador_externo=str(cliente_id_ext),
                defaults={'nombre': 'Cliente Importado'}
            )

            # Creamos el registro del contrato
            nuevo_contrato = Contrato.objects.create(
                cliente=cliente_local,
                tipo="Contrato de Servicio",
                datos=datos_json,
                html_contenido=html_content # Guardamos el HTML editado
            )

            return JsonResponse({'status': 'ok', 'id': nuevo_contrato.id})

        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})

    return JsonResponse({'status': 'error', 'msg': 'Método no permitido'})

def eliminar_contrato(request, contrato_id):
    """ Elimina un contrato y regresa a la página anterior. """
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    contrato.delete()
    # Redirige a la página desde donde se hizo la petición (recientes o todos)
    return redirect(request.META.get('HTTP_REFERER', 'contratos_recientes'))


# ==========================================
# 🔹 4. BÚSQUEDA Y CLIENTES
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
# 🔹 5. GENERACIÓN DE CARÁTULA (VISTA PREVIA)
# ==========================================

def caratula_cliente(request, cliente_id):
    """
    Obtiene datos de la API y muestra la carátula para editar/firmar.
    NOTA: Ya NO guarda automáticamente el contrato en la BD.
    """
    # A. Obtener Datos API
    datos = consultar_api(f"/clients/{cliente_id}")

    if isinstance(datos, list) and len(datos) > 0:
        # Busca el ID exacto o toma el primero
        cliente_data = next((item for item in datos if item.get("id") == int(cliente_id)), datos[0])
    elif isinstance(datos, dict) and "error" not in datos:
        cliente_data = datos
    else:
        cliente_data = {}

    # B. Mapeo de Datos
    contactos = cliente_data.get("contacts", [])
    contacto_principal = contactos[0] if contactos else {}

    telefono = contacto_principal.get("phone", "")
    email = contacto_principal.get("email", "")
    
    calle = cliente_data.get("fullAddress") or cliente_data.get("street1") or "Domicilio no registrado"
    ciudad = cliente_data.get("city") or ""
    cp = cliente_data.get("zipCode") or ""
    direccion_str = f"{calle}, {ciudad}. CP: {cp}"

    nombre_completo = f"{cliente_data.get('firstName', '')} {cliente_data.get('lastName', '')}".strip()

    # Objeto Cliente Contexto
    cliente_obj = {
        "nombre_completo": nombre_completo,
        "telefono": telefono,
        "email": email,
        "direccion_completa": direccion_str,
        "rfc": cliente_data.get("companyTaxId") or "XAXX010101000",
        "ciudad": ciudad,
        "identificador_externo": str(cliente_data.get("id"))
    }

    proveedor = {
        "nombre": cliente_data.get("organizationName", "Computer World Guamuchil"),
    }

    context = {
        "cliente": cliente_obj,
        "proveedor": proveedor,
        "fecha_actual": obtener_fecha_actual_texto(),
        "contrato": { "numero": f"CONT-{cliente_id}" }
    }

    # C. Sincronización Cliente Local (Necesario para guardar firma posteriormente)
    cliente_db, _ = ClienteLocal.objects.update_or_create(
        identificador_externo=str(cliente_id),
        defaults={
            'nombre': nombre_completo,
            'correo': email,
            'telefono': telefono,
            'direccion': direccion_str
        }
    )
    
    # D. Inyectar firma existente si la hay (para mostrarla en la vista previa)
    if cliente_db.firma_imagen:
        cliente_obj["firma_imagen"] = cliente_db.firma_imagen
        context["cliente_db"] = cliente_db

    # E. Renderizar plantilla (Sin guardar Contrato aún)
    return render(request, "clientes/Caratula.html", context)


# ==========================================
# 🔹 6. FIRMA DIGITAL
# ==========================================

@csrf_exempt
def guardar_firma_digital(request):
    """
    Recibe base64 del canvas, crea imagen y la asocia al ClienteLocal.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cliente_id = data.get('cliente_id')
            imagen_b64 = data.get('imagen')

            if not cliente_id or not imagen_b64:
                return JsonResponse({'status': 'error', 'msg': 'Datos incompletos'})

            cliente = ClienteLocal.objects.filter(identificador_externo=str(cliente_id)).first()
            
            if not cliente:
                return JsonResponse({'status': 'error', 'msg': 'Cliente no encontrado localmente'})

            # Procesar Base64
            if ';base64,' in imagen_b64:
                format, imgstr = imagen_b64.split(';base64,') 
                ext = format.split('/')[-1] 
            else:
                imgstr = imagen_b64
                ext = "png"
            
            file_name = f"firma_{cliente.id}_{datetime.datetime.now().timestamp()}.{ext}"
            data_file = ContentFile(base64.b64decode(imgstr), name=file_name)

            cliente.firma_imagen = data_file
            cliente.save()

            return JsonResponse({'status': 'ok', 'url': cliente.firma_imagen.url})

        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
    
    return JsonResponse({'status': 'error', 'msg': 'Método no permitido'})


# ==========================================
# 🔹 7. OTRAS VISTAS (MANUALES / LEGACY)
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

def caratula_pdf(request, cliente_id):
    return HttpResponse("Función PDF disponible para implementación futura.")

def detalle_contrato(request, cliente_id, cliente_nombre):
    contrato = Contrato.objects.filter(cliente__identificador_externo=cliente_id).last()
    return render(request, 'clientes/detalle.html', {'contrato': contrato})

@csrf_exempt
def crear_contrato_desde_cliente(request):
    return JsonResponse({'status': 'ok'})

@csrf_exempt
def guardar_firma(request):
    return JsonResponse({'status': 'ok'})