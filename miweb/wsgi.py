"""
WSGI config for miweb project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'miweb.settings')

application = get_wsgi_application()

# --- CREACIÓN AUTOMÁTICA DE SUPERUSUARIO AL ARRANCAR ---
try:
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'alejo1234')
    else:
        u = User.objects.get(username='admin')
        u.set_password('alejo1234')
        u.is_staff = True
        u.is_superuser = True
        u.save()
except Exception:
    pass # Evita que la aplicación falle si la base de datos aún no está lista

