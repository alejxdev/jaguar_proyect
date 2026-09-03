from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from principal.permisos import GRUPO_CAJERO, GRUPO_DUENO

PERMISOS_CAJERO = [
    'add_venta', 'change_venta', 'view_venta',
    'add_detalleventa', 'change_detalleventa', 'view_detalleventa',
    'add_caja', 'change_caja', 'view_caja',
    'view_producto', 'view_categoria', 'view_cliente',
]


class Command(BaseCommand):
    help = (
        'Crea los grupos Dueno y Cajero con sus permisos. '
        'El SuperAdmin se crea aparte con createsuperuser.'
    )

    def handle(self, *args, **opciones):
        dueno, creado_dueno = Group.objects.get_or_create(name=GRUPO_DUENO)
        cajero, creado_cajero = Group.objects.get_or_create(name=GRUPO_CAJERO)

        permisos_totales = Permission.objects.filter(
            content_type__app_label='principal',
        )
        dueno.permissions.set(permisos_totales)

        permisos_limitados = Permission.objects.filter(
            codename__in=PERMISOS_CAJERO,
        )
        cajero.permissions.set(permisos_limitados)

        if creado_dueno:
            self.stdout.write(f"Grupo '{GRUPO_DUENO}' creado.")
        if creado_cajero:
            self.stdout.write(f"Grupo '{GRUPO_CAJERO}' creado.")
        self.stdout.write(self.style.SUCCESS(
            f"{GRUPO_DUENO}: {dueno.permissions.count()} permisos | "
            f"{GRUPO_CAJERO}: {cajero.permissions.count()} permisos."
        ))
        self.stdout.write(
            'Asigna usuarios con: python manage.py usuario_rol <username> <rol>'
        )
