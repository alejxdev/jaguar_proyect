// ===== Utilidades generales del sistema =====

// Confirmar antes de eliminar (respaldo del atributo onsubmit)
document.querySelectorAll('form[onsubmit]').forEach(form => {
    form.addEventListener('submit', evento => {
        if (!confirm('¿Estás seguro?')) evento.preventDefault();
    });
});

// Las alertas de éxito se desvanecen solas a los 4 segundos
setTimeout(() => {
    document.querySelectorAll('.alerta.success, .alerta.warning').forEach(alerta => {
        alerta.classList.add('desvanecer');
        setTimeout(() => alerta.remove(), 700);
    });
}, 4000);

// ===== Menú desplegable de la barra (Productos) =====
const menuDesplegable = document.querySelector('.menu-desplegable');
if (menuDesplegable) {
    const botonMenu = menuDesplegable.querySelector('.nav-desplegable');
    botonMenu.addEventListener('click', evento => {
        evento.stopPropagation();
        menuDesplegable.classList.toggle('abierto');
    });
    document.addEventListener('click', evento => {
        if (!menuDesplegable.contains(evento.target)) {
            menuDesplegable.classList.remove('abierto');
        }
    });
}
