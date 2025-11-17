from django.urls import path
from . import views

urlpatterns = [
    # Página principal
    path('', views.home, name='home'),

    # Búsqueda de clientes
    path('buscar_cliente/', views.buscar_cliente, name='buscar_cliente'),

    # Contratos
    path('contratos/recientes/', views.contratos_recientes, name='contratos_recientes'),
    path('contratos/todos/', views.todos_contratos, name='todos_contratos'),
    path('contratos/nuevo/', views.nuevo_contrato, name='nuevo_contrato'),
    path('contratos/crear/', views.crear_contrato_desde_cliente, name='crear_contrato'),
    path('contratos/detalle/<int:cliente_id>/<str:cliente_nombre>/', views.detalle_contrato, name='detalle_contrato'),

    # Clientes - documentos e INE (Se mantiene 'clientes/' aquí)
    path('clientes/<int:cliente_id>/subir_ine/', views.subir_ine, name='subir_ine'),

    # Firma (Se mantiene 'clientes/' aquí)
    path('clientes/guardar_firma/', views.guardar_firma, name='guardar_firma'),

    # Carátula (vista y PDF) - CAMBIADAS A SINGULAR 'CLIENTE'
    # Ahora aceptarán: /cliente/1478/caratula/
    path('cliente/<int:cliente_id>/caratula/', views.caratula_cliente, name='caratula_cliente'),
    path('cliente/<int:cliente_id>/caratula/pdf/', views.caratula_pdf, name='caratula_pdf'),
]