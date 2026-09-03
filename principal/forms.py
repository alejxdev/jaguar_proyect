from django import forms
from .models import Configuracion, Producto, Sucursal


class CruceForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.none(), label='Producto',
    )
    sucursal_origen = forms.ModelChoiceField(
        queryset=Sucursal.objects.none(), label='Sucursal origen',
    )
    sucursal_destino = forms.ModelChoiceField(
        queryset=Sucursal.objects.none(), label='Sucursal destino',
    )
    cantidad = forms.IntegerField(min_value=1, initial=1, label='Cantidad')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.order_by('nombre')
        sucursales = Sucursal.objects.order_by('nombre')
        self.fields['sucursal_origen'].queryset = sucursales
        self.fields['sucursal_destino'].queryset = sucursales

    def clean(self):
        datos = super().clean()
        origen = datos.get('sucursal_origen')
        destino = datos.get('sucursal_destino')
        if origen and destino and origen == destino:
            raise forms.ValidationError(
                'La sucursal origen y la destino deben ser distintas.'
            )
        return datos


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo', 'nombre', 'categoria', 'imagen',
            'precio_compra', 'precio_venta', 'stock', 'stock_minimo',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'placeholder': 'Ej: PROD-001'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre del producto'}),
            'imagen': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }


class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = [
            'iva_porcentaje',
            'nombre_empresa', 'ruc', 'direccion', 'telefono', 'correo', 'lema',
            'establecimiento', 'punto_emision',
        ]
        labels = {
            'iva_porcentaje': 'IVA aplicado a las ventas (%)',
            'nombre_empresa': 'Razón social / nombre comercial',
            'ruc': 'RUC',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'correo': 'Correo electrónico',
            'lema': 'Lema / texto de la factura',
            'establecimiento': 'Establecimiento (3 dígitos)',
            'punto_emision': 'Punto de emisión (3 dígitos)',
        }
        help_texts = {
            'iva_porcentaje': (
                'Ecuador: tarifa general 15% (vigente desde abril de 2024). '
                'Usa 0% si todos tus productos son de primera necesidad '
                '(canasta básica). Puedes poner valores intermedios si vendes '
                'mezcla de productos gravados y no gravados.'
            ),
            'establecimiento': 'Código del establecimiento (ej. 001).',
            'punto_emision': 'Código del punto de emisión (ej. 001).',
        }
        widgets = {
            'iva_porcentaje': forms.NumberInput(
                attrs={'step': '0.01', 'min': 0, 'max': 100}
            ),
            'establecimiento': forms.TextInput(attrs={'maxlength': 3}),
            'punto_emision': forms.TextInput(attrs={'maxlength': 3}),
        }
