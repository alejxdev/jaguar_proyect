// ===== Punto de venta: búsqueda, carrito, stock y totales =====

const TASA_IVA = (() => {
    const nodo = document.getElementById('datos-config');
    if (!nodo) return 0;
    try {
        return Number(JSON.parse(nodo.textContent).iva) || 0;
    } catch {
        return 0;
    }
})();

const productos = JSON.parse(
    document.getElementById('datos-productos').textContent
);
const porId = new Map(productos.map(p => [String(p.id), p]));
const carrito = new Map(); // id -> cantidad

let seleccionado = null;

const $ = id => document.getElementById(id);
const moneda = n => `$${Number(n).toFixed(2)}`;

/* ---------- avisos temporales ---------- */
function aviso(mensaje) {
    let zona = $('aviso-pos');
    if (!zona) {
        zona = document.createElement('div');
        zona.id = 'aviso-pos';
        zona.className = 'alerta error';
        document.querySelector('.pos-layout').prepend(zona);
    }
    zona.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${mensaje}`;
    clearTimeout(zona._t);
    zona._t = setTimeout(() => zona.remove(), 2800);
}

/* ---------- imágenes (placeholder o URL dinámica) ---------- */
function imagenProducto(p, clase) {
    return p.imagen
        ? `<img src="${p.imagen}" alt="${p.nombre}" class="${clase}">`
        : `<span class="${clase}"><i class="bi bi-box"></i></span>`;
}

/* ---------- buscador de productos ---------- */
const entradaProducto = $('buscar-producto');
const sugerencias = $('sugerencias');

function filtrarProductos(texto) {
    const q = texto.trim().toLowerCase();
    if (!q) return [];
    return productos.filter(p =>
        p.codigo.toLowerCase().includes(q) || p.nombre.toLowerCase().includes(q)
    ).slice(0, 6);
}

entradaProducto.addEventListener('input', () => {
    const coincidencias = filtrarProductos(entradaProducto.value);
    sugerencias.innerHTML = '';
    if (!coincidencias.length) {
        sugerencias.hidden = true;
        return;
    }
    for (const p of coincidencias) {
        const li = document.createElement('li');
        li.innerHTML = `
            ${imagenProducto(p, 'mini-img')}
            <span class="sug-nombre">${p.codigo} — ${p.nombre}</span>
            <span class="sug-precio">${moneda(p.precio_venta)}</span>`;
        li.addEventListener('click', () => {
            const id = String(p.id);
            seleccionarProducto(id);                       // muestra la vista previa
            agregarAlCarrito(id, 1);                       // y lo agrega a la orden
            entradaProducto.value = '';
            sugerencias.hidden = true;
        });
        sugerencias.appendChild(li);
    }
    sugerencias.hidden = false;
});

/* Enter con código exacto → agrega directo */
entradaProducto.addEventListener('keydown', evento => {
    if (evento.key !== 'Enter') return;
    evento.preventDefault();
    const q = entradaProducto.value.trim().toLowerCase();
    const exacto = productos.find(p => p.codigo.toLowerCase() === q);
    if (exacto) {
        agregarAlCarrito(String(exacto.id), 1);
        entradaProducto.value = '';
        sugerencias.hidden = true;
    } else {
        aviso('No hay un producto con ese código exacto.');
    }
});

document.addEventListener('click', evento => {
    if (!evento.target.closest('.columna-busqueda')) sugerencias.hidden = true;
    if (!evento.target.closest('.selector-cliente') && !evento.target.closest('#resultados-cliente')) {
        resultadosCliente.hidden = true;
    }
});

/* ---------- vista previa ---------- */
function stockDisponible(id) {
    const p = porId.get(id);
    return p.stock - (carrito.get(id) || 0);
}

/* ---------- pago (efectivo / transferencia / mixto) ---------- */
const pagoEfectivo = $('pago-efectivo');
const pagoTransf = $('pago-transferencia');
const datosTransf = $('datos-transferencia');
const estadoPago = $('estado-pago');
let totalActual = 0;
let editadoEfectivo = false;
let editadoTransferencia = false;

const redondear2 = n => Math.round((Number(n) || 0) * 100) / 100;

function validarPago() {
    const efectivo = redondear2(pagoEfectivo.value);
    const transferido = redondear2(pagoTransf.value);
    const entregado = redondear2(efectivo + transferido);
    const diferencia = redondear2(totalActual - entregado);

    datosTransf.hidden = !(transferido > 0);

    estadoPago.className = 'badge-neutro';
    const faltanDatos = transferido > 0
        && (!$('pago-banco').value.trim() || !$('pago-comprobante').value.trim());
    if (!carrito.size) {
        estadoPago.textContent = 'Sin cobrar';
    } else if (faltanDatos) {
        estadoPago.textContent = 'Falta banco / comprobante';
        estadoPago.classList.add('descuadre');
    } else if (Math.abs(diferencia) < 0.01) {
        estadoPago.textContent = 'Pago cuadrado';
        estadoPago.classList.add('pagado');
    } else if (diferencia > 0) {
        estadoPago.textContent = `Falta ${moneda(diferencia)}`;
        estadoPago.classList.add('descuadre');
    } else {
        estadoPago.textContent = `Sobra ${moneda(-diferencia)}`;
        estadoPago.classList.add('descuadre');
    }

    $('confirmar').disabled = !carrito.size
        || Math.abs(diferencia) >= 0.01
        || faltanDatos;
}

function iniciarPago(totalVenta) {
    totalActual = totalVenta;
    if (!editadoEfectivo && !editadoTransferencia) {
        pagoEfectivo.value = totalVenta ? totalVenta.toFixed(2) : '';
        pagoTransf.value = '';
    }
    validarPago();
}

pagoEfectivo.addEventListener('input', () => {
    editadoEfectivo = true;
    if (!editadoTransferencia) {
        const restante = redondear2(totalActual - redondear2(pagoEfectivo.value));
        pagoTransf.value = restante > 0 ? restante.toFixed(2) : '';
    }
    validarPago();
});

pagoTransf.addEventListener('input', () => {
    editadoTransferencia = true;
    if (!editadoEfectivo) {
        const restante = redondear2(totalActual - redondear2(pagoTransf.value));
        pagoEfectivo.value = restante > 0 ? restante.toFixed(2) : '';
    }
    validarPago();
});

['pago-banco', 'pago-comprobante'].forEach(id => {
    $(id).addEventListener('input', validarPago);
});

function actualizarStockPreview() {
    if (!seleccionado) return;
    const disponible = stockDisponible(String(seleccionado.id));
    const badge = $('pv-stock');
    badge.textContent = disponible > 0 ? `Disponible: ${disponible} u.` : 'Agotado';
    badge.className = disponible === 0 ? 'badge-rojo' : 'badge-neutro';
}

function seleccionarProducto(id) {
    seleccionado = porId.get(id);
    $('pv-imagen').innerHTML = seleccionado.imagen
        ? `<img src="${seleccionado.imagen}" alt="${seleccionado.nombre}">`
        : '<i class="bi bi-box"></i>';
    $('pv-nombre').textContent = seleccionado.nombre;
    $('pv-meta').textContent = `SKU ${seleccionado.codigo}`;
    $('pv-precio').textContent = moneda(seleccionado.precio_venta);
    $('vista-previa').classList.add('activa');
    actualizarStockPreview();
}

/* ---------- carrito ---------- */
function agregarAlCarrito(id, pedida) {
    const p = porId.get(id);
    if (!p) return;
    const disponible = stockDisponible(id);
    if (disponible <= 0) {
        aviso(`"${p.nombre}" no tiene stock disponible.`);
        return;
    }
    const cantidad = Math.min(Math.max(1, Math.floor(Number(pedida) || 1)), disponible);
    if (cantidad < pedida) {
        aviso(`Se ajustó la cantidad: solo hay ${disponible} u. de "${p.nombre}".`);
    }
    carrito.set(id, (carrito.get(id) || 0) + cantidad);
    renderCarrito();
    actualizarStockPreview();
}

function setCantidad(id, valor) {
    const p = porId.get(id);
    const actual = carrito.get(id) || 0;
    let v = Math.floor(Number(valor));
    if (!v || v <= 0) {
        carrito.delete(id);
    } else {
        if (v > p.stock) {
            aviso(`Stock máximo de "${p.nombre}": ${p.stock} u.`);
            v = p.stock;
        }
        carrito.set(id, v);
    }
    renderCarrito();
    actualizarStockPreview();
}

function renderCarrito() {
    const cuerpo = $('cuerpo-carrito');
    cuerpo.innerHTML = '';
    let subtotal = 0;
    let unidades = 0;

    for (const [id, cantidad] of carrito) {
        const p = porId.get(id);
        const sub = p.precio_venta * cantidad;
        subtotal += sub;
        unidades += cantidad;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><div class="celda-producto">
                    ${imagenProducto(p, 'mini-img')}
                    <span class="prod-nombre" data-id="${id}" title="Ver detalle">
                        ${p.nombre}<small>${p.codigo}</small>
                    </span>
                </div></td>
            <td>${moneda(p.precio_venta)}</td>
            <td><div class="stepper stepper-tabla">
                    <button type="button" data-accion="menos" data-id="${id}">&minus;</button>
                    <input type="number" min="1" max="${p.stock}" value="${cantidad}" data-id="${id}">
                    <button type="button" data-accion="mas" data-id="${id}">+</button>
                </div></td>
            <td class="verde">${moneda(sub)}</td>
            <td><button type="button" class="btn-x" data-accion="eliminar" data-id="${id}"
                        title="Quitar"><i class="bi bi-trash"></i></button></td>`;
        cuerpo.appendChild(tr);
    }

    $('carrito-vacio').hidden = carrito.size > 0;
    $('tabla-carrito').hidden = carrito.size === 0;
    $('res-articulos').textContent = unidades;
    $('res-subtotal').textContent = moneda(subtotal);

    const iva = subtotal * TASA_IVA;
    $('res-iva').textContent = moneda(iva);
    const totalVenta = redondear2(subtotal + iva);
    $('total').textContent = moneda(totalVenta);

    iniciarPago(totalVenta);

    // Contrato con el backend: inputs ocultos cant_ID
    $('contenedor-items').innerHTML = [...carrito]
        .map(([id, cantidad]) => `<input type="hidden" name="cant_${id}" value="${cantidad}">`)
        .join('');
}

/* Eventos delegados de la tabla */
$('cuerpo-carrito').addEventListener('click', evento => {
    const nombre = evento.target.closest('.prod-nombre');
    if (nombre) { seleccionarProducto(nombre.dataset.id); return; }

    const boton = evento.target.closest('button[data-accion]');
    if (!boton) return;
    const { accion, id } = boton.dataset;
    const actual = carrito.get(id) || 0;

    if (accion === 'eliminar') carrito.delete(id);
    if (accion === 'menos') actual <= 1 ? carrito.delete(id) : carrito.set(id, actual - 1);
    if (accion === 'mas') {
        const maximo = porId.get(id).stock;
        if (actual >= maximo) aviso(`Stock máximo de "${porId.get(id).nombre}": ${maximo} u.`);
        else carrito.set(id, actual + 1);
    }
    renderCarrito();
    actualizarStockPreview();
});

$('cuerpo-carrito').addEventListener('change', evento => {
    const entrada = evento.target.closest('input[data-id]');
    if (entrada) setCantidad(entrada.dataset.id, entrada.value);
});

/* ---------- cliente ---------- */
const campoCliente = $('campo-cliente');
const buscarCliente = $('buscar-cliente');
const resultadosCliente = $('resultados-cliente');

function elegirClienteFinal() {
    $('modo-final').classList.add('activo');
    $('modo-registrado').classList.remove('activo');
    buscarCliente.hidden = true;
    resultadosCliente.hidden = true;
    campoCliente.value = 'Consumidor final';
    $('chip-cliente').innerHTML = '<i class="bi bi-person"></i> Consumidor final';
    $('res-cliente').textContent = 'Consumidor final';
}

$('modo-final').addEventListener('click', elegirClienteFinal);

$('modo-registrado').addEventListener('click', () => {
    $('modo-registrado').classList.add('activo');
    $('modo-final').classList.remove('activo');
    buscarCliente.hidden = false;
    buscarCliente.focus();
});

let temporizadorCliente;
buscarCliente.addEventListener('input', () => {
    clearTimeout(temporizadorCliente);
    temporizadorCliente = setTimeout(async () => {
        const q = buscarCliente.value.trim();
        resultadosCliente.innerHTML = '';
        if (!q) { resultadosCliente.hidden = true; return; }
        try {
            const respuesta = await fetch(`/api/clientes/?q=${encodeURIComponent(q)}`);
            const datos = await respuesta.json();
            if (!datos.clientes.length) {
                const li = document.createElement('li');
                li.className = 'sin-resultados';
                li.textContent = 'Sin clientes registrados que coincidan.';
                resultadosCliente.appendChild(li);
            }
            for (const c of datos.clientes) {
                const li = document.createElement('li');
                li.innerHTML = `
                    <i class="bi bi-person-circle"></i>
                    <span class="sug-nombre">${c.nombre}${c.documento ? ` — ${c.documento}` : ''}</span>`;
                li.addEventListener('click', () => {
                    campoCliente.value = c.nombre;
                    const etiqueta = c.documento ? `${c.nombre} · ${c.documento}` : c.nombre;
                    $('chip-cliente').innerHTML = `<i class="bi bi-person-check"></i> ${etiqueta}`;
                    $('res-cliente').textContent = etiqueta;
                    buscarCliente.value = '';
                    resultadosCliente.hidden = true;
                });
                resultadosCliente.appendChild(li);
            }
            resultadosCliente.hidden = false;
        } catch {
            aviso('No se pudo consultar los clientes.');
        }
    }, 250);
});

/* ---------- limpiar / cancelar / confirmar ---------- */
function reiniciarVenta() {
    carrito.clear();
    editadoEfectivo = false;
    editadoTransferencia = false;
    pagoEfectivo.value = '';
    pagoTransf.value = '';
    $('pago-banco').value = '';
    $('pago-comprobante').value = '';
    renderCarrito();
    actualizarStockPreview();
}

$('limpiar').addEventListener('click', reiniciarVenta);
$('cancelar').addEventListener('click', reiniciarVenta);

$('form-venta').addEventListener('submit', evento => {
    if (!carrito.size) {
        evento.preventDefault();
        aviso('Agrega al menos un producto a la venta.');
    }
});

/* ---------- inicio ---------- */
renderCarrito();
