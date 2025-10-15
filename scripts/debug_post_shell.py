#!/usr/bin/env python
import os, sys
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS += ['testserver','127.0.0.1','localhost']
from django.test import Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from io import BytesIO
from jugadores.models import Jugador

User.objects.filter(username='staff_test_local').delete()
staff=User.objects.create_user(username='staff_test_local', password='pw')
staff.is_staff=True
staff.save()

c=Client()
assert c.login(username='staff_test_local', password='pw')

j=Jugador.objects.first()
buf=BytesIO(); Image.new('RGB',(100,100),(73,109,137)).save(buf,format='PNG'); buf.seek(0)
comp=SimpleUploadedFile('img.png',buf.read(),content_type='image/png')
data={'jugador':str(j.id),'tipo':'inscripcion','monto':'12.00','metodo':'pago_movil','referencia':'ABC-12345678','comprobante':comp,'moneda':'VES'}
resp=c.post('/agregar_pago_admin/', data)
print('status', resp.status_code)
print('location', resp.get('Location'))
s = resp.content.decode('utf-8')
import re
m = re.findall(r'<ul class="errorlist"[^>]*>.*?</ul>', s, flags=re.S)
print('found errorlists:', len(m))
for i,mm in enumerate(m,1):
    print('--- errorlist',i,'---')
    print(mm)

print('\n--- full response snippet (first 2000 chars) ---')
print(s[:2000])
