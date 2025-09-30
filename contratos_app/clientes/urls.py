from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('buscar_cliente/', views.buscar_cliente, name='buscar_cliente'),
    path('contratos/recientes/', views.contratos_recientes, name='contratos_recientes'),
    path('contratos/todos/', views.todos_contratos, name='todos_contratos'),
    path('contratos/nuevo/', views.nuevo_contrato, name='nuevo_contrato'),
    path('cliente/<int:cliente_id>/subir_ine/', views.subir_ine, name='subir_ine'),
    path('guardar_firma/', views.guardar_firma, name='guardar_firma'),
    path('crear_contrato/', views.crear_contrato_desde_cliente, name='crear_contrato'),
]
