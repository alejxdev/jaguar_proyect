from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel, name='panel'),
    path('login/', auth_views.LoginView.as_view(template_name='principal/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('productos/', views.lista_productos, name='lista_productos'),
    path('kardex/', views.kardex, name='kardex'),
    path('productos/nuevo/', views.crear_producto, name='crear_producto'),
    path('productos/cruces/', views.registrar_cruce, name='registrar_cruce'),
    path('productos/<int:pk>/editar/', views.editar_producto, name='editar_producto'),
    path('productos/<int:pk>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('ventas/', views.historial_ventas, name='historial_ventas'),
    path('ventas/nueva/', views.nueva_venta, name='nueva_venta'),
    path('ventas/<int:pk>/', views.detalle_venta, name='detalle_venta'),
    path('ventas/<int:pk>/factura.pdf', views.factura_pdf, name='factura_pdf'),
    path('api/clientes/', views.buscar_clientes, name='buscar_clientes'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('caja/', views.caja, name='caja'),
    path('caja/<int:pk>/cierre.pdf', views.cierre_caja_pdf, name='cierre_caja_pdf'),
]
