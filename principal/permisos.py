from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

GRUPO_DUENO = 'Dueno'
GRUPO_CAJERO = 'Cajero'


def _en_grupo(usuario, nombre):
    return usuario.is_authenticated and usuario.groups.filter(name=nombre).exists()


def es_superadmin(usuario):
    return usuario.is_authenticated and usuario.is_superuser


def es_dueno(usuario):
    return es_superadmin(usuario) or _en_grupo(usuario, GRUPO_DUENO)


def es_cajero(usuario):
    return _en_grupo(usuario, GRUPO_CAJERO)


def requiere_dueno(vista):
    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if es_dueno(request.user):
            return vista(request, *args, **kwargs)
        messages.error(request, 'No tienes permisos para acceder a esa sección.')
        return redirect('panel')
    return envuelta
