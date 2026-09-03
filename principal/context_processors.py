from .permisos import es_cajero, es_dueno


def roles(request):
    return {
        'es_dueno': es_dueno(request.user),
        'es_cajero': es_cajero(request.user),
    }
