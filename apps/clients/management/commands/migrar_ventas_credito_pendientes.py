"""
Comando para migrar ventas a crédito existentes y sincronizar sus estados.
Actualiza el estado_pago de las ventas basándose en el saldo del cliente.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.clients.models import Cliente
from apps.ventas.models import Venta
from apps.transacciones.models import CreditoMovimiento
from decimal import Decimal


class Command(BaseCommand):
    help = 'Migra ventas a crédito existentes y sincroniza estados de pago'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la migración sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO SIMULACIÓN - No se harán cambios reales\n'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  MODO REAL - Se harán cambios en la base de datos\n'))
        
        # Estadísticas
        stats = {
            'clientes_procesados': 0,
            'ventas_actualizadas': 0,
            'movimientos_creados': 0,
            'saldos_corregidos': 0,
            'errores': 0
        }
        
        # 🎯 PASO 1: Procesar TODAS las ventas a crédito (no solo clientes con saldo)
        ventas_credito = Venta.objects.filter(metodo_pago='credit').select_related('cliente')
        
        self.stdout.write(f'\n📊 Ventas a crédito encontradas: {ventas_credito.count()}\n')
        
        # Agrupar por cliente
        clientes_con_ventas = {}
        for venta in ventas_credito:
            if venta.cliente:
                if venta.cliente.id not in clientes_con_ventas:
                    clientes_con_ventas[venta.cliente.id] = {
                        'cliente': venta.cliente,
                        'ventas': []
                    }
                clientes_con_ventas[venta.cliente.id]['ventas'].append(venta)
        
        self.stdout.write(f'👥 Clientes con ventas a crédito: {len(clientes_con_ventas)}\n')
        
        for cliente_id, data in clientes_con_ventas.items():
            cliente = data['cliente']
            ventas = data['ventas']
            
            self.stdout.write(f'\n👤 Procesando: {cliente.nombre} (ID: {cliente.id})')
            self.stdout.write(f'   Saldo actual: ${cliente.saldo_credito_actual}')
            self.stdout.write(f'   Ventas a crédito: {len(ventas)}')
            
            try:
                with transaction.atomic():
                    # Calcular total de ventas a crédito
                    total_ventas = sum(v.total for v in ventas)
                    self.stdout.write(f'   💰 Total en ventas: ${total_ventas}')
                    
                    # Verificar si ya tiene movimientos
                    movimientos_existentes = CreditoMovimiento.objects.filter(cliente=cliente).count()
                    
                    if movimientos_existentes == 0:
                        self.stdout.write(f'   🔧 Creando movimientos de crédito...')
                        
                        # Crear movimientos para cada venta a crédito
                        saldo_acumulado = Decimal('0')
                        
                        for venta in sorted(ventas, key=lambda v: v.fecha_hora):
                            saldo_anterior = saldo_acumulado
                            saldo_acumulado += venta.total
                            
                            # Crear movimiento de cargo
                            if not dry_run:
                                CreditoMovimiento.objects.create(
                                    cliente=cliente,
                                    venta=venta,
                                    tipo='cargo',
                                    monto=venta.total,
                                    saldo_anterior=saldo_anterior,
                                    saldo_nuevo=saldo_acumulado,
                                    usuario_creador=venta.usuario_creador,
                                    notas=f'Migración: Venta a crédito #{venta.numero_factura or venta.id}'
                                )
                                stats['movimientos_creados'] += 1
                            
                            self.stdout.write(f'      ✓ Venta #{venta.numero_factura or venta.id}: ${venta.total}')
                        
                        # 🎯 Corregir saldo del cliente si está en 0
                        if cliente.saldo_credito_actual == 0 and total_ventas > 0:
                            self.stdout.write(f'   ⚠️  Saldo del cliente en $0, corrigiendo a ${total_ventas}')
                            if not dry_run:
                                cliente.saldo_credito_actual = total_ventas
                                cliente.save(update_fields=['saldo_credito_actual'])
                                stats['saldos_corregidos'] += 1
                    else:
                        self.stdout.write(f'   ℹ️  Ya tiene {movimientos_existentes} movimientos registrados')
                    
                    # Actualizar estados de ventas
                    saldo_cliente = cliente.saldo_credito_actual if not dry_run else total_ventas
                    monto_pagado = total_ventas - saldo_cliente
                    
                    if monto_pagado > 0:
                        self.stdout.write(f'   ✅ Pagos detectados: ${monto_pagado}')
                        
                        # Aplicar pagos a ventas (FIFO)
                        monto_restante = monto_pagado
                        
                        for venta in sorted(ventas, key=lambda v: v.fecha_hora):
                            if monto_restante <= 0:
                                # Ventas sin pagar
                                if not dry_run:
                                    venta.saldo_pendiente = venta.total
                                    venta.estado_pago = 'pendiente'
                                    venta.save(update_fields=['saldo_pendiente', 'estado_pago'])
                                    stats['ventas_actualizadas'] += 1
                                
                                self.stdout.write(
                                    f'      ✓ Venta #{venta.numero_factura or venta.id}: '
                                    f'Pendiente ${venta.total}'
                                )
                            else:
                                monto_a_aplicar = min(monto_restante, venta.total)
                                
                                if not dry_run:
                                    venta.saldo_pendiente = venta.total - monto_a_aplicar
                                    
                                    if venta.saldo_pendiente == 0:
                                        venta.estado_pago = 'pagado'
                                    elif venta.saldo_pendiente < venta.total:
                                        venta.estado_pago = 'parcial'
                                    else:
                                        venta.estado_pago = 'pendiente'
                                    
                                    venta.save(update_fields=['saldo_pendiente', 'estado_pago'])
                                    stats['ventas_actualizadas'] += 1
                                
                                self.stdout.write(
                                    f'      ✓ Venta #{venta.numero_factura or venta.id}: '
                                    f'Pagado ${monto_a_aplicar}, Pendiente ${venta.total - monto_a_aplicar}, '
                                    f'Estado: {venta.estado_pago if not dry_run else "simulado"}'
                                )
                                
                                monto_restante -= monto_a_aplicar
                    else:
                        # Todas las ventas están pendientes
                        for venta in ventas:
                            if not dry_run:
                                venta.saldo_pendiente = venta.total
                                venta.estado_pago = 'pendiente'
                                venta.save(update_fields=['saldo_pendiente', 'estado_pago'])
                                stats['ventas_actualizadas'] += 1
                            
                            self.stdout.write(
                                f'      ✓ Venta #{venta.numero_factura or venta.id}: '
                                f'Pendiente ${venta.total}'
                            )
                    
                    stats['clientes_procesados'] += 1
                    self.stdout.write(self.style.SUCCESS(f'   ✅ Cliente procesado correctamente'))
                    
                    if dry_run:
                        # En modo simulación, revertir la transacción
                        transaction.set_rollback(True)
            
            except Exception as e:
                stats['errores'] += 1
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                continue
        
        # Resumen final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('\n📊 RESUMEN DE MIGRACIÓN\n'))
        self.stdout.write(f'Clientes procesados: {stats["clientes_procesados"]}')
        self.stdout.write(f'Ventas actualizadas: {stats["ventas_actualizadas"]}')
        self.stdout.write(f'Movimientos creados: {stats["movimientos_creados"]}')
        self.stdout.write(f'Saldos corregidos: {stats["saldos_corregidos"]}')
        self.stdout.write(f'Errores: {stats["errores"]}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  Esto fue una SIMULACIÓN. Ejecuta sin --dry-run para aplicar cambios.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Migración completada exitosamente!'))
