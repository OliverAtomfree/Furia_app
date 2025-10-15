from django.shortcuts import render, redirect
from .models import Jugador
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def encuestas(request):
    jugadores = Jugador.objects.all()
    mensaje = ''
    if request.method == 'POST':
        if 'jugador' in request.POST:
            jugador_id = request.POST.get('jugador')
            jugador = Jugador.objects.filter(id=jugador_id).first()
            mensaje = f'¡Has votado por {jugador.nombre} {jugador.apellido} como Jugador del Partido!'
        elif 'camiseta' in request.POST:
            camiseta = request.POST.get('camiseta')
            mensaje = f'¡Has votado por la camiseta {camiseta} para el próximo partido!'
    return render(request, 'jugadores/encuestas.html', {'jugadores': jugadores, 'mensaje': mensaje})
