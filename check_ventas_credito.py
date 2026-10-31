from apps.ventas.models import Venta
from apps.clients.models import Cliente

ventas = Venta.objects.filter(metodo_pago='credit')
print(f'Ventas a crédito: {ventas.count()}')

for v in ventas[:10]:
    cliente_nombre = v.cliente.nombre if v.cliente else "N/A"
    print(f'  - Venta #{v.id}: Cliente {cliente_nombre}, Total: ${v.total}, Estado: {v.estado_pago}')

print(f'\nClientes con saldo > 0: {Cliente.objects.filter(saldo_credito_actual__gt=0).count()}')
for c in Cliente.objects.filter(saldo_credito_actual__gt=0)[:10]:
    print(f'  - {c.nombre}: ${c.saldo_credito_actual}')
