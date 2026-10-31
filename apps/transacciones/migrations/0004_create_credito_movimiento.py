# Generated migration for CreditoMovimiento model

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('transacciones', '0003_transaccion_venta_total_snapshot'),
        ('clients', '0009_add_credito_fields'),
        ('ventas', '0010_detalleventa_iva_monto_cajasesion_venta_caja_sesion_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CreditoMovimiento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(
                    choices=[('cargo', 'Cargo'), ('pago', 'Pago'), ('ajuste', 'Ajuste')],
                    max_length=20,
                    verbose_name='Tipo de Movimiento'
                )),
                ('monto', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monto')),
                ('saldo_anterior', models.DecimalField(
                    decimal_places=2,
                    max_digits=10,
                    verbose_name='Saldo Anterior'
                )),
                ('saldo_nuevo', models.DecimalField(
                    decimal_places=2,
                    max_digits=10,
                    verbose_name='Saldo Nuevo'
                )),
                ('fecha', models.DateTimeField(auto_now_add=True, verbose_name='Fecha')),
                ('referencia', models.CharField(
                    blank=True,
                    max_length=100,
                    null=True,
                    verbose_name='Referencia'
                )),
                ('notas', models.TextField(blank=True, null=True, verbose_name='Notas')),
                ('cliente', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='movimientos_credito',
                    to='clients.cliente',
                    verbose_name='Cliente'
                )),
                ('venta', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='movimientos_credito',
                    to='ventas.venta',
                    verbose_name='Venta'
                )),
                ('transaccion', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='movimientos_credito',
                    to='transacciones.transaccion',
                    verbose_name='Transacción'
                )),
                ('usuario_creador', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='movimientos_credito_creados',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuario'
                )),
            ],
            options={
                'verbose_name': 'Movimiento de Crédito',
                'verbose_name_plural': 'Movimientos de Crédito',
                'ordering': ['-fecha'],
                'indexes': [
                    models.Index(fields=['cliente', '-fecha'], name='transaccion_cliente_fecha_idx'),
                    models.Index(fields=['tipo', '-fecha'], name='transaccion_tipo_fecha_idx'),
                ],
            },
        ),
    ]
