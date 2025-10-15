import os
import sys
import django

env_path = os.path.dirname(os.path.dirname(__file__))
os.chdir(env_path)
sys.path.insert(0, env_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from jugadores.models import Equipo, Jugador

# Preparar datos mínimos
Equipo.objects.get_or_create(nombre='E1_debug')

# Crear user staff
staff, created = User.objects.get_or_create(username='debug_staff')
if created:
    staff.set_password('pw')
    staff.is_staff = True
    staff.save()
else:
    staff.is_staff = True
    staff.set_password('pw')
    staff.save()

# Crear jugador asociado
user_j, _ = User.objects.get_or_create(username='pj_debug')
user_j.set_password('pw')
user_j.save()
e1 = Equipo.objects.first()
jugador, _ = Jugador.objects.get_or_create(user=user_j, defaults={'nombre':'Dbg','apellido':'User','equipo':e1})

c = Client()
# login
c.force_login(staff)

# preparar comprobante
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from io import BytesIO
buf = BytesIO()
# Generar una imagen suficientemente grande para pasar la validación de tamaño
img = Image.new('RGB', (600, 600), color=(73, 109, 137))
img.save(buf, format='PNG')
buf.seek(0)
comprobante_file = SimpleUploadedFile('img.png', buf.read(), content_type='image/png')

data = {
    'jugador': str(jugador.id),
    'tipo': 'inscripcion',
    'monto': '12.00',
    'metodo': 'pago_movil',
    'referencia': 'ABC-12345678',
    'moneda': 'VES',
}

from django.urls import reverse
url = reverse('agregar_pago_admin')
resp = c.post(url, data={**data, 'comprobante': comprobante_file}, **{'HTTP_HOST': 'localhost'})
print('STATUS', resp.status_code)
if hasattr(resp, 'redirect_chain'):
    print('REDIRECTS', resp.redirect_chain)
if hasattr(resp, 'context') and resp.context:
    print('TEMPLATE CONTEXT KEYS:', list(resp.context.keys()))
    # show messages if exist
    msgs = resp.context.get('messages')
    if msgs:
        print('MESSAGES:')
        for m in msgs:
            print('-', m)
print('CONTENT START:')
print(resp.content.decode('utf-8')[:4000])
