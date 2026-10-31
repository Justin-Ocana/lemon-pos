# 📋 Sistema de Crédito - Documentación

## 🎯 Descripción General

El sistema de crédito permite a los clientes comprar productos y pagar posteriormente, con un límite de crédito establecido y seguimiento completo de movimientos.

## 📊 Conceptos Básicos

### Cliente con Crédito
Un cliente puede tener:
- **Crédito Habilitado**: Permiso para comprar a crédito
- **Límite de Crédito**: Monto máximo que puede deber (ej: $1000)
- **Saldo Actual**: Deuda actual del cliente (ej: $350)
- **Crédito Disponible**: Límite - Saldo (ej: $650)
- **Días de Crédito**: Plazo para pagar (ej: 30 días)

### Ejemplo Práctico
```
Cliente: Juan Pérez
Límite de crédito: $1,000
Saldo actual: $350
Crédito disponible: $650
Días de crédito: 30 días
```

## 🔄 Flujo de Operaciones

### 1. Venta a Crédito

**Proceso:**
1. Cliente selecciona productos en el POS
2. Al finalizar, selecciona "Método de Pago: Crédito"
3. Sistema valida:
   - ✅ Cliente tiene crédito habilitado
   - ✅ Monto de venta ≤ Crédito disponible
   - ❌ Consumidor Final NO puede comprar a crédito
4. Si es válido:
   - Crea la venta con `estado_pago = 'pendiente'`
   - Registra un **cargo** en movimientos de crédito
   - Actualiza `saldo_credito_actual` del cliente

**Ejemplo:**
```
Venta: $200
Saldo anterior: $350
Nuevo saldo: $550
Crédito disponible: $450
```

### 2. Pago de Crédito

**Proceso:**
1. Cliente realiza un pago (efectivo, tarjeta, transferencia)
2. Se registra en el sistema:
   - Crea transacción de tipo `pago_credito`
   - Registra un **pago** en movimientos de crédito
   - Reduce `saldo_credito_actual` del cliente
   - Actualiza `estado_pago` de la venta si corresponde

**Ejemplo:**
```
Pago: $150
Saldo anterior: $550
Nuevo saldo: $400
Crédito disponible: $600
```

### 3. Estados de Pago

- **Pendiente**: Venta a crédito sin pagos
- **Parcial**: Venta con pagos parciales
- **Pagado**: Venta completamente pagada

## 🗄️ Estructura de Base de Datos

### Tabla: `Cliente`
```python
credito_habilitado = BooleanField()      # ¿Puede comprar a crédito?
limite_credito = DecimalField()          # Límite máximo
saldo_credito_actual = DecimalField()    # Deuda actual
dias_credito = IntegerField()            # Plazo en días
```

### Tabla: `CreditoMovimiento`
```python
cliente = ForeignKey(Cliente)
tipo = CharField()                       # 'cargo', 'pago', 'ajuste'
monto = DecimalField()
saldo_anterior = DecimalField()          # Para auditoría
saldo_nuevo = DecimalField()             # Para auditoría
venta = ForeignKey(Venta)               # Si es cargo
transaccion = ForeignKey(Transaccion)   # Si es pago
fecha = DateTimeField()
referencia = CharField()
notas = TextField()
```

### Tabla: `Venta`
```python
metodo_pago = CharField()                # 'credit' para crédito
estado_pago = CharField()                # 'pendiente', 'parcial', 'pagado'
saldo_pendiente = DecimalField()         # Monto pendiente de pago
```

## 🔐 Validaciones Importantes

### Al Crear Venta a Crédito
```python
# 1. Consumidor Final NO puede comprar a crédito
if cliente.es_consumidor_final():
    raise ValueError("Consumidor Final no puede comprar a crédito")

# 2. Cliente debe tener crédito habilitado
if not cliente.credito_habilitado:
    raise ValueError("Cliente no tiene crédito habilitado")

# 3. Verificar crédito disponible
if cliente.get_credito_disponible() < monto_venta:
    raise ValueError("Crédito insuficiente")
```

### Al Registrar Pago
```python
# No pagar más de lo que se debe
if monto_pago > cliente.saldo_credito_actual:
    raise ValueError("El monto excede la deuda actual")
```

## 📱 Funcionalidades del Sistema

### Para Clientes

1. **Habilitar Crédito**
   - Ir a: Clientes → Editar Cliente
   - Marcar "Crédito Habilitado"
   - Establecer "Límite de Crédito"
   - Definir "Días de Crédito"

2. **Ver Historial de Crédito**
   - Ir a: Clientes → Detalle Cliente → Ver Historial
   - Muestra todos los cargos y pagos
   - Saldos anteriores y nuevos para auditoría

3. **Registrar Pago**
   - Ir a: Clientes → Detalle Cliente → Registrar Pago
   - Ingresar monto, método de pago, referencia
   - Sistema actualiza automáticamente el saldo

### Para Ventas

1. **Venta a Crédito**
   - En el POS, seleccionar cliente
   - Agregar productos al carrito
   - Seleccionar "Método de Pago: Crédito"
   - Sistema valida y registra automáticamente

2. **Ver Clientes con Deuda**
   - Ir a: Clientes → Clientes con Deuda
   - Lista todos los clientes con saldo pendiente
   - Muestra porcentaje de uso del crédito
   - Acceso rápido a historial y pagos

## 🎨 Interfaz de Usuario

### Detalle del Cliente
Muestra una tarjeta de crédito con:
- Límite de crédito
- Saldo actual (en rojo)
- Crédito disponible (en verde)
- Barra de progreso visual
- Botones: "Ver Historial" y "Registrar Pago"

### Historial de Crédito
Tabla con:
- Fecha y hora del movimiento
- Tipo (Cargo 📤 / Pago 💰)
- Monto (+ para cargos, - para pagos)
- Saldo anterior y nuevo
- Referencia (venta o comprobante)
- Notas

### Clientes con Deuda
Lista con:
- Información del cliente
- Límite y saldo
- Porcentaje de uso (con colores)
- Acciones rápidas

## 🔧 Métodos Útiles

### En el Modelo Cliente

```python
# Verificar si puede comprar a crédito
cliente.puede_comprar_a_credito(monto)

# Obtener crédito disponible
cliente.get_credito_disponible()

# Registrar cargo (venta a crédito)
cliente.registrar_cargo_credito(
    monto=200,
    venta=venta_obj,
    usuario=request.user,
    notas="Venta #1234"
)

# Registrar pago
cliente.registrar_pago_credito(
    monto=150,
    transaccion=transaccion_obj,
    usuario=request.user,
    referencia="Comprobante #5678"
)
```

### En el Modelo Venta

```python
# Verificar si puede pagar a crédito
venta.puede_pagar_credito()

# Aplicar pago a venta
venta.aplicar_pago(
    monto=100,
    metodo_pago='cash',
    referencia='Pago parcial'
)
```

## 📈 Reportes y Análisis

### Calcular Saldo de Cliente
```python
from apps.transacciones.models import CreditoMovimiento

saldo = CreditoMovimiento.calcular_saldo_cliente(cliente)
```

### Obtener Historial
```python
movimientos = CreditoMovimiento.obtener_historial_cliente(
    cliente,
    limit=20  # Últimos 20 movimientos
)
```

## 🚨 Casos Especiales

### Consumidor Final
- **NO** puede comprar a crédito
- Solo puede pagar en efectivo, tarjeta o transferencia
- Validación automática en el sistema

### Pago Mixto (Futuro)
Permitir pagar parte en efectivo y parte a crédito:
```
Total: $300
- Efectivo: $100
- Crédito: $200
```

### Vencimientos (Futuro)
Agregar alertas cuando:
- Crédito está por vencer
- Cliente supera el 80% del límite
- Pagos atrasados

## 🔗 URLs Disponibles

```python
# Historial de crédito
/clientes/credito/<cliente_id>/historial/

# Registrar pago
/clientes/credito/<cliente_id>/pagar/

# Clientes con deuda
/clientes/credito/deudas/

# API: Verificar crédito
/clientes/credito/<cliente_id>/verificar/?monto=200
```

## ✅ Checklist de Implementación

- [x] Modelos de base de datos
- [x] Migraciones aplicadas
- [x] Vistas para gestión de crédito
- [x] Templates HTML
- [x] Validaciones de negocio
- [x] Integración con POS
- [x] Historial de movimientos
- [x] Registro de pagos
- [ ] Reportes de cuentas por cobrar
- [ ] Alertas de vencimiento
- [ ] Pago mixto
- [ ] Exportación a Excel/PDF

## 🎓 Mejores Prácticas

1. **Siempre validar** antes de permitir venta a crédito
2. **Registrar movimientos** para auditoría completa
3. **Actualizar saldos** de forma atómica (transacciones DB)
4. **Mostrar alertas** cuando el crédito esté por agotarse
5. **Revisar periódicamente** clientes con deuda
6. **Documentar** todos los ajustes manuales

## 📞 Soporte

Para dudas o problemas con el sistema de crédito, revisar:
- Este documento
- Código en `apps/clients/models.py`
- Código en `apps/transacciones/models.py`
- Vistas en `apps/clients/views.py`
