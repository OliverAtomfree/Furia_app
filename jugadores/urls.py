# jugadores/urls.py
from django.urls import path
from . import views
from .views_clasificacion import tabla_clasificacion
from .views_estadisticas import estadisticas_equipo
from .views_estadisticas import estadisticas_por_partido, estadisticas_por_torneo, debug_estadisticas_jugador
from .views_encuestas import encuestas

urlpatterns = [
    # Rutas para vistas públicas y de usuario
    path('', views.inicio, name='inicio'),
    path('jugador/<int:jugador_id>/', views.perfil_jugador, name='perfil_jugador'),
    path('partido/<int:partido_id>/', views.detalle_partido, name='detalle_partido'),
# Noticias eliminado
    path('resultados/', views.resultados_partidos, name='resultados_partidos'),


    # Rutas para la autenticación
    path('registro/', views.registro, name='registro'),
    path('iniciar_sesion/', views.iniciar_sesion, name='iniciar_sesion'),
    path('cerrar_sesion/', views.cerrar_sesion, name='cerrar_sesion'),
    
    # Rutas para el perfil del jugador
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    # Staff/admin puede editar cualquier perfil
    path('perfil/editar/<int:jugador_id>/', views.editar_perfil_admin, name='editar_perfil_admin'),
    
    # Rutas para el staff (con la lógica de autenticación en las vistas)
    path('registrar_estadistica/', views.registrar_estadistica, name='registrar_estadistica'),
    path('agregar_partido/', views.agregar_partido, name='agregar_partido'),

    # Rutas para agregar entidades desde el frontend (solo staff)
    path('agregar_jugador/', views.agregar_jugador, name='agregar_jugador'),
    path('agregar_equipo/', views.agregar_equipo, name='agregar_equipo'),
    path('agregar_torneo/', views.agregar_torneo, name='agregar_torneo'),

    # Listados para staff/admin
    path('lista_jugadores/', views.lista_jugadores, name='lista_jugadores'),
    path('eliminar_jugador/<int:jugador_id>/', views.eliminar_jugador, name='eliminar_jugador'),
    path('lista_equipos/', views.lista_equipos, name='lista_equipos'),
    path('lista_torneos/', views.lista_torneos, name='lista_torneos'),
    path('torneo/<int:torneo_id>/', views.torneo_detalle, name='torneo_detalle'),
    # Edición de equipo y torneo
    path('equipo/<int:equipo_id>/editar/', views.editar_equipo, name='editar_equipo'),
        path('eliminar_equipo/<int:equipo_id>/', views.eliminar_equipo, name='eliminar_equipo'),
    path('torneo/<int:torneo_id>/editar/', views.editar_torneo, name='editar_torneo'),
    path('torneo/<int:torneo_id>/agregar_equipos/', views.agregar_equipos_a_torneo, name='agregar_equipos_a_torneo'),
    path('eliminar_torneo/<int:torneo_id>/', views.eliminar_torneo, name='eliminar_torneo'),

    path('clasificacion/', tabla_clasificacion, name='tabla_clasificacion'),
    path('estadisticas_equipo/', estadisticas_equipo, name='estadisticas_equipo'),
    path('estadisticas/partido/<int:partido_id>/', estadisticas_por_partido, name='estadisticas_por_partido'),
    path('estadisticas/torneo/<int:torneo_id>/', estadisticas_por_torneo, name='estadisticas_por_torneo'),
    path('encuestas/', encuestas, name='encuestas'),
    # Dashboard staff/admin
        path('debug/jugador/<int:jugador_id>/', debug_estadisticas_jugador, name='debug_estadisticas_jugador'),
    path('dashboard_staff/', views.dashboard_staff, name='dashboard_staff'),
    # Rutas para pagos
    path('registrar_pago/', views.registrar_pago, name='registrar_pago'),
    path('mis_pagos/', views.mis_pagos, name='mis_pagos'),
    path('lista_pagos/', views.lista_pagos, name='lista_pagos'),
    path('aprobar_pago/<int:pago_id>/', views.aprobar_pago, name='aprobar_pago'),
    path('archivar_pago/<int:pago_id>/', views.archivar_pago, name='archivar_pago'),
    path('agregar_pago_admin/', views.agregar_pago_admin, name='agregar_pago_admin'),
    path('pago/<int:pago_id>/', views.pago_detalle, name='pago_detalle'),
]
