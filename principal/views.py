from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ConfiguracionForm, CruceForm, ProductoForm
from .models import (
    Caja, Categoria, Cliente, Configuracion, ConteoCaja, DetalleVenta,
    MovimientoKardex, Producto, Sucursal, Venta,
)
from .permisos import es_dueno, requiere_dueno
from .pdf import render_pdf_response


def _ctx_cierre_caja(caja):
    resumen = caja.resumen()
    ventas = caja.ventas().order_by('fecha')
    try:
        conteo = caja.conteo
    except ConteoCaja.DoesNotExist:
        conteo = None
    return {
        'caja': caja,
        'resumen': resumen,
        'ventas': ventas,
        'conteo': conteo,
        'config': Configuracion.obtener(),
    }

DIAS_SEMANA = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom']


def _a_decimal(valor):
    if valor in (None, ''):
        return None
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return None


@login_required
def panel(request):
    hoy = timezone.localdate()
    inicio_semana = hoy - timedelta(days=6)
    inicio_anterior = hoy - timedelta(days=13)

    productos = Producto.objects.select_related('categoria')
    ventas_hoy_qs = Venta.objects.filter(fecha__date=hoy)

    resumen = productos.aggregate(
        unidades=Sum('stock'),
        valor_costo=Sum(F('precio_compra') * F('stock')),
        valor_venta=Sum(F('precio_venta') * F('stock')),
    )

    ganancia_hoy = (
        DetalleVenta.objects.filter(venta__in=ventas_hoy_qs)
        .aggregate(
            g=Sum(
                F('precio_unitario') * F('cantidad')
                - F('producto__precio_compra') * F('cantidad')
            )
        )['g']
    ) or 0

    ticket_promedio = ventas_hoy_qs.aggregate(t=Avg('total'))['t'] or 0

    # Serie de ventas de los últimos 7 días para el gráfico
    ventas_por_dia = {
        fila['fecha__date']: fila
        for fila in (
            Venta.objects.filter(fecha__date__gte=inicio_semana)
            .values('fecha__date')
            .annotate(total=Sum('total'), numero=Count('id'))
        )
    }
    serie_dias = []
    for i in range(7):
        dia = inicio_semana + timedelta(days=i)
        datos = ventas_por_dia.get(dia, {})
        serie_dias.append({
            'etiqueta': f"{DIAS_SEMANA[dia.weekday()]} {dia:%d/%m}",
            'total': datos.get('total') or 0,
            'numero': datos.get('numero') or 0,
            'es_hoy': dia == hoy,
        })
    maximo_dia = max((d['total'] for d in serie_dias), default=0)

    # Coordenadas del gráfico lineal (SVG 560x150)
    ancho, alto = 560, 150
    paso_x = (ancho - 40) / 6
    for i, d in enumerate(serie_dias):
        d['x'] = round(20 + i * paso_x, 1)
        if maximo_dia:
            d['y'] = round(alto - 12 - (d['total'] / maximo_dia) * (alto - 26), 1)
        else:
            d['y'] = alto - 12

    linea_puntos = ' '.join(f"{d['x']},{d['y']}" for d in serie_dias)
    area_puntos = (
        linea_puntos
        + f" {serie_dias[-1]['x']},{alto - 6} {serie_dias[0]['x']},{alto - 6}"
    )

    total_semana = sum(d['total'] for d in serie_dias)
    total_anterior = (
        Venta.objects.filter(
            fecha__date__gte=inicio_anterior, fecha__date__lt=inicio_semana
        ).aggregate(t=Sum('total'))['t']
        or 0
    )
    if total_anterior > 0:
        variacion = round((total_semana - total_anterior) / total_anterior * 100)
    elif total_semana > 0:
        variacion = None
    else:
        variacion = 0

    top_vendidos = list(
        DetalleVenta.objects
        .values('producto__nombre')
        .annotate(
            unidades=Sum('cantidad'),
            ingresos=Sum(F('precio_unitario') * F('cantidad')),
        )
        .order_by('-unidades')[:5]
    )
    maximo_top = max((t['unidades'] for t in top_vendidos), default=0)
    for t in top_vendidos:
        t['porcentaje'] = int(t['unidades'] / maximo_top * 100) if maximo_top else 0

    bajo_stock = [p for p in productos if p.bajo_stock]
    num_agotados = sum(1 for p in bajo_stock if p.stock == 0)

    contexto = {
        'hoy': hoy,
        'total_productos': productos.count(),
        'total_categorias': Categoria.objects.count(),
        'unidades_totales': resumen['unidades'] or 0,
        'valor_inventario': resumen['valor_costo'] or 0,
        'valor_venta_inventario': resumen['valor_venta'] or 0,
        'ventas_hoy_cantidad': ventas_hoy_qs.count(),
        'ventas_hoy_total': ventas_hoy_qs.aggregate(t=Sum('total'))['t'] or 0,
        'ganancia_hoy': ganancia_hoy,
        'ticket_promedio': ticket_promedio,
        'serie_dias': serie_dias,
        'linea_puntos': linea_puntos,
        'area_puntos': area_puntos,
        'total_semana': total_semana,
        'variacion': variacion,
        'bajo_stock': bajo_stock,
        'num_agotados': num_agotados,
        'top_vendidos': top_vendidos,
        'ultimas_ventas': (
            Venta.objects.annotate(articulos=Count('detalles')).order_by('-fecha')[:8]
        ),
    }
    return render(request, 'principal/panel.html', contexto)


@login_required
def lista_productos(request):
    productos = Producto.objects.select_related('categoria')
    consulta = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '')
    if consulta:
        productos = productos.filter(
            Q(codigo__icontains=consulta) | Q(nombre__icontains=consulta)
        )
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    contexto = {
        'productos': productos,
        'categorias': Categoria.objects.all(),
        'consulta': consulta,
        'categoria_sel': categoria_id,
    }
    return render(request, 'principal/lista_productos.html', contexto)


@requiere_dueno
def crear_producto(request):
    formulario = ProductoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and formulario.is_valid():
        formulario.save()
        messages.success(request, f'Producto "{formulario.instance.nombre}" creado.')
        return redirect('lista_productos')
    return render(request, 'principal/formulario_producto.html', {
        'formulario': formulario,
        'titulo': 'Nuevo producto',
    })


@requiere_dueno
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    formulario = ProductoForm(
        request.POST or None, request.FILES or None, instance=producto,
    )
    if request.method == 'POST' and formulario.is_valid():
        formulario.save()
        messages.success(request, f'Producto "{producto.nombre}" actualizado.')
        return redirect('lista_productos')
    return render(request, 'principal/formulario_producto.html', {
        'formulario': formulario,
        'titulo': f'Editar: {producto.nombre}',
    })


@requiere_dueno
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f'Producto "{nombre}" eliminado.')
    return redirect('lista_productos')


@login_required
def kardex(request):
    consulta = request.GET.get('q', '').strip()
    productos = (
        Producto.objects
        .select_related('categoria')
        .annotate(
            entradas=Sum('movimientos__cantidad', filter=Q(movimientos__tipo='entrada')),
            salidas=Sum('movimientos__cantidad', filter=Q(movimientos__tipo='salida')),
        )
    )
    if consulta:
        productos = productos.filter(
            Q(codigo__icontains=consulta) | Q(nombre__icontains=consulta)
        )
    movimientos = (
        MovimientoKardex.objects
        .select_related('venta', 'producto', 'sucursal', 'usuario')[:30]
    )
    return render(request, 'principal/kardex.html', {
        'productos': productos,
        'movimientos': movimientos,
        'consulta': consulta,
    })


@login_required
def registrar_cruce(request):
    hay_sucursales = Sucursal.objects.exists()
    formulario = CruceForm(request.POST or None)
    if request.method == 'POST' and formulario.is_valid():
        datos = formulario.cleaned_data
        cantidad = datos['cantidad']
        try:
            with transaction.atomic():
                producto = (
                    Producto.objects.select_for_update()
                    .get(pk=datos['producto'].pk)
                )
                if producto.stock < cantidad:
                    raise ValueError(
                        f'Stock insuficiente de "{producto.nombre}" '
                        f'(disponible: {producto.stock}).'
                    )
                MovimientoKardex.objects.create(
                    producto=producto,
                    sucursal=datos['sucursal_origen'],
                    tipo='salida',
                    cantidad=cantidad,
                    referencia=f'Cruce hacia {datos["sucursal_destino"]}',
                    usuario=request.user,
                )
                MovimientoKardex.objects.create(
                    producto=producto,
                    sucursal=datos['sucursal_destino'],
                    tipo='entrada',
                    cantidad=cantidad,
                    referencia=f'Cruce desde {datos["sucursal_origen"]}',
                    usuario=request.user,
                )
        except ValueError as error:
            messages.error(request, str(error))
        else:
            messages.success(
                request,
                f'Cruce registrado: {cantidad} u. de "{producto.nombre}" '
                f'de {datos["sucursal_origen"]} a {datos["sucursal_destino"]}.',
            )
            return redirect('kardex')
    return render(request, 'principal/registrar_cruce.html', {
        'formulario': formulario,
        'hay_sucursales': hay_sucursales,
    })


@login_required
def nueva_venta(request):
    config = Configuracion.obtener()
    if request.method == 'POST':
        cliente = request.POST.get('cliente', '').strip() or 'Consumidor final'
        items = []
        for campo, valor in request.POST.items():
            if not campo.startswith('cant_'):
                continue
            try:
                cantidad = int(valor)
            except ValueError:
                continue
            producto_id = campo[5:]
            if producto_id.isdigit() and cantidad > 0:
                items.append((int(producto_id), cantidad))
        if not items:
            messages.error(request, 'Agrega al menos un producto a la venta.')
            return redirect('nueva_venta')
        try:
            venta = Venta.registrar(
                items, cliente, iva_porcentaje=config.iva_porcentaje,
                pago_efectivo=_a_decimal(request.POST.get('pago_efectivo')),
                pago_transferencia=_a_decimal(request.POST.get('pago_transferencia')),
                banco=request.POST.get('pago_banco', '').strip(),
                comprobante=request.POST.get('pago_comprobante', '').strip(),
                usuario=request.user,
            )
        except ValueError as error:
            messages.error(request, str(error))
            return redirect('nueva_venta')
        messages.success(request, f'Venta #{venta.id} registrada por ${venta.total}.')
        return redirect('detalle_venta', pk=venta.id)

    productos_json = [
        {
            'id': fila['id'],
            'codigo': fila['codigo'],
            'nombre': fila['nombre'],
            'precio_venta': float(fila['precio_venta']),
            'stock': fila['stock'],
            'imagen': f"{settings.MEDIA_URL}{fila['imagen']}" if fila['imagen'] else '',
        }
        for fila in Producto.objects.order_by('nombre').values(
            'id', 'codigo', 'nombre', 'precio_venta', 'stock', 'imagen'
        )
    ]
    contexto = {
        'productos_json': productos_json,
        'iva_porcentaje': config.iva_porcentaje,
    }
    return render(request, 'principal/nueva_venta.html', contexto)


@requiere_dueno
def configuracion(request):
    config = Configuracion.obtener()
    formulario = ConfiguracionForm(request.POST or None, instance=config)
    if request.method == 'POST' and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            f'Configuración guardada. IVA {formulario.instance.iva_porcentaje}%.',
        )
        return redirect('configuracion')
    ultimo = (
        Venta.objects.order_by('-id').values_list('id', flat=True).first() or 0
    )
    return render(request, 'principal/configuracion.html', {
        'formulario': formulario,
        'proximo_secuencial': config.secuencial(ultimo + 1),
    })


@login_required
def caja(request):
    sesion = Caja.sesion_actual()
    administra = es_dueno(request.user)

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'abrir':
            if sesion:
                messages.error(request, 'La caja ya está abierta.')
            else:
                monto = _a_decimal(request.POST.get('monto_apertura')) or Decimal('0')
                if monto < 0:
                    messages.error(request, 'El monto inicial no puede ser negativo.')
                else:
                    Caja.objects.create(monto_apertura=monto, usuario_abre=request.user)
                    messages.success(request, f'Caja abierta con ${monto}.')
            return redirect('caja')
        if accion == 'cerrar':
            if not sesion:
                messages.error(request, 'No hay una caja abierta.')
            elif not administra and sesion.usuario_abre != request.user:
                messages.error(
                    request,
                    'Solo puedes cerrar la caja que abriste tú.',
                )
            else:
                # Conteo de billetes/monedas del arqueo físico.
                valores = {clave: Decimal(str(valor)) for clave, valor in ConteoCaja.VALORES.items()}
                cantidades = {}
                total_conteo = Decimal('0')
                alguno_ingresado = False
                for campo, valor in valores.items():
                    cantidad = _a_decimal(request.POST.get(campo))
                    if cantidad is None:
                        cantidad = 0
                    elif cantidad < 0:
                        messages.error(request, 'Las cantidades del conteo no pueden ser negativas.')
                        return redirect('caja')
                    cantidad = int(cantidad)
                    cantidades[campo] = cantidad
                    total_conteo += cantidad * valor
                    if cantidad:
                        alguno_ingresado = True
                if not alguno_ingresado:
                    messages.error(request, 'Ingresa el conteo de billetes y monedas para cerrar la caja.')
                else:
                    esperado = sesion.resumen()['esperado']
                    sesion.fecha_cierre = timezone.now()
                    sesion.monto_esperado = esperado
                    sesion.monto_contado = total_conteo
                    sesion.save()
                    ConteoCaja.objects.create(caja=sesion, **cantidades)
                    diferencia = sesion.diferencia()
                    texto = 'Sin diferencias.'
                    if diferencia < 0:
                        texto = f'Faltan ${abs(diferencia)}.'
                    elif diferencia > 0:
                        texto = f'Sobran ${diferencia}.'
                    messages.success(request, f'Caja cerrada. {texto}')
                    return render_pdf_response(
                        request,
                        'principal/cierre_caja_pdf.html',
                        _ctx_cierre_caja(sesion),
                        f'cierre-caja-{sesion.id}.pdf',
                    )
            return redirect('caja')

    historial = Caja.objects.filter(fecha_cierre__isnull=False)
    if not administra:
        historial = historial.filter(usuario_abre=request.user)
    resumen = sesion.resumen() if sesion else None
    return render(request, 'principal/caja.html', {
        'sesion': sesion,
        'resumen': resumen,
        'historial': historial[:6],
        'administra_caja': administra,
    })


@login_required
def cierre_caja_pdf(request, pk):
    caja = get_object_or_404(Caja, pk=pk)
    if caja.fecha_cierre is None:
        messages.error(request, 'El cierre solo está disponible cuando la caja está cerrada.')
        return redirect('caja')
    if not es_dueno(request.user) and caja.usuario_abre != request.user:
        messages.error(request, 'Solo puedes ver el cierre de tus propias cajas.')
        return redirect('caja')
    return render_pdf_response(
        request,
        'principal/cierre_caja_pdf.html',
        _ctx_cierre_caja(caja),
        f'cierre-caja-{caja.id}.pdf',
    )


@login_required
def buscar_clientes(request):
    consulta = request.GET.get('q', '').strip()
    clientes = Cliente.objects.all()
    if consulta:
        clientes = clientes.filter(
            Q(nombre__icontains=consulta) | Q(documento__icontains=consulta)
        )
    datos = list(clientes.values('id', 'nombre', 'documento')[:8])
    return JsonResponse({'clientes': datos})


@requiere_dueno
def historial_ventas(request):
    ventas = Venta.objects.prefetch_related('detalles__producto').order_by('-fecha')
    return render(request, 'principal/historial_ventas.html', {'ventas': ventas})


@login_required
def detalle_venta(request, pk):
    venta = get_object_or_404(
        Venta.objects.prefetch_related('detalles__producto'), pk=pk,
    )
    return render(request, 'principal/detalle_venta.html', {'venta': venta})


@login_required
def factura_pdf(request, pk):
    venta = get_object_or_404(
        Venta.objects.prefetch_related('detalles__producto'), pk=pk,
    )
    config = Configuracion.obtener()
    secuencial = config.secuencial(venta.id)
    # El subtotal se calcula desde los detalles para que la factura siempre cuadre
    # (algunos registros antiguos no guardaron bien el subtotal).
    subtotal = sum(
        (d.precio_unitario * d.cantidad) for d in venta.detalles.all()
    )
    iva = venta.total - subtotal
    nombre = f'{secuencial}.pdf'
    return render_pdf_response(
        request,
        'principal/factura_pdf.html',
        {
            'venta': venta,
            'config': config,
            'secuencial': secuencial,
            'subtotal': subtotal,
            'iva': iva,
        },
        nombre,
    )
