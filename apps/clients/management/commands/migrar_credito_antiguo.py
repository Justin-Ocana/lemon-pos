"""
Comando de Django para migrar datos de crédito antiguo al nuevo sistema.
Migra de 'credito' y 'cupo' a 'credito_habilitado', 'limite_credito', etc.

Ejecutar con: python manage.py migrar_credito_antiguo
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.clients.models import Cliente
from decimal import Decimal


class Command(BaseCommand):
    help = 'Migra datos de crédito antiguo (credito/cupo) al nuevo sistema de crédito'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la migración sin guardar cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("🔄 MIGRACIÓN DE SISTEMA DE CRÉDITO"))
        self.stdout.write("=" * 70)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  MODO DRY-RUN: No se guardarán cambios\n"))
        
        # Obtener todos los clientes
        clientes = Cliente.objects.all()
        total_clientes = clientes.count()
        
        self.stdout.write(f"\n📊 Total de clientes: {total_clientes}\n")
        
        # Contadores
        migrados = 0
        con_credito = 0
        sin_cambios = 0
        errores = 0
        
        with transaction.atomic():
            for cliente in clientes:
                try:
                    # Verificar si ya tiene el nuevo sistema configurado
                    if cliente.credito_habilitado or cliente.limite_credito > 0:
                        self.stdout.write(
                            f"⏭️  {cliente.nombre} - Ya tiene nuevo sistema configurado"
                        )
                        sin_cambios += 1
                        continue
                    
                    # Verificar si tiene crédito en el sistema antiguo
                    tiene_credito_antiguo = (
                        hasattr(cliente, 'credito') and cliente.credito > 0
                    ) or (
                        hasattr(cliente, 'cupo') and cliente.cupo > 0
                    )
                    
                    if not tiene_credito_antiguo:
                        sin_cambios += 1
                        continue
                    
                    # Migrar datos
                    self.stdout.write(f"\n🔄 Migrando: {cliente.nombre}")
                    
                    # Obtener valores antiguos
                    dias_credito_antiguo = getattr(cliente, 'credito', 0)
                    cupo_antiguo = getattr(cliente, 'cupo', Decimal('0'))
                    
                    self.stdout.write(f"   📋 Datos antiguos:")
                    self.stdout.write(f"      - Crédito (días): {dias_credito_antiguo}")
                    self.stdout.write(f"      - Cupo: ${cupo_antiguo}")
                    
                    # Configurar nuevo sistema
                    if cupo_antiguo > 0:
                        cliente.credito_habilitado = True
                        cliente.limite_credito = cupo_antiguo
                        cliente.saldo_credito_actual = Decimal('0')  # Empezar en 0
                        
                        # Mapear días de crédito
                        if dias_credito_antiguo > 0:
                            cliente.dias_credito = dias_credito_antiguo
                        else:
                            # Si no tenía días pero tenía cupo, asignar 30 días por defecto
                            cliente.dias_credito = 30
                        
                        self.stdout.write(f"   ✅ Datos nuevos:")
                        self.stdout.write(f"      - Crédito habilitado: Sí")
                        self.stdout.write(f"      - Límite de crédito: ${cliente.limite_credito}")
                        self.stdout.write(f"      - Saldo actual: ${cliente.saldo_credito_actual}")
                        self.stdout.write(f"      - Días de crédito: {cliente.dias_credito}")
                        
                        if not dry_run:
                            cliente.save(update_fields=[
                                'credito_habilitado',
                                'limite_credito',
                                'saldo_credito_actual',
                                'dias_credito'
                            ])
                        
                        migrados += 1
                        con_credito += 1
                    else:
                        sin_cambios += 1
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Error migrando {cliente.nombre}: {str(e)}")
                    )
                    errores += 1
            
            if dry_run:
                # Revertir transacción en dry-run
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("\n⚠️  Cambios revertidos (dry-run)"))
        
        # Resumen
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("📊 RESUMEN DE MIGRACIÓN"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"\n✅ Clientes migrados: {migrados}")
        self.stdout.write(f"💳 Con crédito habilitado: {con_credito}")
        self.stdout.write(f"⏭️  Sin cambios: {sin_cambios}")
        self.stdout.write(f"❌ Errores: {errores}")
        self.stdout.write(f"\n📊 Total procesados: {total_clientes}\n")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Esta fue una simulación. Ejecuta sin --dry-run para aplicar cambios.\n"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✅ Migración completada exitosamente!\n")
            )
        
        # Verificación final
        if not dry_run and migrados > 0:
            self.stdout.write("=" * 70)
            self.stdout.write("🔍 VERIFICACIÓN")
            self.stdout.write("=" * 70)
            
            clientes_con_credito = Cliente.objects.filter(credito_habilitado=True)
            self.stdout.write(f"\nClientes con crédito habilitado: {clientes_con_credito.count()}")
            
            if clientes_con_credito.exists():
                self.stdout.write("\nEjemplos:")
                for cliente in clientes_con_credito[:5]:
                    self.stdout.write(
                        f"  • {cliente.nombre}: "
                        f"Límite ${cliente.limite_credito}, "
                        f"Disponible ${cliente.get_credito_disponible()}, "
                        f"{cliente.dias_credito} días"
                    )
