import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'miweb.settings')
django.setup()

from principal.models import Categoria, Cliente, DetalleVenta, Producto, Venta

DetalleVenta.objects.all().delete()
Venta.objects.all().delete()
Producto.objects.all().delete()
Categoria.objects.all().delete()

for nombre, documento in [
    ('Ana Torres', '10203040'),
    ('Carlos Mendoza', '55667788'),
    ('Lucía Fernández', '90807060'),
]:
    Cliente.objects.get_or_create(nombre=nombre, defaults={'documento': documento})

bebidas = Categoria.objects.create(nombre='Bebidas')
snacks = Categoria.objects.create(nombre='Snacks')
aseo = Categoria.objects.create(nombre='Aseo')
granos = Categoria.objects.create(nombre='Granos y abarrotes')

# Precios de referencia del mercado ecuatoriano (Tia Ecuador, ago 2026):
# agua 625ml $0.35 | gaseosa 1.35L $1.55 | jabon tocador 110g $0.32
# arroz Real 5kg $8.95 (~$1.79/kg) | azucar San Carlos 1kg $0.99
datos = [
    # codigo, nombre, categoria, compra, venta, stock, minimo
    ('BEB-001', 'Agua embotellada 600ml', bebidas, 0.28, 0.40, 120, 20),
    ('BEB-002', 'Gaseosa 1.5L', bebidas, 1.20, 1.60, 45, 10),
    ('SNK-001', 'Papas fritas 150g', snacks, 0.90, 1.25, 30, 8),
    ('SNK-002', 'Chocolate con leche', snacks, 0.95, 1.30, 6, 10),
    ('ASE-001', 'Jabon de barra', aseo, 0.32, 0.45, 50, 12),
    ('GRA-001', 'Arroz 1kg', granos, 1.50, 1.85, 80, 15),
    ('GRA-002', 'Azucar 1kg', granos, 0.85, 1.10, 4, 10),
]

for codigo, nombre, cat, compra, venta, stock, minimo in datos:
    Producto.objects.create(
        codigo=codigo,
        nombre=nombre,
        categoria=cat,
        precio_compra=compra,
        precio_venta=venta,
        stock=stock,
        stock_minimo=minimo,
    )

print(f'Listo: {Categoria.objects.count()} categorias, {Producto.objects.count()} productos.')
