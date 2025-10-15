import os
import sys
# Asegurar que el directorio del proyecto está en sys.path
BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from jugadores.models import Jugador, Estadistica, Tarjeta

qs = Jugador.objects.filter(nombre__icontains='Hector') | Jugador.objects.filter(nombre__icontains='Héctor')
print('Encontrados:', qs.count())
for j in qs:
    print('---', j.id, j.nombre, j.apellido)
    # Estadísticas donde participa como anotador o asistente o amonestado o expulsado
    ests = (Estadistica.objects.filter(anotadores=j) | Estadistica.objects.filter(asistentes=j) | Estadistica.objects.filter(amonestados=j) | Estadistica.objects.filter(expulsados=j)).distinct()
    print('Estadisticas count:', ests.count())
    for e in ests:
        print(' E: partido=', e.partido, 'goles=', e.goles, 'asistencias=', e.asistencias, 'amonestados_count=', e.amonestados.count(), 'expulsados_count=', e.expulsados.count())
    tars = Tarjeta.objects.filter(jugador=j).order_by('-fecha')
    print('Tarjetas count:', tars.count())
    for t in tars:
        print(' T:', t.get_tipo_display(), 'minuto=', t.minuto, 'partido=', t.partido, 'fecha=', t.fecha)

print('Hecho')
