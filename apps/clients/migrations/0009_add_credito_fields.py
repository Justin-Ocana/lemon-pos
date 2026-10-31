# Generated migration for credit system

from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0008_cliente_es_favorito_cliente_total_compras_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='credito_habilitado',
            field=models.BooleanField(default=False, verbose_name='Crédito Habilitado'),
        ),
        migrations.AddField(
            model_name='cliente',
            name='limite_credito',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=10,
                verbose_name='Límite de Crédito'
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='saldo_credito_actual',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=10,
                verbose_name='Saldo de Crédito Actual',
                help_text='Deuda actual del cliente'
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='dias_credito',
            field=models.IntegerField(
                default=0,
                verbose_name='Días de Crédito',
                help_text='Plazo en días para pagar (0 = sin plazo)'
            ),
        ),
    ]
