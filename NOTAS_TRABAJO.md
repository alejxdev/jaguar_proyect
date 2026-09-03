# Registro de trabajo — Jaguar POS

Última actualización: jueves 27/08/2026. Pedirme "lee NOTAS_TRABAJO.md" al empezar una sesión para recuperar el contexto.

## HECHO EL 27/08/2026 (3ª tanda)

### 8. Conteo de billetes/monedas al cerrar caja (arqueo)
- Nueva tabla **`ConteoCaja`** (migración **0010**) 1 a 1 con `Caja`: guarda la CANTIDAD de cada billete ($100, 50, 20, 10, 5, 1) y moneda ($1, 0.50, 0.25, 0.10, 0.05, 0.01).
  - `total()` suma cantidad×valor; `renglones()` lista las denominaciones con cantidad>0 (para el PDF). `VALORES` = const de cada denominación.
- El **cierre de caja ahora se hace SOLO por conteo** (decisión del usuario): ya NO se pide "monto contado" a mano. El sistema suma el arqueo y ese es `monto_contado`.
- Form de cierre en `caja.html`: cuadrícula de billetes y monedas (campo de cantidad por denominación) + total y diferencia calculados en vivo por JS. Estilos `.conteo-fila`/`.campo-grupo-conteo` en `estilos.css`.
- Vista `caja` (accion=cerrar): lee cantidades, rechaza negativos, si todas en 0 muestra error; guarda `ConteoCaja` y calcula `monto_contado`.
- PDF `cierre_caja_pdf.html`: nueva sección "Conteo de billetes y monedas" con el desglose. Usa la variable `conteo` (puede ser None en cajas antiguas → se omite la sección). `_ctx_cierre_caja` prepara `conteo` con try/except.
- Registrado en Admin (`ConteoCajaAdmin`, método `total`).
- **Bug corregido**: los campos de denominación ausentes en el POST devolvían None y se trataban como "negativo" → se interpretan como 0.
- **Bug corregido**: `dict(self.BILLETES)` fallaba por tuplas de 3 → ahora comprensión `{campo: etiqueta}`.
- Tests: 3 nuevos (cierre por conteo guarda y cuadra total, rechaza sin conteo, PDF con conteo). Total 6 tests OK.

### 9. Cajeros ahora pueden hacer cruces entre sucursales y ver Kardex
- ANTES: `registrar_cruce` y `kardex` eran `@requiere_dueno` y en el navbar solo se veían para dueños.
- AHORA: `registrar_cruce` y `kardex` pasan a `@login_required` (cualquier cajero autenticado). En `base.html` "Cruces / Traslados" y "Kardex" ya visibles para todos.
- Motivo: pedido del usuario; además el flujo del cruce redirige a `kardex`, así que el cajero debe poder verlo (solo lectura, no hay escritura en esa vista). El cruce NO altera stock global (solo mueve entre sucursales).

## HECHO EL 27/08/2026

### 4. Facturas y cierre de caja en PDF (WeasyPrint)
- Nueva dependencia **WeasyPrint 69.0** (añadida a `requirements.txt`) para generar PDF desde plantillas HTML/CSS.
- **IMPORTANTE (Windows):** WeasyPrint necesita las librerías GTK/Pango. Instalé **MSYS2** (`C:\msys64`) y el paquete `mingw-w64-ucrt-x86_64-pango`. Las DLL están en `C:\msys64\ucrt64\bin`.
  - Variable de entorno `WEASYPRINT_DLL_DIRECTORIES` fijada a nivel de usuario con `setx`.
  - `settings.py` además hace `os.add_dll_directory(C:\msys64\ucrt64\bin)` en Windows si existe (robustez).
  - En el futuro VPS LINUX se instala con `apt install` (aquí no aplica).
- Utilidad `principal/pdf.py`: `render_pdf_response(request, plantilla, contexto, nombre_archivo)` -> devuelve el PDF como descarga.
- Plantillas nuevas: `principal/factura_pdf.html` y `principal/cierre_caja_pdf.html` (con logo y estilos propios incrustados; NO heredan de base.html).
- **Factura**: botón "Factura PDF" en `detalle_venta.html`. Vista `factura_pdf` (login), URL `ventas/<pk>/factura.pdf`.
- **Cierre de caja**: al cerrar la caja se genera y descarga el PDF automáticamente (la vista `caja` ahora devuelve el PDF en lugar de redirigir). Vista `cierre_caja_pdf` (login; solo propia/dueño), URL `caja/<pk>/cierre.pdf`. Botón "PDF" en el historial de cajas cerradas de `caja.html`.
- Verificado con cliente de pruebas: factura PDF y cierre PDF devuelven 200 + `%PDF-` con el logo incrustado.

### 5. Factura personalizable al estilo Ecuador (datos del emisor + RUC)
- **Migración 0009**: el modelo `Configuracion` ahora guarda los datos del emisor que se imprimen en la factura:
  - `nombre_empresa` (razón social / nombre comercial), `ruc`, `direccion`, `telefono`, `correo`, `lema` (texto opcional bajo el nombre).
  - `establecimiento` y `punto_emision` (3 dígitos c/u) para la numeración.
  - Método `Configuracion.secuencial(num)` -> devuelve `establecimiento-punto-secuencial(9)` (ej. `001-001-000000001`).
- **IMPORTANTE / PENDIENTE DEL USUARIO**: estos campos están vacíos por defecto (solo `nombre_empresa='JAGUAR'`). Hay que llenar RUC, dirección, teléfono, correo en **Configuración** para que salgan en la factura.
- `ConfiguracionForm` ampliado con todos los campos. Plantilla `configuracion.html` reorganizada en secciones (Impuestos / Datos del emisor / Numeración) + vista previa del próximo secuencial.
- `factura_pdf.html` rediseñada como factura ecuatoriana: razón social, lema, dirección, teléfono/correo, caja R.U.C. grande, FACTURA, número `001-001-000xxx`, fecha, cliente, tabla (código/descripción/cant/precio/subtotal), totales, firmas y nota de representación.
- El **subtotal de la factura se calcula desde los detalles** (no del campo guardado) para que SIEMPRE cuadre con el total. Motivo: la venta 39 (y quizá otras antiguas) tiene `subtotal=0` pero `total` correcto (dato histórico corrupto). El total mostrado es el oficial guardado (`venta.total`); `iva = total - subtotal`.
- El nombre del archivo descargado ahora es el número secuencial: `001-001-000000039.pdf` (antes `factura-39.pdf`).
- Nota legal/alcance: el PDF actual es la **representación impresa** de la operación, NO un comprobante electrónico SRI válido (requeriría XML firmado con certificado P12 + transmisión/autorización al SRI). Queda documentado en la propia factura y es un desarrollo aparte si se requiere cumplimiento tributario electrónico.
- Tests actualizados: verifican que el nombre del archivo usa la numeración. 4 tests OK.

### 6. Rediseño visual de los PDF (estilo clásico corporativo)
- `factura_pdf.html` y `cierre_caja_pdf.html` rediseñadas con estilo sobrio y profesional: barra teal superior, encabezado emisor izq + título doc derecha, caja R.U.C., tarjetas de datos (cliente/fecha/pago), tabla con encabezado teal + filas alternas, totales a la derecha con TOTAL A PAGAR resaltado (verde teal), firmas y pie legal.
- Mismo lenguaje visual en ambos documentos (marca `#0f766e`). Cierre de caja muestra tarjetas de CUADRE (apertura/esperado/contado/diferencia con colores ok/falta) + RESUMEN de ventas, y ahora usa `config` (empresa/RUC/dirección) — se añadió `config` a `_ctx_cierre_caja`.
- Validado por coordenadas (PyMuPDF temporal, luego desinstalado): estructura, alineación y montos correctos. 4 tests OK, `manage.py check` OK.

## Proyecto
- Django 6.1 + SQLite3, app única `principal`. Venv en `.venv` (usar `.venv\Scripts\python.exe`).
- Ejecutar: `python manage.py runserver`. Test client requiere `Client(SERVER_NAME='localhost')`.
- Cache-busting en `base.html` y `login.html`: CSS `?v=16`, JS `?v=2`. Subir versión SIEMPRE que se toque un archivo estático.

## HECHO EL 27/08/2026 (2ª tanda)
### 7. "Recuerda mis datos" en el login
- Checkbox en `login.html` que guarda usuario y contraseña en `localStorage` del navegador (clave `jaguar_credenciales`) y los rellena automáticamente al volver a la página de login. Se desmarca → borra lo guardado.
- Solo del lado del navegador (no se persiste en servidor ni BD). Estilos `.checkbox-recuerda` en `estilos.css`. CSS subido a `?v=15`.

## HECHO EL 22/08/2026

### 1. Dropdown "Productos" + Cruce de mercancía (Kardex real)
- Navbar: botón Productos desplegable con 'Catálogo de productos' y 'Cruces / Traslados'.
- Abre con clic (scripts.js) Y con hover (CSS). Puente invisible `::before` para que no se cierre al cruzar el hueco.
- Modelos nuevos (migration **0008**): `Sucursal` y `MovimientoKardex` (entrada/salida, sucursal, venta, usuario).
- Vista `/productos/cruces/`: transacción atómica, SALIDA en origen + ENTRADA en destino; valida stock insuficiente y origen != destino; stock global NO cambia.
- Las ventas ahora generan movimientos SALIDA en kardex (`Venta.registrar(usuario=...)`).
- Kardex (`/kardex/`) muestra entradas/salidas por producto + últimos 30 movimientos con tipo/sucursal.
- Crear sucursales desde Admin → Sucursales (el formulario avisa si no hay).

### 2. Sistema de roles y permisos (grupos nativos)
- `principal/permisos.py`: `es_dueno()` (superuser O grupo Dueno), `es_cajero()`, decorador `@requiere_dueno`.
- Vistas protegidas con `@requiere_dueno`: crear/editar/eliminar producto, kardex, cruces, configuración, historial. Intruso → mensaje y redirect al panel.
- Context processor `principal.context_processors.roles` → variables `es_dueno`/`es_cajero` en plantillas.
- Navbar por rol: Cajero = Panel/Nueva venta/Productos(sin cruces)/Caja. Dueño = todo menos Admin. Admin link solo superuser.
- Catálogo solo lectura para cajero (sin botones ni POST de eliminar).
- Caja: cajero solo cierra la caja que él abrió; historial filtrado a sus sesiones.
- Comandos: `inicializar_roles` (crea grupos Dueno=36 perms, Cajero=12) e `usuario_rol <usuario> <dueno|cajero|ninguno>`.
- Usuarios creados: `dueno.fuyd` y `cajero.fuyd`, clave `jaguar123`.
- Verificado con matriz completa de 11 pruebas (todas OK). SuperAdmin = `createsuperuser` normal.

### 3. Arreglos varios del día
- Menú no abría: `scripts.js` sin versión en su URL → navegador usaba copia vieja. Ahora `?v=2`.
- Opciones se cerraban al mover el mouse: hueco de 6px entre botón y menú → resuelto con `.menu-contenido::before`.

## PENDIENTE / DECISIÓN DEL USUARIO
- **Respaldo pendiente de aprobar**: existe `E:\01 DESAROLLO SOFTWARE\respaldo_miweb_20260822` (estado previo a roles+cruces).
  - Si el usuario aprueba → BORRAR esa carpeta.
  - Si dice "regresemos" → restaurar copiando su contenido sobre `miweb\`.
- El grupo 'Cajero' fue borrado una vez desde Admin (ya recreado). No borrar grupos; si pasa, correr `inicializar_roles`.
- Posible mejora ofrecida: sección "Usuarios" dentro de la web para que el dueño cree cajeros sin entrar al Admin (aún sin decidir).

## Lecciones/incidentes
- Una vez `settings.py` quedó sobrescrito por error al escribir otro archivo; se restauró desde el respaldo. Verificar siempre el `filePath` antes de escribir.
