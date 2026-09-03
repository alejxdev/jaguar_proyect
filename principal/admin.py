from django.contrib import admin
from .models import (
    Caja, Categoria, Cliente, Configuracion, ConteoCaja, DetalleVenta,
    MovimientoKardex, Producto, Sucursal, Venta,
)


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'documento', 'telefono']
    search_fields = ['nombre', 'documento']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'categoria', 'precio_venta', 'stock', 'bajo_stock']
    list_filter = ['categoria']
    search_fields = ['codigo', 'nombre']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'cliente', 'fecha', 'total', 'metodo_pago',
        'monto_efectivo', 'monto_transferencia', 'banco', 'comprobante',
    ]
    inlines = [DetalleVentaInline]


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ['venta', 'producto', 'cantidad', 'precio_unitario']


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ['id', 'iva_porcentaje']


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'fecha_apertura', 'fecha_cierre',
        'monto_apertura', 'monto_esperado', 'monto_contado',
    ]


@admin.register(ConteoCaja)
class ConteoCajaAdmin(admin.ModelAdmin):
    list_display = ['id', 'caja', 'total']


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre']
    search_fields = ['nombre']


@admin.register(MovimientoKardex)
class MovimientoKardexAdmin(admin.ModelAdmin):
    list_display = [
        'fecha', 'tipo', 'producto', 'sucursal',
        'cantidad', 'referencia', 'usuario',
    ]
    list_filter = ['tipo', 'sucursal']
    search_fields = ['producto__nombre', 'producto__codigo', 'referencia']
