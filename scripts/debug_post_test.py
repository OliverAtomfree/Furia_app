# debug_post_test.py - reproduce failing test POST and print response info
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from io import BytesIO
from PIL import Image

# create staff user
User.objects.filter(username='staff_test_local').delete()
staff = User.objects.create_user(username='staff_test_local', password='pw')
staff.is_staff = True
staff.save()

c = Client()
logged = c.login(username='staff_test_local', password='pw')
print('logged in?', logged)

# build image
buf = BytesIO()
img = Image.new('RGB', (100,100), color=(73,109,137))
img.save(buf, format='PNG')
buf.seek(0)

from django.core.files.uploadedfile import SimpleUploadedFile
comprobante = SimpleUploadedFile('img.png', buf.read(), content_type='image/png')

# prepare data (copy from test)
from jugadores.models import Jugador
j = Jugador.objects.first()
if not j:
    print('no jugador exists; abort')
    raise SystemExit(1)

data = {
    'jugador': str(j.id),
    'tipo': 'inscripcion',
    'monto': '12.00',
    'metodo': 'pago_movil',
    'referencia': 'ABC-12345678',
    'comprobante': comprobante,
    'moneda': 'VES',
}
resp = c.post('/agregar_pago_admin/', data)
print('status_code', resp.status_code)
print('redirected:', resp.has_header('Location'))
print('Content length:', len(resp.content))
# Print a snippet of content for debugging
print('--- response snippet ---')
print(resp.content.decode('utf-8')[:2000])
print('--- end snippet ---')
