"""
Script de prueba para el sistema de crédito.
Ejecutar con: python manage.py shell < test_sistema_credito.py
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.clients.models import Cliente
from apps.transacciones.models import CreditoMovimiento

User = get_user_model()

print("=" * 60)
print("🧪 PRUEBA DEL SISTEMA DE CRÉDITO")
print("=" * 60)

# 1. Obtener o crear usuario de prueba
try:
    usuario = User.objects.first()
    if not usuario:
        print("❌ No hay usuarios en el sistema. Crea uno primero.")
        exit()
    print(f"✅ Usuario: {usuario.username}")
except Exception as e:
    print(f"❌ Error al obtener usuario: {e}")
    exit()

# 2. Crear cliente de prueba con crédito
print("\n" + "=" * 60)
print("📝 CREANDO CLIENTE DE PRUEBA")
print("=" * 60)

try:
    # Eliminar cliente de prueba si existe
    Cliente.objects.filter(identificacion='1234567890').delete()
    
    cliente = Cliente.objects.create(
        usuario_creador=usuario,
        codigo='TEST-001',
        nombre='Cliente Prueba Crédito',
        identificacion='1234567890',
        email='prueba@credito.com',
        telefono='0999999999',
        direccion='Calle Prueba 123',
        ciudad='Quito',
        grupo='regular',
        estado='activo',
        # Configuración de crédito
        credito_habilitado=True,
        limite_credito=Decimal('1000.00'),
        saldo_credito_actual=Decimal('0.00'),
        dias_credito=30
    )
    print(f"✅ Cliente creado: {cliente.nombre}")
    print(f"   - Límite de crédito: ${cliente.limite_credito}")
    print(f"   - Saldo actual: ${cliente.saldo_credito_actual}")
    print(f"   - Crédito disponible: ${cliente.get_credito_disponible()}")
except Exception as e:
    print(f"❌ Error al crear cliente: {e}")
    exit()

# 3. Probar validaciones
print("\n" + "=" * 60)
print("🔍 PROBANDO VALIDACIONES")
print("=" * 60)

# 3.1 Verificar que puede comprar a crédito
monto_prueba = Decimal('200.00')
puede_comprar = cliente.puede_comprar_a_credito(monto_prueba)
print(f"¿Puede comprar ${monto_prueba}? {'✅ Sí' if puede_comprar else '❌ No'}")

# 3.2 Verificar que no puede exceder el límite
monto_excesivo = Decimal('1500.00')
puede_comprar_excesivo = cliente.puede_comprar_a_credito(monto_excesivo)
print(f"¿Puede comprar ${monto_excesivo}? {'❌ Sí (ERROR)' if puede_comprar_excesivo else '✅ No (Correcto)'}")

# 4. Registrar cargo (simulando venta a crédito)
print("\n" + "=" * 60)
print("💳 REGISTRANDO CARGO (VENTA A CRÉDITO)")
print("=" * 60)

try:
    movimiento1 = cliente.registrar_cargo_credito(
        monto=Decimal('250.00'),
        venta=None,  # En producción sería el objeto Venta
        usuario=usuario,
        notas="Venta de prueba #1"
    )
    print(f"✅ Cargo registrado: ${movimiento1.monto}")
    print(f"   - Saldo anterior: ${movimiento1.saldo_anterior}")
    print(f"   - Saldo nuevo: ${movimiento1.saldo_nuevo}")
    print(f"   - Crédito disponible: ${cliente.get_credito_disponible()}")
except Exception as e:
    print(f"❌ Error al registrar cargo: {e}")

# 5. Registrar otro cargo
print("\n" + "=" * 60)
print("💳 REGISTRANDO SEGUNDO CARGO")
print("=" * 60)

try:
    movimiento2 = cliente.registrar_cargo_credito(
        monto=Decimal('350.00'),
        venta=None,
        usuario=usuario,
        notas="Venta de prueba #2"
    )
    print(f"✅ Cargo registrado: ${movimiento2.monto}")
    print(f"   - Saldo anterior: ${movimiento2.saldo_anterior}")
    print(f"   - Saldo nuevo: ${movimiento2.saldo_nuevo}")
    print(f"   - Crédito disponible: ${cliente.get_credito_disponible()}")
except Exception as e:
    print(f"❌ Error al registrar cargo: {e}")

# 6. Registrar pago
print("\n" + "=" * 60)
print("💰 REGISTRANDO PAGO")
print("=" * 60)

try:
    movimiento3 = cliente.registrar_pago_credito(
        monto=Decimal('200.00'),
        transaccion=None,  # En producción sería el objeto Transaccion
        usuario=usuario,
        referencia="Pago efectivo #001",
        notas="Pago parcial de deuda"
    )
    print(f"✅ Pago registrado: ${movimiento3.monto}")
    print(f"   - Saldo anterior: ${movimiento3.saldo_anterior}")
    print(f"   - Saldo nuevo: ${movimiento3.saldo_nuevo}")
    print(f"   - Crédito disponible: ${cliente.get_credito_disponible()}")
except Exception as e:
    print(f"❌ Error al registrar pago: {e}")

# 7. Verificar historial
print("\n" + "=" * 60)
print("📋 HISTORIAL DE MOVIMIENTOS")
print("=" * 60)

movimientos = CreditoMovimiento.obtener_historial_cliente(cliente)
print(f"Total de movimientos: {movimientos.count()}")
print("\nDetalle:")
for mov in movimientos:
    signo = '+' if mov.tipo == 'cargo' else '-'
    print(f"  {mov.fecha.strftime('%Y-%m-%d %H:%M')} | {mov.get_tipo_display():8} | {signo}${mov.monto:8.2f} | Saldo: ${mov.saldo_nuevo:8.2f}")

# 8. Calcular saldo (verificación)
print("\n" + "=" * 60)
print("🧮 VERIFICACIÓN DE SALDO")
print("=" * 60)

saldo_calculado = CreditoMovimiento.calcular_saldo_cliente(cliente)
saldo_actual = cliente.saldo_credito_actual
print(f"Saldo en cliente: ${saldo_actual}")
print(f"Saldo calculado: ${saldo_calculado}")
print(f"{'✅ Coinciden' if saldo_calculado == saldo_actual else '❌ NO coinciden (ERROR)'}")

# 9. Probar validación de pago excesivo
print("\n" + "=" * 60)
print("🚫 PROBANDO VALIDACIÓN DE PAGO EXCESIVO")
print("=" * 60)

try:
    cliente.registrar_pago_credito(
        monto=Decimal('5000.00'),  # Más de lo que debe
        usuario=usuario,
        notas="Intento de pago excesivo"
    )
    print("❌ ERROR: Se permitió pago excesivo")
except ValueError as e:
    print(f"✅ Validación correcta: {e}")

# 10. Resumen final
print("\n" + "=" * 60)
print("📊 RESUMEN FINAL")
print("=" * 60)
print(f"Cliente: {cliente.nombre}")
print(f"Límite de crédito: ${cliente.limite_credito}")
print(f"Saldo actual: ${cliente.saldo_credito_actual}")
print(f"Crédito disponible: ${cliente.get_credito_disponible()}")
print(f"Días de crédito: {cliente.dias_credito} días")
print(f"Total movimientos: {movimientos.count()}")

# Calcular totales
total_cargos = sum(m.monto for m in movimientos if m.tipo == 'cargo')
total_pagos = sum(m.monto for m in movimientos if m.tipo == 'pago')
print(f"\nTotal cargos: ${total_cargos}")
print(f"Total pagos: ${total_pagos}")
print(f"Diferencia: ${total_cargos - total_pagos}")

print("\n" + "=" * 60)
print("✅ PRUEBA COMPLETADA")
print("=" * 60)
