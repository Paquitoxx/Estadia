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
from django.db.models import Q  # <--- IMPORTANTE: Necesario para la búsqueda avanzada

# Modelos y Formularios
from .models import ClienteLocal, Contrato
from .forms import ClienteForm, ContratoForm

# ==========================================
# 🔹 1. UTILIDADES Y CONEXIÓN
# ==========================================

def obtener_fecha_actual_texto():
    """Genera la fecha actual en formato texto (ej. 24 de Noviembre de 2025)."""
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    hoy = datetime.date.today()
    return f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

def consultar_api(endpoint, params=None):
    """Consulta la API externa y maneja errores de conexión."""
    base_url = os.getenv("API_URL")
    api_key = os.getenv("API_KEY")

    if not base_url or not api_key:
        print("⚠️ Advertencia: Faltan variables de entorno API_URL o API_KEY")
        return {'error': 'Configuración de API faltante'}

    url = f"{base_url}{endpoint}"
    headers = {'Content-Type': 'application/json', 'X-Auth-App-Key': api_key}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Normalizar respuesta (si es lista o diccionario)
            if isinstance(data, list): return data
            if isinstance(data, dict): return data.get('results', data)
            return []
        return {'error': f"Error {response.status_code} al consultar API"}
    except Exception as e:
        return {'error': f"Error de conexión: {str(e)}"}


# ==========================================
# 🔹 2. NAVEGACIÓN Y LISTADOS
# ==========================================

def home(request):
    return render(request, 'clientes/home.html')

def contratos_recientes(request):
    """
    Muestra los contratos generados recientemente.
    Si hay búsqueda (?q=), filtra por cliente, correo o ID.
    Si no, muestra los últimos 20.
    """
    # 1. Consulta Base Optimizada
    queryset = Contrato.objects.select_related("cliente").order_by("-fecha_generacion")

    # 2. Lógica de Búsqueda
    query = request.GET.get('q')
    
    if query:
        queryset = queryset.filter(
            Q(cliente__nombre__icontains=query) |                # Nombre del cliente
            Q(cliente__correo__icontains=query) |                # Correo
            Q(cliente__identificador_externo__icontains=query) | # ID de la API
            Q(id__icontains=query)                               # ID del contrato local
        )

    # 3. Limitar resultados 
    # Si buscamos, mostramos hasta 50 coincidencias, si no, los últimos 20
    limit = 50 if query else 20
    contratos = queryset[:limit]

    return render(request, "clientes/recientes.html", {"contratos": contratos})

def todos_contratos(request):
    """
    Listado paginado de todos los contratos con BÚSQUEDA INTEGRADA.
    Filtra por nombre antes de paginar para no romper la navegación.
    """
    # 1. Consulta Base
    queryset = Contrato.objects.select_related("cliente").order_by("-fecha_generacion")

    # 2. Capturar y aplicar búsqueda
    query = request.GET.get("q")

    if query:
        queryset = queryset.filter(
            Q(cliente__nombre__icontains=query) |                # Buscar por Nombre
            Q(cliente__identificador_externo__icontains=query) | # Buscar por ID Cliente
            Q(id__icontains=query)                               # Buscar por Folio Contrato
        )

    # 3. Paginación
    paginator = Paginator(queryset, 20) # 20 contratos por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 4. Renderizar (Pasamos 'query' al contexto para mantener la búsqueda en botones)
    return render(request, "clientes/todos.html", {
        "page_obj": page_obj, 
        "contratos": page_obj.object_list,
        "query": query 
    })


def ver_contrato_guardado(request, contrato_id):
    """Recupera y muestra el HTML histórico (snapshot) guardado en la BD."""
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if contrato.html_contenido:
        return HttpResponse(contrato.html_contenido)
    return HttpResponse("Este contrato no tiene una versión HTML guardada.", status=404)


# ==========================================
# 🔹 3. GESTIÓN (GUARDAR / ELIMINAR / EDITAR)
# ==========================================

@csrf_exempt
def guardar_contrato_confirmado(request):
    """
    Recibe el HTML final (con ediciones manuales y firmas) y lo guarda en la BD.
    Se activa SOLO con el botón 'Guardar Contrato' en la carátula.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cliente_id_ext = data.get('cliente_id')
            html_content = data.get('html')
            datos_json = data.get('datos_extra', {})

            if not cliente_id_ext or not html_content:
                return JsonResponse({'status': 'error', 'msg': 'Faltan datos para guardar.'})

            # 1. Asegurar o recuperar el cliente local
            cliente_local, _ = ClienteLocal.objects.get_or_create(
                identificador_externo=str(cliente_id_ext),
                defaults={'nombre': 'Cliente Importado'}
            )

            # 2. Crear el registro del contrato
            nuevo_contrato = Contrato.objects.create(
                cliente=cliente_local,
                tipo="Contrato de Servicio",
                datos=datos_json,
                html_contenido=html_content # Guardamos el HTML tal cual se ve en pantalla
            )

            return JsonResponse({'status': 'ok', 'id': nuevo_contrato.id})

        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})

    return JsonResponse({'status': 'error', 'msg': 'Método no permitido'})

def eliminar_contrato(request, contrato_id):
    """Elimina un contrato y retorna a la lista anterior."""
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    contrato.delete()
    return redirect(request.META.get('HTTP_REFERER', 'contratos_recientes'))

def editar_contrato(request, contrato_id):
    """
    Abre un contrato existente mostrando su HTML guardado.
    Esto permite volver a editar o reimprimir un contrato antiguo.
    """
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if not contrato.html_contenido:
        return HttpResponse("Este contrato no tiene contenido editable.", status=404)
    return HttpResponse(contrato.html_contenido)


# ==========================================
# 🔹 4. BÚSQUEDA Y CLIENTES (API EXTERNA)
# ==========================================

def buscar_cliente(request):
    """
    Esta función busca clientes EN LA API EXTERNA para generar nuevos contratos.
    No confundir con la búsqueda local de contratos.
    """
    query = request.GET.get('q', '').strip()
    resultados = []
    
    if query:
        # Consulta a la API externa
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
    Obtiene datos de la API, prepara la plantilla y la muestra para edición.
    IMPORTANTE: Ya NO guarda el contrato automáticamente.
    """
    # A. Obtener Datos API
    datos = consultar_api(f"/clients/{cliente_id}")

    # Manejo robusto de la respuesta (lista vs dict)
    if isinstance(datos, list) and len(datos) > 0:
        cliente_data = next((item for item in datos if item.get("id") == int(cliente_id)), datos[0])
    elif isinstance(datos, dict) and "error" not in datos:
        cliente_data = datos
    else:
        cliente_data = {}

    # B. Mapeo de Datos (Limpieza)
    contactos = cliente_data.get("contacts", [])
    contacto_principal = contactos[0] if contactos else {}

    telefono = contacto_principal.get("phone", "")
    email = contacto_principal.get("email", "")
    
    calle = cliente_data.get("fullAddress") or cliente_data.get("street1") or "Domicilio no registrado"
    ciudad = cliente_data.get("city") or ""
    cp = cliente_data.get("zipCode") or ""
    direccion_str = f"{calle}, {ciudad}. CP: {cp}"

    nombre_completo = f"{cliente_data.get('firstName', '')} {cliente_data.get('lastName', '')}".strip()

    # C. Preparar Contexto para la Plantilla
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

    # D. Sincronización Cliente Local 
    cliente_db, _ = ClienteLocal.objects.update_or_create(
        identificador_externo=str(cliente_id),
        defaults={
            'nombre': nombre_completo,
            'correo': email,
            'telefono': telefono,
            'direccion': direccion_str
        }
    )
    
    # E. Inyectar firma existente
    if cliente_db.firma_imagen:
        cliente_obj["firma_imagen"] = cliente_db.firma_imagen
        context["cliente_db"] = cliente_db

    # F. Renderizar plantilla
    return render(request, "clientes/Caratula.html", context)


# ==========================================
# 🔹 6. FIRMA DIGITAL (CANVAS)
# ==========================================

@csrf_exempt
def guardar_firma_digital(request):
    """
    Recibe la imagen Base64 del canvas y la guarda en ClienteLocal.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cliente_id = data.get('cliente_id')
            imagen_b64 = data.get('imagen')
            tipo_firma = data.get('tipo_firma', '') # Opcional: si quieres guardar distintos tipos

            if not cliente_id or not imagen_b64:
                return JsonResponse({'status': 'error', 'msg': 'Datos incompletos'})

            cliente = ClienteLocal.objects.filter(identificador_externo=str(cliente_id)).first()
            
            if not cliente:
                return JsonResponse({'status': 'error', 'msg': 'Cliente no encontrado localmente'})

            # Procesar Base64 a Archivo
            if ';base64,' in imagen_b64:
                format, imgstr = imagen_b64.split(';base64,') 
                ext = format.split('/')[-1] 
            else:
                imgstr = imagen_b64
                ext = "png"
            
            file_name = f"firma_{cliente.id}_{datetime.datetime.now().timestamp()}.{ext}"
            data_file = ContentFile(base64.b64decode(imgstr), name=file_name)

            # Guardar archivo (Aquí siempre guardamos en 'firma_imagen', 
            # si quisieras separar autorizacion/main necesitarías otro campo en el modelo)
            cliente.firma_imagen = data_file
            cliente.save()

            return JsonResponse({'status': 'ok', 'url': cliente.firma_imagen.url})

        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
    
    return JsonResponse({'status': 'error', 'msg': 'Método no permitido'})


# ==========================================
# 🔹 7. VISTAS LEGACY / AUXILIARES
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
    return HttpResponse("Función PDF disponible.")

def detalle_contrato(request, cliente_id, cliente_nombre):
    contrato = Contrato.objects.filter(cliente__identificador_externo=cliente_id).last()
    return render(request, 'clientes/detalle.html', {'contrato': contrato})

@csrf_exempt
def crear_contrato_desde_cliente(request):
    return JsonResponse({'status': 'ok'})

@csrf_exempt
def guardar_firma(request):
    return JsonResponse({'status': 'ok'})