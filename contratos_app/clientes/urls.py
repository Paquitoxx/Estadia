from django.urls import path
from . import views

urlpatterns = [
    # Principal
    path('', views.home, name='home'),
    path('buscar_cliente/', views.buscar_cliente, name='buscar_cliente'),

    # Listados
    path('contratos/recientes/', views.contratos_recientes, name='contratos_recientes'),
    path('contratos/todos/', views.todos_contratos, name='todos_contratos'),

    # 🔥 VISTA CRÍTICA: Ver el contrato histórico guardado
    path('contratos/ver/<int:contrato_id>/', views.ver_contrato_guardado, name='ver_contrato_guardado'),

    # ==========================================
    # 🔴 AQUÍ ESTABA LO QUE FALTABA:
    # ==========================================
    
    # 1. Ruta para ELIMINAR (Soluciona el error NoReverseMatch)
    path('contratos/eliminar/<int:contrato_id>/', views.eliminar_contrato, name='eliminar_contrato'),

    # 2. Ruta para GUARDAR EL CONTRATO FINAL (Botón Verde)
    path('contratos/guardar-confirmado/', views.guardar_contrato_confirmado, name='guardar_contrato_confirmado'),

    # ==========================================

    # Gestión manual
    path('contratos/nuevo/', views.nuevo_contrato, name='nuevo_contrato'),
    path('contratos/crear/', views.crear_contrato_desde_cliente, name='crear_contrato'),
    path('contratos/detalle/<int:cliente_id>/<str:cliente_nombre>/', views.detalle_contrato, name='detalle_contrato'),

    # Documentos y Firmas
    path('clientes/<int:cliente_id>/subir_ine/', views.subir_ine, name='subir_ine'),
    path('clientes/guardar_firma/', views.guardar_firma, name='guardar_firma'), # (Legacy)
    
    # ✍️ NUEVA RUTA: Guardar Firma Digital desde Canvas
    path('clientes/guardar_firma_digital/', views.guardar_firma_digital, name='guardar_firma_digital'),

    # 📄 GENERACIÓN AUTOMÁTICA DE CARÁTULA
    path('cliente/<int:cliente_id>/caratula/', views.caratula_cliente, name='caratula_cliente'),
    path('cliente/<int:cliente_id>/caratula/pdf/', views.caratula_pdf, name='caratula_pdf'),
]