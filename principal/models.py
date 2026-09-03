from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db import transaction
from django.db.models import Count, Sum


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    documento = models.CharField(max_length=30, blank=True, default='')
    telefono = models.CharField(max_length=30, blank=True, default='')

    def __str__(self):
        return f'{self.nombre} ({self.documento})' if self.documento else self.nombre

    class Meta:
        ordering = ['nombre']


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='productos',
    )
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    imagen = models.ImageField(upload_to='productos/', blank=True)
    stock = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'

    @property
    def bajo_stock(self):
        return self.stock <= self.stock_minimo

    @property
    def valor_inventario(self):
        return self.precio_compra * self.stock

    class Meta:
        ordering = ['nombre']


class Venta(models.Model):
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('mixto', 'Mixto'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.CharField(max_length=150, blank=True, default='Consumidor final')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    metodo_pago = models.CharField(
        max_length=15, choices=METODOS_PAGO, default='efectivo',
    )
    monto_efectivo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_transferencia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    banco = models.CharField(max_length=100, blank=True, default='')
    comprobante = models.CharField(max_length=50, blank=True, default='')

    def __str__(self):
        return f'Venta #{self.id}'

    @classmethod
    def registrar(
        cls, items, cliente='', iva_porcentaje=0,
        pago_efectivo=None, pago_transferencia=None, banco='', comprobante='',
        usuario=None,
    ):
        """
        Registra una venta completa: crea la venta, sus detalles,
        descuenta el stock, calcula el total con IVA y valida el pago.
        items: lista de tuplas (producto_id, cantidad).
        pago_efectivo/pago_transferencia: montos; los vacíos se completan
        automáticamente con el resto. Lanza ValueError si no hay stock
        suficiente o el pago no cuadra con el total.
        """
        from decimal import ROUND_HALF_UP, Decimal

        centavo = Decimal('0.01')

        def moneda(valor):
            return Decimal(str(valor)).quantize(centavo, rounding=ROUND_HALF_UP)

        tasa = Decimal(str(iva_porcentaje or 0))
        with transaction.atomic():
            venta = cls.objects.create(
                cliente=cliente or 'Consumidor final',
                iva_porcentaje=tasa,
            )
            subtotal = Decimal('0')
            for producto_id, cantidad in items:
                if cantidad <= 0:
                    continue
                producto = Producto.objects.select_for_update().get(pk=producto_id)
                if producto.stock < cantidad:
                    raise ValueError(
                        f'Stock insuficiente de "{producto.nombre}" '
                        f'(disponible: {producto.stock}).'
                    )
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio_venta,
                )
                producto.stock -= cantidad
                producto.save(update_fields=['stock'])
                subtotal += producto.precio_venta * cantidad
                MovimientoKardex.objects.create(
                    producto=producto,
                    tipo='salida',
                    cantidad=cantidad,
                    referencia=f'Venta #{venta.id}',
                    venta=venta,
                    usuario=usuario,
                )
            venta.subtotal = subtotal
            venta.iva = (
                (subtotal * tasa / Decimal('100'))
                .quantize(centavo, rounding=ROUND_HALF_UP)
            )
            venta.total = subtotal + venta.iva

            efectivo = moneda(pago_efectivo) if pago_efectivo is not None else None
            transferencia = (
                moneda(pago_transferencia) if pago_transferencia is not None else None
            )
            if efectivo is None and transferencia is None:
                efectivo, transferencia = venta.total, Decimal('0')
            elif efectivo is None:
                efectivo = venta.total - transferencia
            elif transferencia is None:
                transferencia = venta.total - efectivo

            if efectivo < 0 or transferencia < 0:
                raise ValueError('Ningún monto de pago puede ser negativo.')
            if efectivo + transferencia != venta.total:
                raise ValueError(
                    f'El pago no cuadra: entregado ${efectivo + transferencia} '
                    f'vs total ${venta.total}.'
                )
            if transferencia > 0 and (not banco or not comprobante):
                raise ValueError(
                    'Indica el banco y el número de comprobante '
                    'de la transferencia.'
                )

            venta.metodo_pago = (
                'mixto'
                if efectivo > 0 and transferencia > 0
                else 'transferencia' if transferencia > 0 else 'efectivo'
            )
            venta.monto_efectivo = efectivo
            venta.monto_transferencia = transferencia
            venta.banco = banco
            venta.comprobante = comprobante
            venta.save(update_fields=[
                'subtotal', 'iva', 'total', 'metodo_pago',
                'monto_efectivo', 'monto_transferencia', 'banco', 'comprobante',
            ])
        return venta


class Configuracion(models.Model):
    iva_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=15,
        help_text='Tarifa general en Ecuador: 15% (productos de primera necesidad: 0%).',
    )

    # Datos del emisor (para la representación impresa de la factura)
    nombre_empresa = models.CharField(
        max_length=150, blank=True, default='JAGUAR',
        help_text='Razón social o nombre comercial que aparece en la factura.',
    )
    ruc = models.CharField(
        max_length=13, blank=True, default='',
        help_text='Número de RUC del emisor (13 dígitos).',
    )
    direccion = models.CharField(
        max_length=250, blank=True, default='',
        help_text='Dirección de la matriz o del establecimiento.',
    )
    telefono = models.CharField(
        max_length=30, blank=True, default='',
        help_text='Teléfono de contacto.',
    )
    correo = models.EmailField(
        blank=True, default='',
        help_text='Correo electrónico de contacto.',
    )
    lema = models.CharField(
        max_length=200, blank=True, default='',
        help_text='Lema o texto libre que se imprime bajo el nombre (opcional).',
    )

    # Numeración de comprobantes: establecimiento(3) - punto(3) - secuencial(9)
    establecimiento = models.CharField(
        max_length=3, blank=True, default='001',
        help_text='Código del establecimiento (3 dígitos, ej. 001).',
    )
    punto_emision = models.CharField(
        max_length=3, blank=True, default='001',
        help_text='Código del punto de emisión (3 dígitos, ej. 001).',
    )

    class Meta:
        verbose_name_plural = 'configuracion'

    @classmethod
    def obtener(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def secuencial(self, numero):
        return f'{self.establecimiento or "001"}-{self.punto_emision or "001"}-{int(numero):09d}'

    def __str__(self):
        return f'IVA: {self.iva_porcentaje}%'


class Caja(models.Model):
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    monto_apertura = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_esperado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    monto_contado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usuario_abre = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cajas_abiertas',
    )

    class Meta:
        ordering = ['-fecha_apertura']

    def __str__(self):
        estado = 'abierta' if self.fecha_cierre is None else 'cerrada'
        return f'Caja #{self.id} ({estado})'

    @classmethod
    def sesion_actual(cls):
        return cls.objects.filter(fecha_cierre__isnull=True).first()

    def ventas(self):
        qs = Venta.objects.filter(fecha__gte=self.fecha_apertura)
        if self.fecha_cierre:
            qs = qs.filter(fecha__lte=self.fecha_cierre)
        return qs

    def resumen(self):
        datos = self.ventas().aggregate(
            numero=Count('id'),
            efectivo=Sum('monto_efectivo'),
            transferencia=Sum('monto_transferencia'),
            total=Sum('total'),
        )
        datos['efectivo'] = datos['efectivo'] or Decimal('0')
        datos['transferencia'] = datos['transferencia'] or Decimal('0')
        datos['total'] = datos['total'] or Decimal('0')
        datos['esperado'] = self.monto_apertura + datos['efectivo']
        return datos

    def diferencia(self):
        if self.monto_contado is None or self.monto_esperado is None:
            return None
        return self.monto_contado - self.monto_esperado


class ConteoCaja(models.Model):
    """Arqueo del cierre: cantidad de cada billete/moneda en la caja física."""
    BILLETES = [
        ('b_100', 'Billetes de $100', Decimal('100')),
        ('b_50', 'Billetes de $50', Decimal('50')),
        ('b_20', 'Billetes de $20', Decimal('20')),
        ('b_10', 'Billetes de $10', Decimal('10')),
        ('b_5', 'Billetes de $5', Decimal('5')),
        ('b_1', 'Billetes de $1', Decimal('1')),
        ('m_1', 'Monedas de $1', Decimal('1')),
        ('m_050', 'Monedas de $0.50', Decimal('0.50')),
        ('m_025', 'Monedas de $0.25', Decimal('0.25')),
        ('m_010', 'Monedas de $0.10', Decimal('0.10')),
        ('m_005', 'Monedas de $0.05', Decimal('0.05')),
        ('m_001', 'Monedas de $0.01', Decimal('0.01')),
    ]
    # Los valores por denominación se guardan como constantes (cada caja es 1 a 1
    # con su cierre, no dependen del tiempo).
    VALORES = {
        'b_100': Decimal('100'), 'b_50': Decimal('50'), 'b_20': Decimal('20'),
        'b_10': Decimal('10'), 'b_5': Decimal('5'), 'b_1': Decimal('1'),
        'm_1': Decimal('1'), 'm_050': Decimal('0.50'), 'm_025': Decimal('0.25'),
        'm_010': Decimal('0.10'), 'm_005': Decimal('0.05'), 'm_001': Decimal('0.01'),
    }

    caja = models.OneToOneField(Caja, on_delete=models.CASCADE, related_name='conteo')

    b_100 = models.PositiveIntegerField(default=0)
    b_50 = models.PositiveIntegerField(default=0)
    b_20 = models.PositiveIntegerField(default=0)
    b_10 = models.PositiveIntegerField(default=0)
    b_5 = models.PositiveIntegerField(default=0)
    b_1 = models.PositiveIntegerField(default=0)
    m_1 = models.PositiveIntegerField(default=0)
    m_050 = models.PositiveIntegerField(default=0)
    m_025 = models.PositiveIntegerField(default=0)
    m_010 = models.PositiveIntegerField(default=0)
    m_005 = models.PositiveIntegerField(default=0)
    m_001 = models.PositiveIntegerField(default=0)

    def total(self):
        return sum(
            getattr(self, clave, 0) * valor
            for clave, valor in self.VALORES.items()
        )

    def renglones(self):
        """Lista [(etiqueta, valor, cantidad, subtotal)] solo con cantidades > 0."""
        etiquetas = {campo: etiqueta for campo, etiqueta, _ in self.BILLETES}
        renglones = []
        for clave, valor in self.VALORES.items():
            cantidad = getattr(self, clave, 0)
            if cantidad:
                renglones.append((etiquetas[clave], valor, cantidad, cantidad * valor))
        return renglones

    def __str__(self):
        return f'Conteo de caja #{self.caja_id}: ${self.total():.2f}'


class Sucursal(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class MovimientoKardex(models.Model):
    TIPOS = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name='movimientos',
    )
    sucursal = models.ForeignKey(
        Sucursal, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos',
    )
    tipo = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.PositiveIntegerField()
    referencia = models.CharField(max_length=150, blank=True, default='')
    venta = models.ForeignKey(
        Venta, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_kardex',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_kardex',
    )

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.get_tipo_display()} {self.cantidad} x {self.producto.nombre}'


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles')
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre}'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad
