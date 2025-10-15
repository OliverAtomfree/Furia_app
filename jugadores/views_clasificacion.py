from django.shortcuts import render
from .models import Equipo, Partido, Torneo
from django.db.models import Q, Sum, Count, F

def tabla_clasificacion(request):
    torneos = Torneo.objects.all()
    torneo_id = request.GET.get('torneo')
    torneo = Torneo.objects.filter(id=torneo_id).first() if torneo_id else torneos.first()
    equipos = Equipo.objects.filter(torneos=torneo)
    clasificacion = []
    for equipo in equipos:
        partidos_local = Partido.objects.filter(equipo_local=equipo, torneo=torneo)
        partidos_visitante = Partido.objects.filter(equipo_visitante=equipo, torneo=torneo)
        jugados = partidos_local.count() + partidos_visitante.count()
        ganados = partidos_local.filter(marcador_local__gt=F('marcador_visitante')).count() + \
                  partidos_visitante.filter(marcador_visitante__gt=F('marcador_local')).count()
        empatados = partidos_local.filter(marcador_local=F('marcador_visitante')).count() + \
                    partidos_visitante.filter(marcador_local=F('marcador_visitante')).count()
        perdidos = jugados - ganados - empatados
        goles_favor = partidos_local.aggregate(Sum('marcador_local'))['marcador_local__sum'] or 0
        goles_favor += partidos_visitante.aggregate(Sum('marcador_visitante'))['marcador_visitante__sum'] or 0
        goles_contra = partidos_local.aggregate(Sum('marcador_visitante'))['marcador_visitante__sum'] or 0
        goles_contra += partidos_visitante.aggregate(Sum('marcador_local'))['marcador_local__sum'] or 0
        puntos = ganados * 3 + empatados
        clasificacion.append({
            'nombre': equipo.nombre,
            'puntos': puntos,
            'jugados': jugados,
            'ganados': ganados,
            'empatados': empatados,
            'perdidos': perdidos,
            'goles_favor': goles_favor,
            'goles_contra': goles_contra,
        })
    clasificacion = sorted(clasificacion, key=lambda x: (-x['puntos'], x['goles_favor']-x['goles_contra']))
    return render(request, 'jugadores/tabla_clasificacion.html', {
        'equipos': clasificacion,
        'torneos': torneos,
        'torneo_seleccionado': torneo
    })
