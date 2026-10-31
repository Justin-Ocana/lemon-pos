from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cliente
from .forms import ClienteForm
from django.http import JsonResponse
from django.db.models import Q

# Vista para buscar clientes mediante AJAX
def search_clients(request):
    """
    Busca clientes por nombre, identificación o código.
    Devuelve una respuesta JSON con los clientes coincidentes.
    """
    term = request.GET.get('term', '')
    
    if len(term) < 2:
        return JsonResponse({'results': []})
    
    # Busca clientes que coincidan con el término y pertenezcan al usuario actual
    clients = Cliente.objects.filter(
        Q(nombre__icontains=term) | 
        Q(identificacion__icontains=term) |
        Q(codigo__icontains=term)
    ).filter(estado=True, usuario_creador=request.user)[:10]  # Limita a 10 resultados
    
    # Formatea los resultados
    results = []
    for client in clients:
        results.append({
            'id': client.id,
            'codigo': client.codigo,
            'nombre': client.nombre,
            'identificacion': client.identificacion,
            'direccion': client.direccion,
            'ciudad': client.ciudad
        })
    
    return JsonResponse({'results': results})

# Vista para listar clientes
def lista_clientes(request):
    from django.db.models import Count, Sum
    from datetime import datetime, timedelta
    
    # Obtiene parámetros de consulta
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'nombre')
    estado_filter = request.GET.get('estado', '')
    
    # Filtra clientes por el usuario actual
    clientes = Cliente.objects.filter(usuario_creador=request.user)
    
    # Calcula métricas para el dashboard
    total_clientes = clientes.count()
    clientes_activos = clientes.filter(estado='activo').count()
    clientes_con_credito = clientes.filter(cupo__gt=0).count()
    
    # Clientes nuevos este mes
    primer_dia_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    clientes_nuevos_mes = clientes.filter(fecha_registro__gte=primer_dia_mes).count()
    
    # Aplica filtro de búsqueda si se proporciona (búsqueda mejorada)
    if query:
        clientes = clientes.filter(
            Q(nombre__icontains=query) |
            Q(identificacion__icontains=query) |
            Q(email__icontains=query) |
            Q(telefono__icontains=query) |
            Q(codigo__icontains=query)
        )
    
    # Aplica filtro por estado si se proporciona
    if estado_filter:
        clientes = clientes.filter(estado=estado_filter)
    
    # Aplica ordenación (favoritos primero si no hay ordenación específica)
    if sort_by == 'identificacion':
        clientes = clientes.order_by('identificacion')
    elif sort_by == 'email':
        clientes = clientes.order_by('email')
    elif sort_by == 'grupo':
        clientes = clientes.order_by('grupo')
    elif sort_by == 'estado':
        clientes = clientes.order_by('estado')
    else:
        clientes = clientes.order_by('-es_favorito', 'nombre')
    
    context = {
        'clientes': clientes,
        'query': query,
        'sort_by': sort_by,
        'estado_filter': estado_filter,
        'section_title': 'Lista de Clientes',
        # Métricas
        'total_clientes': total_clientes,
        'clientes_activos': clientes_activos,
        'clientes_con_credito': clientes_con_credito,
        'clientes_nuevos_mes': clientes_nuevos_mes,
    }
    
    return render(request, 'clients/lista_clientes.html', context)

# Vista para agregar un nuevo cliente
def agregar_cliente(request):
    if request.method == 'POST':
        # 🎯 Aplicar valores por defecto para campos no enviados desde el modal
        data = request.POST.copy()
        
        # Valores por defecto si no están presentes
        if 'grupo' not in data or not data['grupo']:
            data['grupo'] = 'regular'
        if 'estado' not in data or not data['estado']:
            data['estado'] = 'activo'
        if 'credito' not in data or not data['credito']:
            data['credito'] = 0
        if 'cupo' not in data or not data['cupo']:
            data['cupo'] = 0
        if 'tasa_descuento' not in data or not data['tasa_descuento']:
            data['tasa_descuento'] = 0
        if 'tasa_recargo' not in data or not data['tasa_recargo']:
            data['tasa_recargo'] = 0
        
        form = ClienteForm(data)
        if form.is_valid():
            # Guarda sin confirmar en la base de datos aún
            cliente = form.save(commit=False)
            # Asocia el cliente con el usuario actual
            cliente.usuario_creador = request.user
            cliente.save()
            
            # Si es una petición AJAX (desde el modal), devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/x-www-form-urlencoded':
                return JsonResponse({
                    'success': True,
                    'client_id': cliente.id,
                    'client_name': cliente.nombre,
                    'client_identification': cliente.identificacion,
                    'client_grupo': cliente.get_grupo_display(),
                    'client_credito': cliente.credito,
                    'client_cupo': float(cliente.cupo),
                    'client_tasa_descuento': float(cliente.tasa_descuento),
                    'client_tasa_recargo': float(cliente.tasa_recargo)
                })
            
            messages.success(request, 'Cliente agregado correctamente.')
            return redirect('clients:lista')
        else:
            # Si hay errores y es AJAX, devolver errores detallados
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/x-www-form-urlencoded':
                # Formatear errores de forma legible
                error_messages = []
                for field, errors in form.errors.items():
                    field_name = form.fields[field].label if field in form.fields else field
                    for error in errors:
                        error_messages.append(f"{field_name}: {error}")
                
                return JsonResponse({
                    'success': False,
                    'error': '\n'.join(error_messages)
                }, status=400)
            # Imprime errores del formulario si los hay
            print("Form errors:", form.errors)
    else:
        form = ClienteForm()
    
    return render(request, 'clients/form_cliente.html', {
        'form': form,
        'section_title': 'Agregar Cliente'
    })

# Vista para editar un cliente existente
def editar_cliente(request, cliente_id):
    # Solo permite editar clientes creados por el usuario actual
    cliente = get_object_or_404(Cliente, id=cliente_id, usuario_creador=request.user)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            # Imprime los datos del formulario para verificar
            print("Form data:", form.cleaned_data)
            cliente = form.save()
            # Imprime el cliente guardado para verificar el campo comentarios
            print("Saved cliente:", cliente.comentarios)
            messages.success(request, 'Cliente actualizado correctamente.')
            return redirect('clients:lista')
        else:
            # Imprime errores del formulario si los hay
            print("Form errors:", form.errors)
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'clients/form_cliente.html', {
        'form': form,
        'cliente': cliente,
        'section_title': 'Editar Cliente'
    })

# Vista para eliminar un cliente
def eliminar_cliente(request, cliente_id):
    # Solo permite eliminar clientes creados por el usuario actual
    cliente = get_object_or_404(Cliente, id=cliente_id, usuario_creador=request.user)
    
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente eliminado correctamente.')
        return redirect('clients:lista')
    
    return render(request, 'clients/eliminar_cliente.html', {
        'cliente': cliente,
        'section_title': 'Eliminar Cliente'
    })

# Vista para ver los detalles de un cliente
def detalle_cliente(request, cliente_id):
    # Solo permite ver clientes creados por el usuario actual
    cliente = get_object_or_404(Cliente, id=cliente_id, usuario_creador=request.user)
    
    # Obtener las ventas COMPLETADAS del cliente (que tienen transacción)
    from apps.ventas.models import Venta
    from apps.transacciones.models import Transaccion
    from django.db.models import Sum, Count, Exists, OuterRef
    
    # Solo ventas que tienen transacción (ventas completadas)
    ventas = Venta.objects.filter(
        cliente=cliente,
        usuario_creador=request.user
    ).annotate(
        tiene_transaccion=Exists(
            Transaccion.objects.filter(venta=OuterRef('pk'))
        )
    ).filter(
        tiene_transaccion=True
    ).order_by('-fecha_hora')[:10]
    
    # Calcular estadísticas reales solo de ventas completadas
    stats = Venta.objects.filter(
        cliente=cliente,
        usuario_creador=request.user
    ).annotate(
        tiene_transaccion=Exists(
            Transaccion.objects.filter(venta=OuterRef('pk'))
        )
    ).filter(
        tiene_transaccion=True
    ).aggregate(
        total_gastado=Sum('total'),
        total_compras=Count('id')
    )
    
    # Actualizar el cliente con las estadísticas reales si están desactualizadas
    if stats['total_gastado'] and stats['total_gastado'] != cliente.total_gastado:
        cliente.total_gastado = stats['total_gastado'] or 0
        cliente.total_compras = stats['total_compras'] or 0
        # Obtener la última compra COMPLETADA
        ultima_venta = Venta.objects.filter(
            cliente=cliente,
            usuario_creador=request.user
        ).annotate(
            tiene_transaccion=Exists(
                Transaccion.objects.filter(venta=OuterRef('pk'))
            )
        ).filter(
            tiene_transaccion=True
        ).order_by('-fecha_hora').first()
        if ultima_venta:
            cliente.ultima_compra = ultima_venta.fecha_hora
        cliente.save(update_fields=['total_gastado', 'total_compras', 'ultima_compra'])
    
    return render(request, 'clients/detalle_cliente.html', {
        'cliente': cliente,
        'ventas': ventas,
        'section_title': 'Detalle de Cliente',
        'total_gastado_real': stats['total_gastado'] or 0,
        'total_compras_real': stats['total_compras'] or 0,
    })

# Vista para búsqueda de clientes mediante AJAX
def client_search_view(request):
    """
    Maneja solicitudes de búsqueda AJAX para clientes.
    Si no hay término de búsqueda, devuelve todos los clientes del usuario.
    """
    search_term = request.GET.get('q', '')
    
    if search_term:
        # Filtra por el término de búsqueda y el usuario actual
        clients = Cliente.objects.filter(
            Q(nombre__icontains=search_term) | 
            Q(identificacion__icontains=search_term) |
            Q(telefono__icontains=search_term) |
            Q(email__icontains=search_term),
            usuario_creador=request.user
        ).values('id', 'nombre', 'identificacion', 'telefono', 'email', 'direccion', 'ciudad', 'codigo')[:50]
    else:
        # Si no hay término de búsqueda, devuelve todos los clientes (limitado a 50)
        clients = Cliente.objects.filter(
            usuario_creador=request.user
        ).order_by('-fecha_registro').values('id', 'nombre', 'identificacion', 'telefono', 'email', 'direccion', 'ciudad', 'codigo')[:50]
    
    return JsonResponse(list(clients), safe=False)

# Vista para marcar/desmarcar cliente como favorito
def toggle_favorito(request, cliente_id):
    """
    Marca o desmarca un cliente como favorito mediante AJAX.
    """
    if request.method == 'POST':
        cliente = get_object_or_404(Cliente, id=cliente_id, usuario_creador=request.user)
        cliente.es_favorito = not cliente.es_favorito
        cliente.save()
        return JsonResponse({
            'success': True,
            'es_favorito': cliente.es_favorito
        })
    return JsonResponse({'success': False}, status=400)



# ========================================
# VISTAS DE GESTIÓN DE CRÉDITO
# ========================================

def historial_credito_cliente(request, cliente_id):
    """
    Muestra el historial completo de movimientos de crédito de un cliente.
    """
    from apps.transacciones.models import CreditoMovimiento
    from django.core.paginator import Paginator
    
    cliente = get_object_or_404(Cliente, id=cliente_id, usuario_creador=request.user)
    
    # Obtener movimientos
    movimientos = CreditoMovimiento.obtener_historial_cliente(cliente)
    
    # Paginación
    paginator = Paginator(movimientos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular totales
    total_cargos = sum(
        m.monto for m in movimientos if m.tipo == 'cargo'
    )
    total_pagos = sum(
        m.monto for m in movimientos if m.tipo == 'pago'
    )
    
    context = {
        'cliente': cliente,
        'movimientos': page_obj,
        'total_cargos': total_cargos,
        'total_pagos': total_pagos,
        'section_title': f'Historial de Crédito - {cliente.nombre}'
    }
    
    return render(request, 'clients/historial_credito.html', context)


def registrar_pago_credito(request, cliente_id):
    """
    Registra un pago de crédito de un cliente.
    """
    from apps.transacciones.models import Transaccion
    from decimal import Decimal, InvalidOperation
    
    cliente = get_object_or_404(Cliente, id=cliente_id, usuario_creador=request.user)
    
    if request.method == 'POST':
        try:
            monto = Decimal(request.POST.get('monto', '0'))
            metodo_pago = request.POST.get('metodo_pago', 'cash')
            referencia = request.POST.get('referencia', '')
            notas = request.POST.get('notas', '')
            
            # Validaciones
            if monto <= 0:
                messages.error(request, 'El monto debe ser mayor a cero.')
                return redirect('clients:historial_credito', cliente_id=cliente_id)
            
            if monto > cliente.saldo_credito_actual:
                messages.error(
                    request,
                    f'El monto ${monto} excede la deuda actual ${cliente.saldo_credito_actual}'
                )
                return redirect('clients:historial_credito', cliente_id=cliente_id)
            
            # Crear transacción
            transaccion = Transaccion.objects.create(
                cliente=cliente,
                usuario_creador=request.user,
                tipo_transaccion='pago_credito',
                metodo_pago=metodo_pago,
                monto=monto,
                referencia=referencia,
                notas=notas
            )
            
            # Registrar movimiento de crédito
            cliente.registrar_pago_credito(
                monto=monto,
                transaccion=transaccion,
                usuario=request.user,
                referencia=referencia,
                notas=notas
            )
            
            messages.success(
                request,
                f'Pago de ${monto} registrado correctamente. Nuevo saldo: ${cliente.saldo_credito_actual}'
            )
            
            # Si es AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'nuevo_saldo': float(cliente.saldo_credito_actual),
                    'credito_disponible': float(cliente.get_credito_disponible())
                })
            
            return redirect('clients:historial_credito', cliente_id=cliente_id)
            
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f'Error en el monto ingresado: {str(e)}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            return redirect('clients:historial_credito', cliente_id=cliente_id)
        
        except Exception as e:
            messages.error(request, f'Error al registrar el pago: {str(e)}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            return redirect('clients:historial_credito', cliente_id=cliente_id)
    
    # GET request - mostrar formulario
    context = {
        'cliente': cliente,
        'section_title': f'Registrar Pago - {cliente.nombre}'
    }
    return render(request, 'clients/registrar_pago.html', context)


def clientes_con_deuda(request):
    """
    Lista todos los clientes que tienen deuda pendiente.
    """
    from django.db.models import Q
    from decimal import Decimal
    
    # Filtrar clientes con saldo > 0
    clientes = Cliente.objects.filter(
        usuario_creador=request.user,
        saldo_credito_actual__gt=Decimal('0')
    ).order_by('-saldo_credito_actual')
    
    # Búsqueda
    query = request.GET.get('q', '')
    if query:
        clientes = clientes.filter(
            Q(nombre__icontains=query) |
            Q(identificacion__icontains=query)
        )
    
    # Calcular totales
    total_deuda = sum(c.saldo_credito_actual for c in clientes)
    total_clientes_deuda = clientes.count()
    
    context = {
        'clientes': clientes,
        'total_deuda': total_deuda,
        'total_clientes_deuda': total_clientes_deuda,
        'query': query,
        'section_title': 'Clientes con Deuda'
    }
    
    return render(request, 'clients/clientes_con_deuda.html', context)


def verificar_credito_disponible(request, cliente_id):
    """
    API endpoint para verificar si un cliente tiene crédito disponible.
    Usado en el POS antes de permitir venta a crédito.
    """
    from decimal import Decimal
    
    cliente = get_object_or_404(Cliente, id=cliente_id, usuario_creador=request.user)
    monto = request.GET.get('monto', '0')
    
    try:
        monto = Decimal(monto)
        puede_comprar = cliente.puede_comprar_a_credito(monto)
        
        return JsonResponse({
            'success': True,
            'puede_comprar': puede_comprar,
            'credito_habilitado': cliente.credito_habilitado,
            'limite_credito': float(cliente.limite_credito),
            'saldo_actual': float(cliente.saldo_credito_actual),
            'credito_disponible': float(cliente.get_credito_disponible()),
            'monto_solicitado': float(monto),
            'mensaje': 'Crédito disponible' if puede_comprar else 'Crédito insuficiente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
