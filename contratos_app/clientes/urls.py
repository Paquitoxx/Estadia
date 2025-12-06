from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # PAGINA PRINCIPAL Y BUSQUEDA API
    # ==========================================
    path('', views.home, name='home'),
    path('buscar_cliente/', views.buscar_cliente, name='buscar_cliente'),

    # ==========================================
    # LISTADOS DE CONTRATOS (HISTORIAL)
    # ==========================================
    # Estas vistas soportaran busqueda por nombre localmente
    path('contratos/recientes/', views.contratos_recientes, name='contratos_recientes'),
    path('contratos/todos/', views.todos_contratos, name='todos_contratos'),

    # ==========================================
    # VISUALIZACION Y EDICION
    # ==========================================
    
    # Ver contrato (solo lectura, snapshot HTML)
    path('contratos/ver/<int:contrato_id>/', views.ver_contrato_guardado, name='ver_contrato_guardado'),

    # Nueva Ruta: Abrir un contrato existente para seguir editandolo
    path('contratos/editar/<int:contrato_id>/', views.editar_contrato, name='editar_contrato'),

    # ==========================================
    # GESTION DE DATOS (CRUD)
    # ==========================================
    
    # Guardar nuevo contrato o actualizacion
    path('contratos/guardar-confirmado/', views.guardar_contrato_confirmado, name='guardar_contrato_confirmado'),

    # Eliminar contrato
    path('contratos/eliminar/<int:contrato_id>/', views.eliminar_contrato, name='eliminar_contrato'),

    # ==========================================
    # FIRMA DIGITAL Y DOCUMENTOS
    # ==========================================
    path('clientes/guardar_firma_digital/', views.guardar_firma_digital, name='guardar_firma_digital'),
    path('clientes/<int:cliente_id>/subir_ine/', views.subir_ine, name='subir_ine'),
    path('clientes/guardar_firma/', views.guardar_firma, name='guardar_firma'), # Legacy

    # ==========================================
    # GENERACION DE CARATULA (DESDE CERO)
    # ==========================================
    path('cliente/<int:cliente_id>/caratula/', views.caratula_cliente, name='caratula_cliente'),
    
    # Opcionales / Legacy
    path('cliente/<int:cliente_id>/caratula/pdf/', views.caratula_pdf, name='caratula_pdf'),
    path('contratos/nuevo/', views.nuevo_contrato, name='nuevo_contrato'),
    path('contratos/crear/', views.crear_contrato_desde_cliente, name='crear_contrato'),
    path('contratos/detalle/<int:cliente_id>/<str:cliente_nombre>/', views.detalle_contrato, name='detalle_contrato'),
]