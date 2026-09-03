from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Caja, Configuracion, Producto, Venta

User = get_user_model()


class PdfTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username='dueno', password='test1234', is_superuser=True,
        )
        self.config = Configuracion.obtener()
        self.config.nombre_empresa = 'Mi Empresa SA'
        self.config.ruc = '1799999999001'
        self.config.establecimiento = '001'
        self.config.punto_emision = '001'
        self.config.save()
        self.producto = Producto.objects.create(
            codigo='P01', nombre='Producto de prueba', stock=50,
            precio_compra=5, precio_venta=10,
        )
        # 2 uds x $10 = $20 subtotal; con IVA 15% el total es $23
        self.venta = Venta.registrar(
            [(self.producto.pk, 2)], cliente='Cliente Test',
            iva_porcentaje=self.config.iva_porcentaje,
            pago_efectivo=23.0, usuario=self.usuario,
        )

    def test_factura_pdf(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(f'/ventas/{self.venta.pk}/factura.pdf')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))
        self.assertGreater(len(respuesta.content), 1000)
        esperado = self.config.secuencial(self.venta.pk)
        self.assertTrue(
            f'filename="{esperado}.pdf"' in respuesta['Content-Disposition'],
            respuesta['Content-Disposition'],
        )

    def test_cierre_caja_perfil_pdf(self):
        from django.utils import timezone

        caja = Caja.objects.create(monto_apertura=10, usuario_abre=self.usuario)
        esperado = caja.resumen()['esperado']
        caja.fecha_cierre = timezone.now()
        caja.monto_esperado = esperado
        caja.monto_contado = esperado
        caja.save()
        self.client.force_login(self.usuario)
        respuesta = self.client.get(f'/caja/{caja.pk}/cierre.pdf')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))
        self.assertGreater(len(respuesta.content), 1000)

    def test_cerrar_caja_devuelve_pdf(self):
        caja = Caja.objects.create(monto_apertura=10, usuario_abre=self.usuario)
        self.client.force_login(self.usuario)
        respuesta = self.client.post('/caja/', {
            'accion': 'cerrar',
            # Conteo: 1 billete de $10
            'b_10': '1',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))

    def test_conteo_calcula_total_y_guarda(self):
        caja = Caja.objects.create(monto_apertura=0, usuario_abre=self.usuario)
        self.client.force_login(self.usuario)
        respuesta = self.client.post('/caja/', {
            'accion': 'cerrar',
            'b_100': '1', 'b_50': '1', 'b_20': '1',
            'm_050': '1', 'm_025': '1', 'm_010': '1',
        })
        # Esperado: 100+50+20+0.50+0.25+0.10 = 170.85
        self.assertEqual(respuesta.status_code, 200)
        caja.refresh_from_db()
        self.assertEqual(caja.monto_contado, Decimal('170.85'))
        self.assertTrue(hasattr(caja, 'conteo'))
        self.assertEqual(caja.conteo.b_100, 1)
        self.assertEqual(caja.conteo.renglones()[0][3], Decimal('100'))

    def test_cerrar_caja_sin_conteo_rechaza(self):
        caja = Caja.objects.create(monto_apertura=0, usuario_abre=self.usuario)
        self.client.force_login(self.usuario)
        respuesta = self.client.post('/caja/', {'accion': 'cerrar'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Caja.sesion_actual() is not None)

    def test_ventas_no_lista_sin_login(self):
        respuesta = self.client.get(f'/ventas/{self.venta.pk}/factura.pdf')
        self.assertEqual(respuesta.status_code, 302)
