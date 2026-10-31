from django.db import models, IntegrityError
from django.conf import settings
import time
import random
from django.utils import timezone
from decimal import Decimal

class Transaccion(models.Model):
    TIPO_TRANSACCION_CHOICES = [
        ('venta', 'Pago de Venta'),
        ('pago_credito', 'Pago de Crédito'),
        ('devolucion', 'Devolución'),
        ('abono', 'Abono a Cuenta'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('cash', 'Efectivo'),
        ('card', 'Tarjeta'),
        ('transfer', 'Transferencia'),
        ('credit', 'Crédito'),
    ]
    
    # === IDENTIFICACIÓN ===
    transaction_id = models.PositiveIntegerField(primary_key=True, unique=True)
    factuID = models.PositiveIntegerField(editable=False)
    numero_factura_usuario = models.PositiveIntegerField(editable=False)
    
    # === RELACIONES ===
    venta = models.ForeignKey('ventas.Venta', on_delete=models.CASCADE, null=True, blank=True)
    usuario_creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cliente = models.ForeignKey('clients.Cliente', on_delete=models.SET_NULL, null=True, blank=True)  # Para pagos de crédito
    
    # === TIPO Y MÉTODO ===
    tipo_transaccion = models.CharField(
        max_length=20,
        choices=TIPO_TRANSACCION_CHOICES,
        default='venta',
        verbose_name="Tipo de Transacción"
    )
    metodo_pago = models.CharField(max_length=50, choices=METODO_PAGO_CHOICES)
    
    # === MONTOS ===
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    venta_total_snapshot = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Total de Venta (Snapshot)",
        help_text="Snapshot del total de la venta al momento de la transacción"
    )
    
    # === METADATA ===
    fecha = models.DateTimeField(auto_now_add=True)
    procesado_pago = models.BooleanField(default=False)
    referencia = models.CharField(max_length=100, null=True, blank=True, verbose_name="Referencia Bancaria")
    notas = models.TextField(null=True, blank=True, verbose_name="Notas Adicionales")

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            max_retries = 10
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Generate a random transaction_id for global uniqueness
                    self.transaction_id = random.randint(100000, 999999)
                    
                    # Get the last factuID for this specific user
                    last_user_transaction = Transaccion.objects.filter(
                        usuario_creador=self.usuario_creador
                    ).order_by('-factuID').first()
                    
                    # Set factuID as sequential per user starting from 1
                    if last_user_transaction:
                        self.factuID = last_user_transaction.factuID + 1
                    else:
                        self.factuID = 1
                    
                    # Keep numero_factura_usuario for backward compatibility
                    self.numero_factura_usuario = self.factuID
                    
                    super().save(*args, **kwargs)
                    break
                except IntegrityError:
                    retry_count += 1
                    if retry_count >= max_retries:
                        # If we've tried too many times with random IDs, use a sequential approach
                        max_id = Transaccion.objects.aggregate(models.Max('transaction_id'))['transaction_id__max'] or 0
                        self.transaction_id = max_id + 1
                        
                        # Get the last factuID for this specific user
                        last_user_transaction = Transaccion.objects.filter(
                            usuario_creador=self.usuario_creador
                        ).order_by('-factuID').first()
                        
                        # Set factuID as sequential per user
                        if last_user_transaction:
                            self.factuID = last_user_transaction.factuID + 1
                        else:
                            self.factuID = 1
                        
                        # Keep numero_factura_usuario for backward compatibility
                        self.numero_factura_usuario = self.factuID
                            
                        super().save(*args, **kwargs)
                        break
                    time.sleep(0.1)
        else:
            # If transaction_id already exists, we don't modify factuID or numero_factura_usuario
            # to maintain the sequential numbering per user
            super().save(*args, **kwargs)



class CreditoMovimiento(models.Model):
    """
    Modelo para registrar todos los movimientos de crédito de un cliente.
    Mantiene un historial completo de cargos y pagos.
    
    Tipos de movimiento:
    - cargo: Nueva compra a crédito (aumenta deuda)
    - pago: Pago/abono del cliente (disminuye deuda)
    - ajuste: Ajuste manual (puede aumentar o disminuir)
    """
    
    TIPO_CHOICES = [
        ('cargo', 'Cargo'),
        ('pago', 'Pago'),
        ('ajuste', 'Ajuste'),
    ]
    
    # === RELACIONES ===
    cliente = models.ForeignKey(
        'clients.Cliente',
        on_delete=models.CASCADE,
        related_name='movimientos_credito',
        verbose_name='Cliente'
    )
    venta = models.ForeignKey(
        'ventas.Venta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_credito',
        verbose_name='Venta'
    )
    transaccion = models.ForeignKey(
        'Transaccion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_credito',
        verbose_name='Transacción'
    )
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='movimientos_credito_creados',
        verbose_name='Usuario'
    )
    
    # === DATOS DEL MOVIMIENTO ===
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de Movimiento'
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto'
    )
    
    # === SALDOS (para auditoría) ===
    saldo_anterior = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Saldo Anterior'
    )
    saldo_nuevo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Saldo Nuevo'
    )
    
    # === METADATA ===
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    referencia = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Referencia'
    )
    notas = models.TextField(null=True, blank=True, verbose_name='Notas')
    
    class Meta:
        verbose_name = 'Movimiento de Crédito'
        verbose_name_plural = 'Movimientos de Crédito'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['cliente', '-fecha'], name='credito_cliente_fecha_idx'),
            models.Index(fields=['tipo', '-fecha'], name='credito_tipo_fecha_idx'),
        ]
    
    def __str__(self):
        signo = '+' if self.tipo == 'cargo' else '-'
        return f"{self.cliente.nombre} - {self.get_tipo_display()} {signo}${self.monto}"
    
    def get_tipo_icon(self):
        """Retorna el ícono para mostrar según el tipo"""
        icons = {
            'cargo': '📤',  # Salida de dinero (cargo al cliente)
            'pago': '💰',   # Entrada de dinero (pago del cliente)
            'ajuste': '⚙️'  # Ajuste manual
        }
        return icons.get(self.tipo, '📝')
    
    def get_tipo_color(self):
        """Retorna la clase CSS de color según el tipo"""
        colors = {
            'cargo': 'text-red-600',
            'pago': 'text-green-600',
            'ajuste': 'text-blue-600'
        }
        return colors.get(self.tipo, 'text-gray-600')
    
    @classmethod
    def calcular_saldo_cliente(cls, cliente):
        """
        Calcula el saldo de un cliente basado en sus movimientos.
        Útil para verificar integridad de datos.
        """
        movimientos = cls.objects.filter(cliente=cliente).order_by('fecha')
        
        saldo = Decimal('0')
        for mov in movimientos:
            if mov.tipo == 'cargo':
                saldo += mov.monto
            elif mov.tipo == 'pago':
                saldo -= mov.monto
            elif mov.tipo == 'ajuste':
                # Los ajustes pueden ser positivos o negativos
                saldo = mov.saldo_nuevo
        
        return saldo
    
    @classmethod
    def obtener_historial_cliente(cls, cliente, limit=None):
        """
        Obtiene el historial de movimientos de un cliente.
        """
        queryset = cls.objects.filter(cliente=cliente).select_related(
            'venta', 'transaccion', 'usuario_creador'
        )
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
