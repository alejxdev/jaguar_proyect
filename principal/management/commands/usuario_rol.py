from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError

from principal.permisos import GRUPO_CAJERO, GRUPO_DUENO

ROLES = {'dueno': GRUPO_DUENO, 'cajero': GRUPO_CAJERO}


class Command(BaseCommand):
    help = 'Asigna el rol de un usuario: usuario_rol <username> <dueno|cajero|ninguno>'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('rol', choices=[*ROLES.keys(), 'ninguno'])

    def handle(self, *args, **opciones):
        username = opciones['username']
        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"El usuario '{username}' no existe.")
        usuario.groups.remove(*Group.objects.filter(name__in=ROLES.values()))
        nombre = ROLES.get(opciones['rol'])
        if nombre:
            usuario.groups.add(Group.objects.get(name=nombre))
            self.stdout.write(self.style.SUCCESS(
                f"'{username}' ahora tiene el rol {nombre}."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Se quitaron los roles de '{username}'."
            ))
