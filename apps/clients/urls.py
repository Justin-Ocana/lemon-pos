from django.urls import path
from . import views

# Define el espacio de nombres para la aplicación
app_name = 'clients'

# Patrones de URL para las vistas de la aplicación
urlpatterns = [
    # Ruta para la lista de clientes
    path('', views.lista_clientes, name='lista'),
    # Ruta para agregar un nuevo cliente
    path('agregar/', views.agregar_cliente, name='agregar'),
    # Ruta para editar un cliente existente, usando el ID (cliente_id)
    path('editar/<int:cliente_id>/', views.editar_cliente, name='editar'),
    # Ruta para eliminar un cliente, usando el ID (cliente_id)
    path('eliminar/<int:cliente_id>/', views.eliminar_cliente, name='eliminar'),
    # Ruta para ver los detalles de un cliente, usando el ID (cliente_id)
    path('detalle/<int:cliente_id>/', views.detalle_cliente, name='detalle'),
    # Ruta para la búsqueda de clientes
    path('search/', views.client_search_view, name='client_search'),
    # Ruta para marcar/desmarcar favorito
    path('toggle-favorito/<int:cliente_id>/', views.toggle_favorito, name='toggle_favorito'),
    
    # === RUTAS DE CRÉDITO ===
    # Historial de crédito del cliente
    path('credito/<int:cliente_id>/historial/', views.historial_credito_cliente, name='historial_credito'),
    # Registrar pago de crédito
    path('credito/<int:cliente_id>/pagar/', views.registrar_pago_credito, name='registrar_pago'),
    # Lista de clientes con deuda
    path('credito/deudas/', views.clientes_con_deuda, name='clientes_con_deuda'),
    # API: Verificar crédito disponible
    path('credito/<int:cliente_id>/verificar/', views.verificar_credito_disponible, name='verificar_credito'),
]