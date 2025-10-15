from django.shortcuts import render
from .models import Jugador, Estadistica, Partido
from django.db.models import Sum, Count, Q, F
from .models import Tarjeta, Torneo
from django.db.models import Value
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required


def _get_count_or_sum(jugador, field_name, partido_qs=None, partido_obj=None):
    """Si existe un campo numérico (goles/asistencias) lo suma; si no, devuelve el count de la relación ManyToMany.
    field_name debe ser 'anotadores' o 'asistentes' (relación ManyToMany en Estadistica)."""
    if partido_obj is not None:
        total = Estadistica.objects.filter(partido=partido_obj, **{field_name: jugador}).aggregate(total=Sum('goles' if field_name=='anotadores' else 'asistencias'))['total'] or 0
        if total > 0:
            return total
        return Estadistica.objects.filter(partido=partido_obj, **{field_name: jugador}).count()
    if partido_qs is not None:
        total = Estadistica.objects.filter(partido__in=partido_qs, **{field_name: jugador}).aggregate(total=Sum('goles' if field_name=='anotadores' else 'asistencias'))['total'] or 0
        if total > 0:
            return total
        return Estadistica.objects.filter(partido__in=partido_qs, **{field_name: jugador}).count()
    # global
    total = Estadistica.objects.filter(**{field_name: jugador}).aggregate(total=Sum('goles' if field_name=='anotadores' else 'asistencias'))['total'] or 0
    if total > 0:
        return total
    return Estadistica.objects.filter(**{field_name: jugador}).count()


def estadisticas_por_partido(request, partido_id):
    partido = Partido.objects.filter(id=partido_id).first()
    if not partido:
        return render(request, 'jugadores/estadisticas_por_partido.html', {'error': 'Partido no encontrado.'})
    jugadores = Jugador.objects.filter(equipo__in=[partido.equipo_local, partido.equipo_visitante])
    # Agregaciones: obtener totales por jugador en pocas consultas para evitar N+1
    datos = []
    # Goles por jugador (puede venir del campo 'goles' en Estadistica)
    goles_qs = Estadistica.objects.filter(partido=partido).values('anotadores').annotate(total_goles=Sum('goles'))
    goles_map = {item['anotadores']: item['total_goles'] or 0 for item in goles_qs if item['anotadores']}
    # Asistencias por jugador
    asist_qs = Estadistica.objects.filter(partido=partido).values('asistentes').annotate(total_asist=Sum('asistencias'))
    asist_map = {item['asistentes']: item['total_asist'] or 0 for item in asist_qs if item['asistentes']}
    # Si no hay valores numéricos en las filas (caso mixto), también contamos las relaciones ManyToMany por jugador
    goles_rel_count = Estadistica.objects.filter(partido=partido).values('anotadores').annotate(cnt=Count('anotadores'))
    goles_rel_map = {item['anotadores']: item['cnt'] for item in goles_rel_count if item['anotadores']}
    asist_rel_count = Estadistica.objects.filter(partido=partido).values('asistentes').annotate(cnt=Count('asistentes'))
    asist_rel_map = {item['asistentes']: item['cnt'] for item in asist_rel_count if item['asistentes']}
    # Tarjetas por jugador por tipo
    tarjetas_qs = Tarjeta.objects.filter(partido=partido).values('jugador', 'tipo').annotate(cnt=Count('id'))
    tarjetas_map = {}
    for item in tarjetas_qs:
        tarifas = tarjetas_map.setdefault(item['jugador'], {'amarilla': 0, 'roja': 0})
        tarifas[item['tipo']] = item['cnt']

    for jugador in jugadores:
        goles = goles_map.get(jugador.id, 0) or goles_rel_map.get(jugador.id, 0)
        asistencias = asist_map.get(jugador.id, 0) or asist_rel_map.get(jugador.id, 0)
        jugador_tarjetas = tarjetas_map.get(jugador.id, {'amarilla': 0, 'roja': 0})
        amarillas = jugador_tarjetas.get('amarilla', 0)
        rojas = jugador_tarjetas.get('roja', 0)
        datos.append({'jugador': jugador, 'goles': goles, 'asistencias': asistencias, 'amarillas': amarillas, 'rojas': rojas})
    return render(request, 'jugadores/estadisticas_por_partido.html', {'partido': partido, 'datos': datos})


def estadisticas_por_torneo(request, torneo_id):
    torneo = Torneo.objects.filter(id=torneo_id).first()
    if not torneo:
        return render(request, 'jugadores/estadisticas_por_torneo.html', {'error': 'Torneo no encontrado.'})
    # Obtener todos los partidos del torneo
    partidos = torneo.partidos.all()
    equipos_ids = list({p.equipo_local_id for p in partidos} | {p.equipo_visitante_id for p in partidos})
    jugadores = Jugador.objects.filter(equipo_id__in=equipos_ids).distinct()
    datos = []
    # Agregaciones globales por torneo: sumar goles/asistencias y contar tarjetas en pocas consultas
    goles_qs = Estadistica.objects.filter(partido__in=partidos).values('anotadores').annotate(total_goles=Sum('goles'))
    goles_map = {item['anotadores']: item['total_goles'] or 0 for item in goles_qs if item['anotadores']}
    asist_qs = Estadistica.objects.filter(partido__in=partidos).values('asistentes').annotate(total_asist=Sum('asistencias'))
    asist_map = {item['asistentes']: item['total_asist'] or 0 for item in asist_qs if item['asistentes']}
    goles_rel_count = Estadistica.objects.filter(partido__in=partidos).values('anotadores').annotate(cnt=Count('anotadores'))
    goles_rel_map = {item['anotadores']: item['cnt'] for item in goles_rel_count if item['anotadores']}
    asist_rel_count = Estadistica.objects.filter(partido__in=partidos).values('asistentes').annotate(cnt=Count('asistentes'))
    asist_rel_map = {item['asistentes']: item['cnt'] for item in asist_rel_count if item['asistentes']}
    tarjetas_qs = Tarjeta.objects.filter(partido__in=partidos).values('jugador', 'tipo').annotate(cnt=Count('id'))
    tarjetas_map = {}
    for item in tarjetas_qs:
        tarifas = tarjetas_map.setdefault(item['jugador'], {'amarilla': 0, 'roja': 0})
        tarifas[item['tipo']] = item['cnt']

    for jugador in jugadores:
        goles = goles_map.get(jugador.id, 0) or goles_rel_map.get(jugador.id, 0)
        asistencias = asist_map.get(jugador.id, 0) or asist_rel_map.get(jugador.id, 0)
        jugador_tarjetas = tarjetas_map.get(jugador.id, {'amarilla': 0, 'roja': 0})
        amarillas = jugador_tarjetas.get('amarilla', 0)
        rojas = jugador_tarjetas.get('roja', 0)
        datos.append({'jugador': jugador, 'goles': goles, 'asistencias': asistencias, 'amarillas': amarillas, 'rojas': rojas})
    return render(request, 'jugadores/estadisticas_por_torneo.html', {'torneo': torneo, 'datos': datos})


@staff_member_required
def debug_estadisticas_jugador(request, jugador_id=None):
    """Vista de depuración: muestra filas de Estadistica y Tarjeta para un jugador (solo staff)."""
    if jugador_id:
        jugador = get_object_or_404(Jugador, id=jugador_id)
    else:
        # si no se pasa id, buscar por nombre en GET
        nombre = request.GET.get('nombre')
        apellido = request.GET.get('apellido')
        jugador = Jugador.objects.filter(nombre__icontains=nombre or '', apellido__icontains=apellido or '').first()
        if not jugador:
            return render(request, 'jugadores/debug_estadisticas.html', {'error': 'Jugador no encontrado'})

    estadisticas = Estadistica.objects.filter(anotadores=jugador) | Estadistica.objects.filter(asistentes=jugador) | Estadistica.objects.filter(amonestados=jugador) | Estadistica.objects.filter(expulsados=jugador)
    estadisticas = estadisticas.distinct().order_by('-partido__fecha')
    tarjetas = Tarjeta.objects.filter(jugador=jugador).order_by('-fecha')
    return render(request, 'jugadores/debug_estadisticas.html', {'jugador': jugador, 'estadisticas': estadisticas, 'tarjetas': tarjetas})

@login_required
def estadisticas_equipo(request):
    # Estadísticas por jugador usando los nuevos campos ManyToMany
    jugadores = Jugador.objects.all()
    estadisticas_jugadores = []
    max_goleador = {'nombre': 'N/A', 'apellido': '', 'goles': 0}
    max_asistente = {'nombre': 'N/A', 'apellido': '', 'asistencias': 0}
    max_amarillas = None
    max_rojas = None
    jugador_amarillas = None
    jugador_rojas = None
    from django.db.models import Sum
    # Precalcular agregados globales para evitar N+1
    # Goles por jugador (sumando campo 'goles' en Estadistica cuando exista)
    goles_qs = Estadistica.objects.values('anotadores').annotate(total_goles=Sum('goles'))
    goles_map = {item['anotadores']: item['total_goles'] or 0 for item in goles_qs if item['anotadores']}
    goles_rel_qs = Estadistica.objects.values('anotadores').annotate(cnt=Count('anotadores'))
    goles_rel_map = {item['anotadores']: item['cnt'] for item in goles_rel_qs if item['anotadores']}
    # Asistencias por jugador
    asist_qs = Estadistica.objects.values('asistentes').annotate(total_asist=Sum('asistencias'))
    asist_map = {item['asistentes']: item['total_asist'] or 0 for item in asist_qs if item['asistentes']}
    asist_rel_qs = Estadistica.objects.values('asistentes').annotate(cnt=Count('asistentes'))
    asist_rel_map = {item['asistentes']: item['cnt'] for item in asist_rel_qs if item['asistentes']}
    # Tarjetas totales por jugador y tipo
    # Solo considerar tarjetas no anuladas para las estadísticas activas
    tarjetas_qs = Tarjeta.objects.filter(anulada=False).values('jugador', 'tipo').annotate(cnt=Count('id'))
    tarjetas_map = {}
    for item in tarjetas_qs:
        mapa = tarjetas_map.setdefault(item['jugador'], {'amarilla': 0, 'roja': 0})
        mapa[item['tipo']] = item['cnt']

    for jugador in jugadores:
        # Sumar los goles/asistencias asociados al jugador (si en el sistema se guarda el número en el campo goles/asistencias)
        goles = goles_map.get(jugador.id, 0) or goles_rel_map.get(jugador.id, 0)
        asistencias = asist_map.get(jugador.id, 0) or asist_rel_map.get(jugador.id, 0)
        # Para tarjetas usamos el mapa precomputado
        jugador_tarjetas = tarjetas_map.get(jugador.id, {'amarilla': 0, 'roja': 0})
        tarjetas_amarillas = jugador_tarjetas.get('amarilla', 0)
        tarjetas_rojas = jugador_tarjetas.get('roja', 0)
        # Lista de tarjetas del jugador (histórico) - prefetech desde el mapa construido más abajo
        tarjetas_lista = []
        estadisticas_jugadores.append({
            'jugador': jugador,
            'goles': goles,
            'asistencias': asistencias,
            'tarjetas_amarillas': tarjetas_amarillas,
            'tarjetas_rojas': tarjetas_rojas,
            'tarjetas': tarjetas_lista,
        })
        if goles > max_goleador['goles']:
            max_goleador = {'nombre': jugador.nombre, 'apellido': jugador.apellido, 'goles': goles}
        if asistencias > max_asistente['asistencias']:
            max_asistente = {'nombre': jugador.nombre, 'apellido': jugador.apellido, 'asistencias': asistencias}
        if tarjetas_amarillas > (max_amarillas['tarjetas_amarillas'] if max_amarillas else 0):
            max_amarillas = {'nombre': jugador.nombre, 'apellido': jugador.apellido, 'tarjetas_amarillas': tarjetas_amarillas}
            jugador_amarillas = jugador
        if tarjetas_rojas > (max_rojas['tarjetas_rojas'] if max_rojas else 0):
            max_rojas = {'nombre': jugador.nombre, 'apellido': jugador.apellido, 'tarjetas_rojas': tarjetas_rojas}
            jugador_rojas = jugador
    # Tarjetas totales
    # Totales reales de tarjetas (no anuladas) usando el modelo Tarjeta
    tarjetas_amarillas_total = Tarjeta.objects.filter(tipo='amarilla', anulada=False).count()
    tarjetas_rojas_total = Tarjeta.objects.filter(tipo='roja', anulada=False).count()
    # Obtener listas históricas de tarjetas por jugador en una sola consulta para evitar N+1
    tarjetas_all = Tarjeta.objects.filter(jugador__in=[j.id for j in jugadores]).order_by('-fecha')
    tarjetas_list_map = {}
    for t in tarjetas_all:
        tarjetas_list_map.setdefault(t.jugador_id, []).append(t)
    # Ahora asignar las listas a los registros en estadisticas_jugadores
    for rec in estadisticas_jugadores:
        rec['tarjetas'] = tarjetas_list_map.get(rec['jugador'].id, [])
    # Porcentaje de victorias
    total_partidos = Partido.objects.count()
    ganados = Partido.objects.filter(Q(marcador_local__gt=F('marcador_visitante')) | Q(marcador_visitante__gt=F('marcador_local'))).count()
    porcentaje_victorias = round((ganados / total_partidos) * 100, 2) if total_partidos > 0 else 0
    context = {
        'max_goleador': max_goleador,
        'max_asistente': max_asistente,
        'tarjetas_amarillas': tarjetas_amarillas_total,
        'tarjetas_rojas': tarjetas_rojas_total,
        'porcentaje_victorias': porcentaje_victorias,
        'estadisticas_jugadores': estadisticas_jugadores,
        'jugador_amarillas': jugador_amarillas,
        'max_amarillas': max_amarillas,
        'jugador_rojas': jugador_rojas,
        'max_rojas': max_rojas,
    }
    return render(request, 'jugadores/estadisticas_equipo.html', context)
