from django.db import models
from django.conf import settings

# Modelo para los clientes
class Cliente(models.Model):
    # Relación con el usuario creador
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clientes',
        null=True
    )
    
    # Opciones para el campo grupo
    GRUPO_CHOICES = [
        ('regular', 'Regular'),
        ('vip', 'VIP'),
        ('corporativo', 'Corporativo'),
    ]
    
    # Opciones para el campo estado
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('suspendido', 'Suspendido'),
    ]
    
    # Opciones para el campo crédito
    CREDITO_CHOICES = [
        (0, 'Sin crédito'),
        (15, '15 días'),
        (30, '30 días'),
        (45, '45 días'),
        (60, '60 días'),
        (90, '90 días'),
    ]
    
    # Campos del modelo
    codigo = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    razon_social = models.CharField(max_length=200, blank=True, null=True, verbose_name="Razón Social")
    identificacion = models.CharField(max_length=20, verbose_name="Identificación")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    grupo = models.CharField(max_length=20, choices=GRUPO_CHOICES, default='regular', verbose_name="Grupo")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo', verbose_name="Estado")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")
    
    # Nuevos campos
    credito = models.IntegerField(choices=CREDITO_CHOICES, default=0, verbose_name="Crédito (días)")
    cupo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cupo")
    tasa_descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tasa de descuento (%)")
    tasa_recargo = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Tasa de recargo (%)")
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    comentarios = models.TextField(blank=True, null=True)
    
    # Campos adicionales para mejoras profesionales
    es_favorito = models.BooleanField(default=False, verbose_name="Cliente Favorito")
    total_gastado = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Gastado")
    total_compras = models.IntegerField(default=0, verbose_name="Total de Compras")
    ultima_compra = models.DateTimeField(null=True, blank=True, verbose_name="Última Compra")
    
    # === SISTEMA DE CRÉDITO ===
    credito_habilitado = models.BooleanField(default=False, verbose_name="Crédito Habilitado")
    limite_credito = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Límite de Crédito"
    )
    saldo_credito_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Saldo de Crédito Actual",
        help_text="Deuda actual del cliente"
    )
    dias_credito = models.IntegerField(
        default=0,
        verbose_name="Días de Crédito",
        help_text="Plazo en días para pagar (0 = sin plazo)"
    )
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre']
    
    # Representación en cadena del objeto
    def __str__(self):
        return self.nombre
    
    def get_iniciales(self):
        """Retorna las iniciales del nombre del cliente"""
        palabras = self.nombre.split()
        if len(palabras) >= 2:
            return f"{palabras[0][0]}{palabras[1][0]}".upper()
        elif len(palabras) == 1:
            return palabras[0][:2].upper()
        return "CL"
    
    def get_credito_disponible(self):
        """Calcula el crédito disponible del cliente"""
        if not self.credito_habilitado or self.limite_credito <= 0:
            return Decimal('0')
        return self.limite_credito - self.saldo_credito_actual
    
    def tiene_credito_disponible(self, monto_requerido):
        """Verifica si el cliente tiene crédito suficiente para un monto"""
        from decimal import Decimal
        if isinstance(monto_requerido, (int, float)):
            monto_requerido = Decimal(str(monto_requerido))
        return self.get_credito_disponible() >= monto_requerido
    
    def registrar_cargo_credito(self, monto, venta=None, usuario=None, notas=None):
        """
        Registra un cargo a crédito (nueva compra).
        Actualiza el saldo y crea el movimiento.
        """
        from decimal import Decimal
        from apps.transacciones.models import CreditoMovimiento
        
        if isinstance(monto, (int, float)):
            monto = Decimal(str(monto))
        
        # Validar que tenga crédito disponible
        if not self.tiene_credito_disponible(monto):
            raise ValueError(
                f"Crédito insuficiente. Disponible: ${self.get_credito_disponible()}, "
                f"Requerido: ${monto}"
            )
        
        # Guardar saldo anterior
        saldo_anterior = self.saldo_credito_actual
        
        # Actualizar saldo
        self.saldo_credito_actual += monto
        self.save(update_fields=['saldo_credito_actual'])
        
        # Crear movimiento
        movimiento = CreditoMovimiento.objects.create(
            cliente=self,
            tipo='cargo',
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=self.saldo_credito_actual,
            venta=venta,
            usuario_creador=usuario or venta.usuario_creador if venta else None,
            notas=notas or f"Compra a crédito - Venta #{venta.id if venta else 'N/A'}"
        )
        
        return movimiento
    
    def registrar_pago_credito(self, monto, transaccion=None, usuario=None, referencia=None, notas=None):
        """
        Registra un pago de crédito (abono a deuda).
        Actualiza el saldo y crea el movimiento.
        Aplica el pago a las ventas pendientes usando FIFO (First In, First Out).
        """
        from decimal import Decimal
        from apps.transacciones.models import CreditoMovimiento
        from apps.ventas.models import Venta
        
        if isinstance(monto, (int, float)):
            monto = Decimal(str(monto))
        
        # Validar que no pague más de lo que debe
        if monto > self.saldo_credito_actual:
            raise ValueError(
                f"El monto ${monto} excede la deuda actual ${self.saldo_credito_actual}"
            )
        
        # Guardar saldo anterior
        saldo_anterior = self.saldo_credito_actual
        
        # Actualizar saldo del cliente
        self.saldo_credito_actual -= monto
        self.save(update_fields=['saldo_credito_actual'])
        
        # 🎯 APLICAR PAGO A VENTAS PENDIENTES (FIFO)
        # Obtener ventas con saldo pendiente, ordenadas por fecha (más antiguas primero)
        ventas_pendientes = Venta.objects.filter(
            cliente=self,
            estado_pago__in=['pendiente', 'parcial']
        ).order_by('fecha_hora')
        
        monto_restante = monto
        ventas_afectadas = []
        
        for venta in ventas_pendientes:
            if monto_restante <= 0:
                break
            
            # Aplicar lo que se pueda a esta venta
            monto_a_aplicar = min(monto_restante, venta.saldo_pendiente)
            
            if monto_a_aplicar > 0:
                # Actualizar venta
                venta.saldo_pendiente -= monto_a_aplicar
                
                # Actualizar estado
                if venta.saldo_pendiente == 0:
                    venta.estado_pago = 'pagado'
                elif venta.saldo_pendiente < venta.total:
                    venta.estado_pago = 'parcial'
                
                venta.save(update_fields=['saldo_pendiente', 'estado_pago'])
                
                ventas_afectadas.append({
                    'venta_id': venta.id,
                    'numero_factura': venta.numero_factura,
                    'monto_aplicado': monto_a_aplicar,
                    'nuevo_estado': venta.estado_pago
                })
                
                monto_restante -= monto_a_aplicar
        
        # Crear movimiento con información de ventas afectadas
        notas_completas = notas or "Pago de crédito"
        if ventas_afectadas:
            etiquetas = ', '.join(
                '#{}'.format(v['numero_factura'] or v['venta_id']) for v in ventas_afectadas
            )
            notas_completas += f"\nVentas afectadas: {etiquetas}"
        
        movimiento = CreditoMovimiento.objects.create(
            cliente=self,
            tipo='pago',
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=self.saldo_credito_actual,
            transaccion=transaccion,
            usuario_creador=usuario,
            referencia=referencia,
            notas=notas_completas
        )
        
        return movimiento
    
    @staticmethod
    def get_consumidor_final(usuario):
        """
        Obtiene o crea el cliente Consumidor Final para el usuario.
        Usa el cliente del sistema con identificación 9999999999.
        """
        consumidor_final, created = Cliente.objects.get_or_create(
            identificacion='9999999999',
            defaults={
                'codigo': 'CF-001',
                'nombre': 'Consumidor Final',
                'razon_social': 'CONSUMIDOR FINAL',
                'direccion': 'N/A',
                'ciudad': 'N/A',
                'grupo': 'regular',
                'estado': 'activo',
                'credito': 0,
                'cupo': 0,
                'tasa_descuento': 0,
                'tasa_recargo': 0,
                'comentarios': 'Cliente por defecto para ventas sin identificación. NO ELIMINAR.',
                'es_favorito': False,
                'usuario_creador': usuario
            }
        )
        return consumidor_final
    
    def es_consumidor_final(self):
        """Verifica si este cliente es el Consumidor Final del sistema"""
        return self.identificacion == '9999999999'
    
    def puede_comprar_a_credito(self, monto_venta=None):
        """
        Verifica si el cliente puede comprar a crédito.
        Consumidor Final NO puede comprar a crédito.
        Si se proporciona monto_venta, verifica que el crédito disponible sea suficiente.
        """
        if self.es_consumidor_final():
            return False
        
        # Verificar condiciones básicas
        if self.estado != 'activo' or not self.credito_habilitado:
            return False
        
        # Si no se proporciona monto, solo verificar que tenga límite de crédito
        if monto_venta is None:
            return self.limite_credito > 0
        
        # Si se proporciona monto, verificar que el crédito disponible sea suficiente
        return self.tiene_credito_disponible(monto_venta)
    
    def actualizar_estadisticas_compra(self, monto_venta):
        """
        Actualiza las estadísticas del cliente después de una compra.
        - Incrementa total_gastado
        - Incrementa total_compras
        - Actualiza ultima_compra
        """
        from decimal import Decimal
        from django.utils import timezone
        
        if isinstance(monto_venta, (int, float)):
            monto_venta = Decimal(str(monto_venta))
        
        self.total_gastado += monto_venta
        self.total_compras += 1
        self.ultima_compra = timezone.now()
        self.save(update_fields=['total_gastado', 'total_compras', 'ultima_compra'])