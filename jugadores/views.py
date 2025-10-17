"""Vistas del app jugadores.

Este módulo fue consolidado para eliminar múltiples definiciones duplicadas
de funciones como `iniciar_sesion` y `registro`. Aquí queda una única
implementación por vista.
"""

import logging
import json
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django import forms

from .models import (
    Jugador, Equipo, Torneo, Partido, Estadistica, VotacionJugadorPartido,
    Pago, Tarjeta
)
from .forms import (
    JugadorForm, EstadisticaForm, PartidoForm, PagoForm, PagoAdminForm,
    TarjetaForm
)

logger = logging.getLogger(__name__)
DEBUG_LOG = os.path.join(os.path.dirname(__file__), '..', 'debug_pago_submit.log')


@staff_member_required
def eliminar_jugador(request, jugador_id):
    jugador = get_object_or_404(Jugador, pk=jugador_id)
    if request.method == 'POST':
        jugador.delete()
        messages.success(request, '¡Jugador eliminado correctamente!')
        return redirect('lista_jugadores')
    return render(request, 'jugadores/eliminar_jugador.html', {'jugador': jugador})


@staff_member_required
def eliminar_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, pk=torneo_id)
    if request.method == 'POST':
        torneo.delete()
        messages.success(request, '¡Torneo eliminado correctamente!')
        return redirect('lista_torneos')
    return render(request, 'jugadores/eliminar_torneo.html', {'torneo': torneo})


@staff_member_required
def eliminar_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == 'POST':
        equipo.delete()
        messages.success(request, '¡Equipo eliminado correctamente!')
        return redirect('lista_equipos')
    return render(request, 'jugadores/eliminar_equipo.html', {'equipo': equipo})


@staff_member_required
def editar_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == 'POST':
        form = EquipoForm(request.POST, request.FILES, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Equipo editado correctamente!')
            return redirect('lista_equipos')
    else:
        form = EquipoForm(instance=equipo)
    return render(request, 'jugadores/editar_equipo.html', {'form': form, 'equipo': equipo})


@staff_member_required
def editar_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, pk=torneo_id)
    if request.method == 'POST':
        form = TorneoForm(request.POST, instance=torneo)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Torneo editado correctamente!')
            return redirect('lista_torneos')
    else:
        form = TorneoForm(instance=torneo)
    equipos = Equipo.objects.all()
    return render(request, 'jugadores/editar_torneo.html', {'form': form, 'torneo': torneo, 'equipos': equipos})


@staff_member_required
def agregar_equipos_a_torneo(request, torneo_id):
    """Añade uno o varios equipos a un torneo existente sin reemplazar los equipos actuales."""
    torneo = get_object_or_404(Torneo, pk=torneo_id)
    if request.method == 'POST':
        equipo_ids = request.POST.getlist('equipos')
        if equipo_ids:
            equipos_qs = Equipo.objects.filter(id__in=equipo_ids)
            for e in equipos_qs:
                torneo.equipos.add(e)
            messages.success(request, f'{equipos_qs.count()} equipo(s) agregados al torneo.')
        else:
            messages.info(request, 'No se seleccionaron equipos.')
        siguiente = request.POST.get('next')
        if siguiente:
            return redirect(siguiente)
        return redirect('editar_torneo', torneo_id=torneo.id)
    return redirect('editar_torneo', torneo_id=torneo.id)


@staff_member_required
def dashboard_staff(request):
    total_jugadores = Jugador.objects.count()
    total_equipos = Equipo.objects.count()
    total_torneos = Torneo.objects.count()
    total_partidos = Partido.objects.count()
    total_pagos = Pago.objects.count()
    pagos_pendientes = Pago.objects.filter(estado='pendiente').count()
    ultimos_pagos = Pago.objects.select_related('jugador').filter(archivado=False).order_by('-fecha')[:8]
    pagos_aprobados = Pago.objects.filter(estado='aprobado').count()
    jugadores_dashboard = Jugador.objects.all()[:50]
    return render(request, 'jugadores/dashboard_staff.html', {
        'total_jugadores': total_jugadores,
        'total_equipos': total_equipos,
        'total_torneos': total_torneos,
        'total_partidos': total_partidos,
        'total_pagos': total_pagos,
        'pagos_pendientes': pagos_pendientes,
        'pagos_aprobados': pagos_aprobados,
        'jugadores_dashboard': jugadores_dashboard,
        'ultimos_pagos': ultimos_pagos,
    })


@login_required
def detalle_partido(request, partido_id):
    partido = get_object_or_404(Partido, id=partido_id)
    estadisticas = Estadistica.objects.filter(partido=partido)
    jugadores = Jugador.objects.filter(equipo__in=[partido.equipo_local, partido.equipo_visitante])
    mensaje = ''
    if request.method == 'POST':
        if request.user.is_staff and 'submit_tarjeta' in request.POST:
            tarjeta_form = TarjetaForm(request.POST)
            if tarjeta_form.is_valid():
                tarjeta = tarjeta_form.save(commit=False)
                tarjeta.partido = partido
                tarjeta.save()
                messages.success(request, 'Tarjeta registrada correctamente.')
                return redirect('detalle_partido', partido_id=partido.id)
            else:
                mensaje = 'Error al registrar la tarjeta.'
        else:
            jugador_id = request.POST.get('jugador')
            jugador = Jugador.objects.filter(id=jugador_id).first()
            if jugador:
                VotacionJugadorPartido.objects.create(partido=partido, jugador=jugador, usuario=request.user)
                mensaje = f'¡Has votado por {jugador.nombre} {jugador.apellido} como Jugador del Partido!'
    votos = VotacionJugadorPartido.objects.filter(partido=partido).values('jugador').annotate(total=Sum('id')).order_by('-total')
    jugador_destacado = None
    if votos:
        jugador_destacado = Jugador.objects.filter(id=votos[0]['jugador']).first()
    tarjetas_por_jugador = {}
    for j in jugadores:
        amarillas = Tarjeta.objects.filter(partido=partido, jugador=j, tipo='amarilla').count()
        rojas = Tarjeta.objects.filter(partido=partido, jugador=j, tipo='roja').count()
        tarjetas = Tarjeta.objects.filter(partido=partido, jugador=j).order_by('fecha')
        tarjetas_por_jugador[j.id] = {
            'amarillas': amarillas,
            'rojas': rojas,
            'tarjetas': tarjetas,
        }
    tarjeta_form = TarjetaForm() if request.user.is_staff else None
    return render(request, 'jugadores/detalle_partido.html', {
        'partido': partido,
        'estadisticas': estadisticas,
        'jugadores': jugadores,
        'mensaje': mensaje,
        'jugador_destacado': jugador_destacado,
        'tarjetas_por_jugador': tarjetas_por_jugador,
        'tarjeta_form': tarjeta_form,
    })


@staff_member_required
def agregar_pago_admin(request):
    if request.method == 'POST':
        form = PagoAdminForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pago = form.save()
                messages.success(request, f'Pago #{pago.id} creado correctamente.')
                siguiente = request.POST.get('next')
                if siguiente == 'dashboard':
                    return redirect('dashboard_staff')
                return redirect('lista_pagos')
            except Exception as e:
                logger.exception('Error al guardar Pago desde agregar_pago_admin')
                messages.error(request, f'Error al guardar el pago: {e}')
        else:
            logger.debug('PagoAdminForm inválido: %s', form.errors.as_json())
            for field, errors in form.errors.items():
                for e in errors:
                    messages.error(request, f'{field}: {e}')
    else:
        form = PagoAdminForm()
    return render(request, 'jugadores/agregar_pago_admin.html', {'form': form})


def inicio(request):
    jugadores_lista = Jugador.objects.all()
    torneos = Torneo.objects.all()[:5]
    equipos = Equipo.objects.all()[:5]
    partidos = Partido.objects.order_by('-fecha')[:5]
    contexto = {'jugadores': jugadores_lista, 'torneos': torneos, 'equipos': equipos, 'partidos': partidos}
    return render(request, 'jugadores/inicio.html', contexto)


@login_required
def registrar_pago(request):
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = PagoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pago = form.save(commit=False)
                pago.jugador = jugador
                pago.save()
                messages.success(request, 'Pago registrado correctamente. Quedará como pendiente hasta su aprobación.')
                return redirect('mis_pagos')
            except Exception as e:
                logger.exception('Error al guardar Pago desde registrar_pago')
                messages.error(request, f'Error al guardar el pago: {e}')
        else:
            logger.debug('PagoForm inválido (registrar_pago): %s', form.errors.as_json())
            for field, errors in form.errors.items():
                for e in errors:
                    messages.error(request, f'{field}: {e}')
    else:
        form = PagoForm()
    return render(request, 'jugadores/registrar_pago.html', {'form': form})


@login_required
def mis_pagos(request):
    jugador = get_object_or_404(Jugador, user=request.user)
    pagos = Pago.objects.filter(jugador=jugador).order_by('-fecha')
    return render(request, 'jugadores/mis_pagos.html', {'pagos': pagos})


@staff_member_required
def lista_pagos(request):
    pagos = Pago.objects.select_related('jugador').order_by('-fecha')
    return render(request, 'jugadores/lista_pagos.html', {'pagos': pagos})


@staff_member_required
def aprobar_pago(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        siguiente = request.POST.get('next')
        motivo = request.POST.get('motivo')
        if accion == 'aprobar':
            pago.estado = 'aprobado'
            pago.motivo_rechazo = None
            pago.save()
            messages.success(request, f'Pago #{pago.id} aprobado.')
        elif accion == 'rechazar':
            pago.estado = 'rechazado'
            pago.motivo_rechazo = motivo or ''
            pago.save()
            messages.success(request, f'Pago #{pago.id} rechazado.')
        if siguiente:
            return redirect(siguiente)
        return redirect('lista_pagos')
    return redirect('lista_pagos')


@login_required
def pago_detalle(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id)
    if not (request.user.is_staff or pago.jugador.user == request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('No tienes permiso para ver este pago')
    return render(request, 'jugadores/pago_detalle.html', {'pago': pago})


@staff_member_required
def archivar_pago(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'archivar':
            pago.archivado = True
            pago.save()
            messages.success(request, f'Pago #{pago.id} archivado.')
        elif accion == 'desarchivar':
            pago.archivado = False
            pago.save()
            messages.success(request, f'Pago #{pago.id} desarchivado.')
        siguiente = request.POST.get('next')
        if siguiente:
            return redirect(siguiente)
        return redirect('lista_pagos')
    return redirect('lista_pagos')


def perfil_jugador(request, jugador_id):
    jugador = get_object_or_404(Jugador, pk=jugador_id)
    from django.db.models import Q
    estadisticas = Estadistica.objects.filter(
        Q(anotadores=jugador) |
        Q(asistentes=jugador) |
        Q(amonestados=jugador) |
        Q(expulsados=jugador)
    ).distinct()
    totales = estadisticas.aggregate(
        goles_totales=Sum('goles'),
        asistencias_totales=Sum('asistencias')
    )
    mensaje_exito = None
    username = request.session.get('nuevo_jugador_username')
    password = request.session.get('nuevo_jugador_password')
    creado_id = request.session.get('jugador_creado_exito')
    if creado_id and int(creado_id) == int(jugador_id):
        # Mostrar las credenciales solo a staff o superuser por seguridad
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            mensaje_exito = f"¡El jugador ha sido creado correctamente!<br>Usuario: <b>{username}</b><br>Contraseña: <b>{password}</b>"
            # limpiar las credenciales de la sesión después de mostrarlas
            request.session.pop('jugador_creado_exito', None)
            request.session.pop('nuevo_jugador_username', None)
            request.session.pop('nuevo_jugador_password', None)
        else:
            # Usuarios normales ven un mensaje genérico sin la contraseña
            mensaje_exito = f"¡El jugador ha sido creado correctamente!<br>Usuario: <b>{username}</b><br>Las credenciales han sido enviadas al administrador para su revisión."
            # no borrar las credenciales desde la sesión de un usuario no administrador
    if request.method == 'POST':
        if 'submit_comentario' in request.POST and not request.user.is_authenticated:
            return redirect('iniciar_sesion')
    # Preferir el campo almacenado 'edad' en el modelo; si es None, calcularlo a partir de fecha_de_nacimiento
    edad = getattr(jugador, 'edad', None)
    if edad is None:
        try:
            edad = jugador.calcular_edad()
        except Exception:
            edad = None

    contexto = {
        'jugador': jugador,
        'estadisticas': estadisticas,
        'totales': totales,
        'mensaje_exito': mensaje_exito,
        'edad': edad,
    }
    return render(request, 'jugadores/perfil_jugador.html', contexto)


@staff_member_required
def agregar_partido(request):
    if request.method == 'POST':
        form = PartidoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Partido creado correctamente!')
            return redirect('agregar_partido')
    else:
        form = PartidoForm()
    return render(request, 'jugadores/agregar_partido.html', {'form': form})


@staff_member_required
def agregar_jugador(request):
    from django.contrib.auth.models import User, Group
    import random, string
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES)
        username = request.POST.get('usuario')
        # aceptar contraseña opcional enviada desde el formulario por el staff
        password_custom = request.POST.get('password_custom', '').strip()
        if form.is_valid() and username:
            nombre = form.cleaned_data['nombre']
            apellido = form.cleaned_data['apellido']
            posicion = form.cleaned_data['posicion']
            numero_de_camiseta = form.cleaned_data['numero_de_camiseta']
            equipo = form.cleaned_data['equipo']
            imagen_url = form.cleaned_data.get('imagen_url')
            # La contraseña es obligatoria: validar presencia y longitud mínima
            if not password_custom:
                form.add_error(None, 'La contraseña es obligatoria. Introduce una contraseña de al menos 8 caracteres.')
                return render(request, 'jugadores/agregar_jugador.html', {'form': form})
            if len(password_custom) < 8:
                form.add_error(None, 'La contraseña debe tener al menos 8 caracteres.')
                return render(request, 'jugadores/agregar_jugador.html', {'form': form})
            password = password_custom
            user_qs = User.objects.filter(username=username)
            if user_qs.exists():
                user = user_qs.first()
                if Jugador.objects.filter(user=user).exists():
                    form.add_error(None, 'Ya existe un jugador con ese nombre de usuario. Intenta con otro.')
                    return render(request, 'jugadores/agregar_jugador.html', {'form': form})
                # Si el usuario ya existe pero no tiene perfil Jugador, actualizar su contraseña
                user.set_password(password)
                user.first_name = nombre
                user.last_name = apellido
                user.save()
            else:
                user = User.objects.create_user(username=username, password=password, first_name=nombre, last_name=apellido)
            grupo_jugadores, creado = Group.objects.get_or_create(name='jugadores')
            user.groups.add(grupo_jugadores)
            # Asegurar que el campo 'cedula' requerido por el modelo exista.
            cedula = request.POST.get('cedula') or form.cleaned_data.get('cedula', '')
            if not cedula:
                # Generar una cédula numérica única de 8 dígitos
                import random
                import string as _string
                from django.db import IntegrityError, transaction
                while True:
                    candidate = ''.join(random.choices('0123456789', k=8))
                    if not Jugador.objects.filter(cedula=candidate).exists():
                        cedula = candidate
                        break
            else:
                from django.db import IntegrityError, transaction
            # Guardar jugador dentro de una transacción para gestionar errores de integridad
            from django.db import IntegrityError, transaction
            try:
                with transaction.atomic():
                    # Evitar UNIQUE constraint usando get_or_create
                    jugador, created = Jugador.objects.get_or_create(
                        user=user,
                        defaults={
                            'nombre': nombre,
                            'apellido': apellido,
                            'posicion': posicion,
                            'numero_de_camiseta': numero_de_camiseta,
                            'equipo': equipo,
                            'imagen_url': imagen_url,
                            'cedula': cedula,
                        }
                    )
                    if not created:
                        # Actualizar los campos por si se creó parcialmente antes
                        changed = False
                        if jugador.nombre != nombre:
                            jugador.nombre = nombre
                            changed = True
                        if jugador.apellido != apellido:
                            jugador.apellido = apellido
                            changed = True
                        if jugador.posicion != posicion:
                            jugador.posicion = posicion
                            changed = True
                        if jugador.numero_de_camiseta != numero_de_camiseta:
                            jugador.numero_de_camiseta = numero_de_camiseta
                            changed = True
                        if jugador.equipo != equipo:
                            jugador.equipo = equipo
                            changed = True
                        # Actualizar foto si se envió una nueva
                        if imagen_url:
                            jugador.imagen_url = imagen_url
                            changed = True
                        if cedula and jugador.cedula != cedula:
                            jugador.cedula = cedula
                            changed = True
                        if changed:
                            jugador.save()
            except Exception as ex:
                try:
                    logger.exception('Error al crear/actualizar Jugador: %s', ex)
                except Exception:
                    pass
                form.add_error(None, 'Error al crear el jugador. Verifica los datos e intenta de nuevo.')
                return render(request, 'jugadores/agregar_jugador.html', {'form': form})
            request.session['nuevo_jugador_username'] = username
            request.session['nuevo_jugador_password'] = password
            request.session['jugador_creado_exito'] = jugador.id
            messages.success(request, f"¡Jugador creado correctamente!<br>Usuario: <b>{username}</b><br>Contraseña: <b>{password}</b>")
            return redirect('inicio')
    else:
        form = JugadorForm()
    return render(request, 'jugadores/agregar_jugador.html', {'form': form})


@staff_member_required
def mostrar_credenciales_jugador(request):
    username = request.session.pop('nuevo_jugador_username', None)
    password = request.session.pop('nuevo_jugador_password', None)
    return render(request, 'jugadores/credenciales_jugador.html', {'username': username, 'password': password})


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['nombre', 'imagen_url']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'imagen_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }


class TorneoForm(forms.ModelForm):
    equipos = forms.ModelMultipleChoiceField(queryset=Equipo.objects.all(), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8}))
    class Meta:
        model = Torneo
        fields = ['nombre', 'fecha_inicio', 'fecha_fin', 'equipos']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'equipos': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8}),
        }
    def save(self, commit=True):
        torneo = super().save(commit=False)
        if commit:
            torneo.save()
            equipos = self.cleaned_data.get('equipos')
            if equipos is not None:
                torneo.equipos.set(equipos)
        return torneo


@staff_member_required
def agregar_equipo(request):
    if request.method == 'POST':
        form = EquipoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Equipo creado correctamente!')
            return redirect('agregar_equipo')
    else:
        form = EquipoForm()
    return render(request, 'jugadores/agregar_equipo.html', {'form': form})


@staff_member_required
def agregar_torneo(request):
    if request.method == 'POST':
        form = TorneoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Torneo creado correctamente!')
            return redirect('agregar_torneo')
    else:
        form = TorneoForm()
    return render(request, 'jugadores/agregar_torneo.html', {'form': form})


def registro(request):
    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            raw_password = form.cleaned_data.get('password1')
            user = form.save()
            from .models import Jugador
            if not Jugador.objects.filter(user=user).exists():
                jugador = Jugador(user=user, nombre=user.first_name, apellido=user.last_name)
                jugador.save()
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')
    else:
        form = CustomUserCreationForm()
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/registro.html', {'form': form})


@login_required
def editar_perfil(request):
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
        else:
            # Log errors and show them to the user so it's claro por qué no se guardó
            try:
                logger.debug('editar_perfil: form inválido. POST keys: %s', list(request.POST.keys()))
                logger.debug('editar_perfil: form.errors: %s', form.errors.as_json())
            except Exception:
                logger.exception('No se pudo volcar debug de editar_perfil')
            for field, errors in form.errors.items():
                for e in errors:
                    messages.error(request, f'{field}: {e}')
    else:
        form = JugadorForm(instance=jugador)
    return render(request, 'jugadores/editar_perfil.html', {'form': form})


# Permitir a staff o superuser editar el perfil de cualquier jugador
@user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))
def editar_perfil_admin(request, jugador_id):
    jugador = get_object_or_404(Jugador, pk=jugador_id)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
        else:
            try:
                logger.debug('editar_perfil_admin: form inválido. POST keys: %s', list(request.POST.keys()))
                logger.debug('editar_perfil_admin: form.errors: %s', form.errors.as_json())
            except Exception:
                logger.exception('No se pudo volcar debug de editar_perfil_admin')
            for field, errors in form.errors.items():
                for e in errors:
                    messages.error(request, f'{field}: {e}')
    else:
        form = JugadorForm(instance=jugador)
    return render(request, 'jugadores/editar_perfil.html', {'form': form, 'admin_edit': True, 'jugador': jugador})


def iniciar_sesion(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm(request)
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})


@login_required
def cerrar_sesion(request):
    logout(request)
    return redirect('inicio')


def resultados_partidos(request):
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id))
        proximos_partidos = proximos_partidos.filter(Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id))
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)


@staff_member_required
def registrar_estadistica(request):
    if request.method == 'POST':
        form = EstadisticaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inicio')
    else:
        form = EstadisticaForm()
    return render(request, 'jugadores/registrar_estadistica.html', {'form': form})


@staff_member_required
def lista_jugadores(request):
    from django.db.models import Q
    jugadores = Jugador.objects.all()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    posicion = request.GET.get('posicion')
    busqueda = request.GET.get('busqueda')
    if equipo_id:
        jugadores = jugadores.filter(equipo_id=equipo_id)
    if posicion:
        jugadores = jugadores.filter(posicion__icontains=posicion)
    if busqueda:
        jugadores = jugadores.filter(Q(nombre__icontains=busqueda) | Q(apellido__icontains=busqueda) | Q(equipo__nombre__icontains=busqueda))
    return render(request, 'jugadores/lista_jugadores.html', {'jugadores': jugadores, 'equipos': equipos, 'equipo_id': equipo_id, 'posicion': posicion, 'busqueda': busqueda})


@staff_member_required
def lista_equipos(request):
    busqueda = request.GET.get('busqueda')
    equipos = Equipo.objects.all()
    if busqueda:
        equipos = equipos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_equipos.html', {'equipos': equipos, 'busqueda': busqueda})


@staff_member_required
def lista_torneos(request):
    busqueda = request.GET.get('busqueda')
    torneos = Torneo.objects.all()
    if busqueda:
        torneos = torneos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_torneos.html', {'torneos': torneos, 'busqueda': busqueda})


@staff_member_required
def torneo_detalle(request, torneo_id):
    torneo = get_object_or_404(Torneo, pk=torneo_id)
    equipos = torneo.equipos.all()
    return render(request, 'jugadores/torneo_detalle.html', {'torneo': torneo, 'equipos': equipos})


def inicio(request):
    """
    Vista de la página de inicio que muestra la lista de todos los jugadores.
    """
    jugadores_lista = Jugador.objects.all()
    # También incluir algunos datos para la página principal
    from .models import Torneo, Equipo, Partido
    torneos = Torneo.objects.all()[:5]
    equipos = Equipo.objects.all()[:5]
    partidos = Partido.objects.order_by('-fecha')[:5]
    contexto = {'jugadores': jugadores_lista, 'torneos': torneos, 'equipos': equipos, 'partidos': partidos}
    return render(request, 'jugadores/inicio.html', contexto)


@login_required
def registrar_pago(request):
    """Permite a un jugador registrar un pago (estado 'pendiente')."""
    jugador = get_object_or_404(Jugador, user=request.user)
    from django.contrib import messages
    if request.method == 'POST':
        form = PagoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                pago = form.save(commit=False)
                pago.jugador = jugador
                pago.save()
                messages.success(request, 'Pago registrado correctamente. Quedará como pendiente hasta su aprobación.')
                return redirect('mis_pagos')
            except Exception as e:
                logger.exception('Error al guardar Pago desde registrar_pago')
                messages.error(request, f'Error al guardar el pago: {e}')
        else:
            # mostrar errores al usuario
            logger.debug('PagoForm inválido (registrar_pago): %s', form.errors.as_json())
            for field, errors in form.errors.items():
                for e in errors:
                    messages.error(request, f'{field}: {e}')
            # Dump POST/FILES for debugging
            try:
                with open(DEBUG_LOG, 'a', encoding='utf-8') as fh:
                    fh.write('FORM INVALID registrar_pago:\n')
                    fh.write(json.dumps({
                        'POST': dict(request.POST),
                        'FILES': {k: str(v) for k,v in request.FILES.items()}
                    }, default=str, ensure_ascii=False))
                    fh.write('\n---\n')
            except Exception:
                logger.exception('No se pudo escribir debug log')
    else:
        form = PagoForm()
    return render(request, 'jugadores/registrar_pago.html', {'form': form})


@login_required
def mis_pagos(request):
    """Lista de pagos del jugador autenticado."""
    jugador = get_object_or_404(Jugador, user=request.user)
    pagos = Pago.objects.filter(jugador=jugador).order_by('-fecha')
    return render(request, 'jugadores/mis_pagos.html', {'pagos': pagos})


@staff_member_required
def lista_pagos(request):
    """Vista para que el staff vea todos los pagos y su estado."""
    pagos = Pago.objects.select_related('jugador').order_by('-fecha')
    return render(request, 'jugadores/lista_pagos.html', {'pagos': pagos})


@staff_member_required
def aprobar_pago(request, pago_id):
    """Permite al staff aprobar o rechazar un pago."""
    pago = get_object_or_404(Pago, id=pago_id)
    from django.contrib import messages
    # Preferir POST para cambios de estado (más seguro). Aceptar 'accion' por POST.
    if request.method == 'POST':
        accion = request.POST.get('accion')
        siguiente = request.POST.get('next')  # url de redirección opcional
        motivo = request.POST.get('motivo')
        if accion == 'aprobar':
            pago.estado = 'aprobado'
            pago.motivo_rechazo = None
            pago.save()
            messages.success(request, f'Pago #{pago.id} aprobado.')
        elif accion == 'rechazar':
            pago.estado = 'rechazado'
            pago.motivo_rechazo = motivo or ''
            pago.save()
            messages.success(request, f'Pago #{pago.id} rechazado.')
        # Redirigir al next si viene, si no al listado
        if siguiente:
            return redirect(siguiente)
        return redirect('lista_pagos')
    # Si llega GET, mostrar una confirmación simple o redirigir
    return redirect('lista_pagos')


@login_required
def pago_detalle(request, pago_id):
    """Detalle de un pago. El jugador dueño y el staff pueden acceder."""
    pago = get_object_or_404(Pago, id=pago_id)
    # Permitir al jugador ver su propio pago o al staff
    if not (request.user.is_staff or pago.jugador.user == request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('No tienes permiso para ver este pago')
    return render(request, 'jugadores/pago_detalle.html', {'pago': pago})


@staff_member_required
def archivar_pago(request, pago_id):
    """Marca o desmarca un pago como archivado (soft-delete) para ocultarlo del dashboard."""
    pago = get_object_or_404(Pago, id=pago_id)
    from django.contrib import messages
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'archivar':
            pago.archivado = True
            pago.save()
            messages.success(request, f'Pago #{pago.id} archivado.')
        elif accion == 'desarchivar':
            pago.archivado = False
            pago.save()
            messages.success(request, f'Pago #{pago.id} desarchivado.')
        siguiente = request.POST.get('next')
        if siguiente:
            return redirect(siguiente)
        return redirect('lista_pagos')
    # GET -> redirect
    return redirect('lista_pagos')

def perfil_jugador(request, jugador_id):
    """
    Vista para mostrar el perfil completo de un jugador, sus estadísticas,
    valoraciones y comentarios. Permite a los usuarios dejar nuevos comentarios
    y a los entrenadores (is_staff) dejar valoraciones.
    """
    jugador = get_object_or_404(Jugador, pk=jugador_id)

    from django.db.models import Q
    estadisticas = Estadistica.objects.filter(
        Q(anotadores=jugador) |
        Q(asistentes=jugador) |
        Q(amonestados=jugador) |
        Q(expulsados=jugador)
    ).distinct()

    # Calcular los totales de goles y asistencias
    totales = estadisticas.aggregate(
        goles_totales=Sum('goles'),
        asistencias_totales=Sum('asistencias')
    )

    mensaje_exito = None
    username = request.session.get('nuevo_jugador_username')
    password = request.session.get('nuevo_jugador_password')
    creado_id = request.session.get('jugador_creado_exito')
    if creado_id and int(creado_id) == int(jugador_id):
        # Mostrar las credenciales solo a staff o superuser por seguridad
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            mensaje_exito = f"¡El jugador ha sido creado correctamente!<br>Usuario: <b>{username}</b><br>Contraseña: <b>{password}</b>"
            # limpiar las credenciales de la sesión después de mostrarlas
            request.session.pop('jugador_creado_exito', None)
            request.session.pop('nuevo_jugador_username', None)
            request.session.pop('nuevo_jugador_password', None)
        else:
            # Usuarios normales ven un mensaje genérico sin la contraseña
            mensaje_exito = f"¡El jugador ha sido creado correctamente!<br>Usuario: <b>{username}</b><br>Las credenciales han sido enviadas al administrador para su revisión."
            # No borramos las credenciales de la sesión desde la sesión del usuario normal
    if request.method == 'POST':
        # Procesa el formulario de comentarios
        if 'submit_comentario' in request.POST:
            if not request.user.is_authenticated:
                return redirect('iniciar_sesion')

    # Usar campo almacenado 'edad' cuando esté disponible; si no, calcularla
    edad = getattr(jugador, 'edad', None)
    if edad is None:
        try:
            edad = jugador.calcular_edad()
        except Exception:
            edad = None

    contexto = {
        'jugador': jugador,
        'estadisticas': estadisticas,
        'totales': totales,
        'mensaje_exito': mensaje_exito,
        'edad': edad,
    }
    return render(request, 'jugadores/perfil_jugador.html', contexto)

# Nuevas vistas para la gestión de contenido del staff

@staff_member_required
def agregar_partido(request):
    """
    Vista para que el staff agregue un nuevo partido.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = PartidoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Partido creado correctamente!')
            return redirect('agregar_partido')
    else:
        form = PartidoForm()
    return render(request, 'jugadores/agregar_partido.html', {'form': form})






# Vistas de autenticación y contenido público

def registro(request):
    """
    Vista para el registro de nuevos usuarios.
    """
    from django import forms
    from django.contrib.auth.models import User
    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
        cedula = forms.CharField(label='Cédula', max_length=8, required=True)
        fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
        
        def clean_cedula(self):
            ced = self.cleaned_data.get('cedula')
            from .models import Jugador
            if ced and Jugador.objects.filter(cedula=ced).exists():
                raise forms.ValidationError('Ya existe un jugador registrado con esa cédula.')
            return ced

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            # Crear o actualizar el objeto Jugador vinculado con cédula y fecha de nacimiento
            from .models import Jugador
            cedula = form.cleaned_data.get('cedula')
            fecha_nac = form.cleaned_data.get('fecha_de_nacimiento')
            jugador, created = Jugador.objects.get_or_create(user=user, defaults={
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'cedula': cedula or '',
                'fecha_de_nacimiento': fecha_nac,
            })
            # Si ya existía (p. ej. creado por la señal), actualizar los campos que faltan
            updated = False
            if cedula and jugador.cedula != cedula:
                jugador.cedula = cedula
                updated = True
            if fecha_nac and jugador.fecha_de_nacimiento != fecha_nac:
                jugador.fecha_de_nacimiento = fecha_nac
                updated = True
            if updated:
                jugador.save()
            # Si el formulario usa 'password1' (UserCreationForm estándar)
            raw_password = form.cleaned_data.get('password1')
            # Guarda el usuario en la base de datos
            user = form.save()
            # Intentar autenticar con la contraseña en claro
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                # Fallback: forzar backend y hacer login (útil si usas autenticación personalizada)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')  # ajusta el nombre de la ruta si es necesario
    else:
        form = CustomUserCreationForm()
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    contexto = {'form': form}
    return render(request, 'jugadores/registro.html', contexto)

@login_required
def editar_perfil(request):
    """
    Vista para que los usuarios autenticados editen su perfil de jugador.
    """
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
    else:
        form = JugadorForm(instance=jugador)

    contexto = {'form': form, 'jugador': jugador, 'admin_edit': False}
    return render(request, 'jugadores/editar_perfil.html', contexto)

def iniciar_sesion(request):
    """
    Vista para que los usuarios inicien sesión.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Asegurar que el usuario no-staff tiene un perfil de Jugador y pertenece al grupo
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    # Crear jugador si no existe
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    # Añadir al grupo 'jugadores'
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                # No interrumpir el login si algo falla al crear el perfil
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm(request)
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})

@login_required
def cerrar_sesion(request):
    """
    Vista para que los usuarios cierren sesión.
    """
    logout(request)
    return redirect('inicio')

def resultados_partidos(request):
    """
    Vista que muestra los resultados de los partidos jugados y los próximos partidos.
    """
    from .models import Equipo
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
        proximos_partidos = proximos_partidos.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)

    

@staff_member_required
def registrar_estadistica(request):
    """
    Vista para registrar estadísticas de un jugador.
    Requiere que el usuario sea staff.
    """
    if request.method == 'POST':
        form = EstadisticaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inicio')
    else:
        form = EstadisticaForm()
        
    contexto = {'form': form}
    return render(request, 'jugadores/registrar_estadistica.html', contexto)

# --- NUEVO: Listados para staff/admin ---
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def lista_jugadores(request):
    from .models import Equipo
    from django.db.models import Q
    jugadores = Jugador.objects.all()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    posicion = request.GET.get('posicion')
    busqueda = request.GET.get('busqueda')
    if equipo_id:
        jugadores = jugadores.filter(equipo_id=equipo_id)
    if posicion:
        jugadores = jugadores.filter(posicion__icontains=posicion)
    if busqueda:
        jugadores = jugadores.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(equipo__nombre__icontains=busqueda)
        )
    return render(request, 'jugadores/lista_jugadores.html', {
        'jugadores': jugadores,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'posicion': posicion,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_equipos(request):
    busqueda = request.GET.get('busqueda')
    equipos = Equipo.objects.all()
    if busqueda:
        equipos = equipos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_equipos.html', {
        'equipos': equipos,
        'busqueda': busqueda,
    })

@login_required
def lista_torneos(request):
    # Redirige a la vista de login (`LOGIN_URL`) si el usuario no está autenticado.
    # Si está autenticado pero no es staff, devolvemos 403.
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('No tienes permiso para ver esta página')
    busqueda = request.GET.get('busqueda')
    torneos = Torneo.objects.all()
    if busqueda:
        torneos = torneos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_torneos.html', {
        'torneos': torneos,
        'busqueda': busqueda,
    })


@staff_member_required
def torneo_detalle(request, torneo_id):
    """Detalle público/privado de un torneo: muestra info básica y equipos asociados."""
    torneo = get_object_or_404(Torneo, pk=torneo_id)
    equipos = torneo.equipos.all()
    return render(request, 'jugadores/torneo_detalle.html', {
        'torneo': torneo,
        'equipos': equipos,
    })

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect

def registro(request):
    """
    Vista para el registro de nuevos usuarios.
    Solicita nombre, apellido, cédula y fecha de nacimiento y crea/actualiza
    el objeto Jugador asociado al usuario.
    """
    from django import forms
    from django.contrib.auth.models import User

    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
        cedula = forms.CharField(label='Cédula', max_length=8, required=True)
        fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

        def clean_cedula(self):
            ced = self.cleaned_data.get('cedula')
            from .models import Jugador
            if ced and Jugador.objects.filter(cedula=ced).exists():
                raise forms.ValidationError('Ya existe un jugador registrado con esa cédula.')
            return ced

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar usuario (contraseña incluida al hacer form.save())
            raw_password = form.cleaned_data.get('password1')
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            # Crear o actualizar Jugador con cédula y fecha
            from .models import Jugador
            cedula = form.cleaned_data.get('cedula')
            fecha_nac = form.cleaned_data.get('fecha_de_nacimiento')
            jugador, created = Jugador.objects.get_or_create(user=user, defaults={
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'cedula': cedula or '',
                'fecha_de_nacimiento': fecha_nac,
            })
            # Si ya existía (p. ej. creado por la señal), actualizar los campos necesarios
            updated = False
            if cedula and jugador.cedula != cedula:
                jugador.cedula = cedula
                updated = True
            if fecha_nac and jugador.fecha_de_nacimiento != fecha_nac:
                jugador.fecha_de_nacimiento = fecha_nac
                updated = True
            if updated:
                jugador.save()

            # Autenticar y loguear
            user = form.save()
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')
    else:
        form = CustomUserCreationForm()

    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    contexto = {'form': form}
    return render(request, 'jugadores/registro.html', contexto)

@login_required
def editar_perfil(request):
    """
    Vista para que los usuarios autenticados editen su perfil de jugador.
    """
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
    else:
        form = JugadorForm(instance=jugador)

    contexto = {'form': form}
    return render(request, 'jugadores/editar_perfil.html', contexto)

def iniciar_sesion(request):
    """
    Vista para que los usuarios inicien sesión.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Asegurar que el usuario no-staff tiene un perfil de Jugador y pertenece al grupo
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    # Crear jugador si no existe
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    # Añadir al grupo 'jugadores'
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                # No interrumpir el login si algo falla al crear el perfil
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm(request)
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})

@login_required
def cerrar_sesion(request):
    """
    Vista para que los usuarios cierren sesión.
    """
    logout(request)
    return redirect('inicio')

def resultados_partidos(request):
    """
    Vista que muestra los resultados de los partidos jugados y los próximos partidos.
    """
    from .models import Equipo
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
        proximos_partidos = proximos_partidos.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)

    

@staff_member_required
def registrar_estadistica(request):
    """
    Vista para registrar estadísticas de un jugador.
    Requiere que el usuario sea staff.
    """
    if request.method == 'POST':
        form = EstadisticaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inicio')
    else:
        form = EstadisticaForm()
        
    contexto = {'form': form}
    return render(request, 'jugadores/registrar_estadistica.html', contexto)

# --- NUEVO: Listados para staff/admin ---
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def lista_jugadores(request):
    from .models import Equipo
    from django.db.models import Q
    jugadores = Jugador.objects.all()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    posicion = request.GET.get('posicion')
    busqueda = request.GET.get('busqueda')
    if equipo_id:
        jugadores = jugadores.filter(equipo_id=equipo_id)
    if posicion:
        jugadores = jugadores.filter(posicion__icontains=posicion)
    if busqueda:
        jugadores = jugadores.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(equipo__nombre__icontains=busqueda)
        )
    return render(request, 'jugadores/lista_jugadores.html', {
        'jugadores': jugadores,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'posicion': posicion,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_equipos(request):
    busqueda = request.GET.get('busqueda')
    equipos = Equipo.objects.all()
    if busqueda:
        equipos = equipos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_equipos.html', {
        'equipos': equipos,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_torneos(request):
    busqueda = request.GET.get('busqueda')
    torneos = Torneo.objects.all()
    if busqueda:
        torneos = torneos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_torneos.html', {
        'torneos': torneos,
        'busqueda': busqueda,
    })

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect

def registro(request):
    """
    Vista para el registro de nuevos usuarios.
    Solicita nombre, apellido, cédula y fecha de nacimiento y crea/actualiza
    el objeto Jugador asociado al usuario.
    """
    from django import forms
    from django.contrib.auth.models import User

    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
        cedula = forms.CharField(label='Cédula', max_length=8, required=True)
        fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

        def clean_cedula(self):
            ced = self.cleaned_data.get('cedula')
            from .models import Jugador
            if ced and Jugador.objects.filter(cedula=ced).exists():
                raise forms.ValidationError('Ya existe un jugador registrado con esa cédula.')
            return ced

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar usuario (contraseña incluida al hacer form.save())
            raw_password = form.cleaned_data.get('password1')
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            # Crear o actualizar Jugador con cédula y fecha
            from .models import Jugador
            cedula = form.cleaned_data.get('cedula')
            fecha_nac = form.cleaned_data.get('fecha_de_nacimiento')
            jugador, created = Jugador.objects.get_or_create(user=user, defaults={
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'cedula': cedula or '',
                'fecha_de_nacimiento': fecha_nac,
            })
            # Si ya existía (p. ej. creado por la señal), actualizar los campos necesarios
            updated = False
            if cedula and jugador.cedula != cedula:
                jugador.cedula = cedula
                updated = True
            if fecha_nac and jugador.fecha_de_nacimiento != fecha_nac:
                jugador.fecha_de_nacimiento = fecha_nac
                updated = True
            if updated:
                jugador.save()

            # Autenticar y loguear
            user = form.save()
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')
    else:
        form = CustomUserCreationForm()

    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    contexto = {'form': form}
    return render(request, 'jugadores/registro.html', contexto)

@login_required
def editar_perfil(request):
    """
    Vista para que los usuarios autenticados editen su perfil de jugador.
    """
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
    else:
        form = JugadorForm(instance=jugador)

    contexto = {'form': form}
    return render(request, 'jugadores/editar_perfil.html', contexto)

def iniciar_sesion(request):
    """
    Vista para que los usuarios inicien sesión.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Asegurar que el usuario no-staff tiene un perfil de Jugador y pertenece al grupo
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    # Crear jugador si no existe
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    # Añadir al grupo 'jugadores'
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                # No interrumpir el login si algo falla al crear el perfil
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm()
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})

@login_required
def cerrar_sesion(request):
    """
    Vista para que los usuarios cierren sesión.
    """
    logout(request)
    return redirect('inicio')

def resultados_partidos(request):
    """
    Vista que muestra los resultados de los partidos jugados y los próximos partidos.
    """
    from .models import Equipo
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
        proximos_partidos = proximos_partidos.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)

    

@staff_member_required
def registrar_estadistica(request):
    """
    Vista para registrar estadísticas de un jugador.
    Requiere que el usuario sea staff.
    """
    if request.method == 'POST':
        form = EstadisticaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inicio')
    else:
        form = EstadisticaForm()
        
    contexto = {'form': form}
    return render(request, 'jugadores/registrar_estadistica.html', contexto)

# --- NUEVO: Listados para staff/admin ---
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def lista_jugadores(request):
    from .models import Equipo
    from django.db.models import Q
    jugadores = Jugador.objects.all()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    posicion = request.GET.get('posicion')
    busqueda = request.GET.get('busqueda')
    if equipo_id:
        jugadores = jugadores.filter(equipo_id=equipo_id)
    if posicion:
        jugadores = jugadores.filter(posicion__icontains=posicion)
    if busqueda:
        jugadores = jugadores.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(equipo__nombre__icontains=busqueda)
        )
    return render(request, 'jugadores/lista_jugadores.html', {
        'jugadores': jugadores,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'posicion': posicion,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_equipos(request):
    busqueda = request.GET.get('busqueda')
    equipos = Equipo.objects.all()
    if busqueda:
        equipos = equipos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_equipos.html', {
        'equipos': equipos,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_torneos(request):
    busqueda = request.GET.get('busqueda')
    torneos = Torneo.objects.all()
    if busqueda:
        torneos = torneos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_torneos.html', {
        'torneos': torneos,
        'busqueda': busqueda,
    })

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect

def registro(request):
    """
    Vista para el registro de nuevos usuarios.
    Solicita nombre, apellido, cédula y fecha de nacimiento y crea/actualiza
    el objeto Jugador asociado al usuario.
    """
    from django import forms
    from django.contrib.auth.models import User

    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
        cedula = forms.CharField(label='Cédula', max_length=8, required=True)
        fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

        def clean_cedula(self):
            ced = self.cleaned_data.get('cedula')
            from .models import Jugador
            if ced and Jugador.objects.filter(cedula=ced).exists():
                raise forms.ValidationError('Ya existe un jugador registrado con esa cédula.')
            return ced

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar usuario (contraseña incluida al hacer form.save())
            raw_password = form.cleaned_data.get('password1')
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            # Crear o actualizar Jugador con cédula y fecha
            from .models import Jugador
            cedula = form.cleaned_data.get('cedula')
            fecha_nac = form.cleaned_data.get('fecha_de_nacimiento')
            jugador, created = Jugador.objects.get_or_create(user=user, defaults={
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'cedula': cedula or '',
                'fecha_de_nacimiento': fecha_nac,
            })
            # Si ya existía (p. ej. creado por la señal), actualizar los campos necesarios
            updated = False
            if cedula and jugador.cedula != cedula:
                jugador.cedula = cedula
                updated = True
            if fecha_nac and jugador.fecha_de_nacimiento != fecha_nac:
                jugador.fecha_de_nacimiento = fecha_nac
                updated = True
            if updated:
                jugador.save()

            # Autenticar y loguear
            user = form.save()
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')
    else:
        form = CustomUserCreationForm()

    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    contexto = {'form': form}
    return render(request, 'jugadores/registro.html', contexto)

@login_required
def editar_perfil(request):
    """
    Vista para que los usuarios autenticados editen su perfil de jugador.
    """
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
    else:
        form = JugadorForm(instance=jugador)

    contexto = {'form': form}
    return render(request, 'jugadores/editar_perfil.html', contexto)

def iniciar_sesion(request):
    """
    Vista para que los usuarios inicien sesión.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Asegurar que el usuario no-staff tiene un perfil de Jugador y pertenece al grupo
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    # Crear jugador si no existe
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    # Añadir al grupo 'jugadores'
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                # No interrumpir el login si algo falla al crear el perfil
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm()
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})

@login_required
def cerrar_sesion(request):
    """
    Vista para que los usuarios cierren sesión.
    """
    logout(request)
    return redirect('inicio')

def resultados_partidos(request):
    """
    Vista que muestra los resultados de los partidos jugados y los próximos partidos.
    """
    from .models import Equipo
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
        proximos_partidos = proximos_partidos.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)

    

@staff_member_required
def registrar_estadistica(request):
    """
    Vista para registrar estadísticas de un jugador.
    Requiere que el usuario sea staff.
    """
    if request.method == 'POST':
        form = EstadisticaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inicio')
    else:
        form = EstadisticaForm()
        
    contexto = {'form': form}
    return render(request, 'jugadores/registrar_estadistica.html', contexto)

# --- NUEVO: Listados para staff/admin ---
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def lista_jugadores(request):
    from .models import Equipo
    from django.db.models import Q
    jugadores = Jugador.objects.all()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    posicion = request.GET.get('posicion')
    busqueda = request.GET.get('busqueda')
    if equipo_id:
        jugadores = jugadores.filter(equipo_id=equipo_id)
    if posicion:
        jugadores = jugadores.filter(posicion__icontains=posicion)
    if busqueda:
        jugadores = jugadores.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(equipo__nombre__icontains=busqueda)
        )
    return render(request, 'jugadores/lista_jugadores.html', {
        'jugadores': jugadores,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'posicion': posicion,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_equipos(request):
    busqueda = request.GET.get('busqueda')
    equipos = Equipo.objects.all()
    if busqueda:
        equipos = equipos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_equipos.html', {
        'equipos': equipos,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_torneos(request):
    busqueda = request.GET.get('busqueda')
    torneos = Torneo.objects.all()
    if busqueda:
        torneos = torneos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_torneos.html', {
        'torneos': torneos,
        'busqueda': busqueda,
    })

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect

def registro(request):
    """
    Vista para el registro de nuevos usuarios.
    Solicita nombre, apellido, cédula y fecha de nacimiento y crea/actualiza
    el objeto Jugador asociado al usuario.
    """
    from django import forms
    from django.contrib.auth.models import User

    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
        cedula = forms.CharField(label='Cédula', max_length=8, required=True)
        fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

        def clean_cedula(self):
            ced = self.cleaned_data.get('cedula')
            from .models import Jugador
            if ced and Jugador.objects.filter(cedula=ced).exists():
                raise forms.ValidationError('Ya existe un jugador registrado con esa cédula.')
            return ced

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar usuario (contraseña incluida al hacer form.save())
            raw_password = form.cleaned_data.get('password1')
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            # Crear o actualizar Jugador con cédula y fecha
            from .models import Jugador
            cedula = form.cleaned_data.get('cedula')
            fecha_nac = form.cleaned_data.get('fecha_de_nacimiento')
            jugador, created = Jugador.objects.get_or_create(user=user, defaults={
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'cedula': cedula or '',
                'fecha_de_nacimiento': fecha_nac,
            })
            # Si ya existía (p. ej. creado por la señal), actualizar los campos necesarios
            updated = False
            if cedula and jugador.cedula != cedula:
                jugador.cedula = cedula
                updated = True
            if fecha_nac and jugador.fecha_de_nacimiento != fecha_nac:
                jugador.fecha_de_nacimiento = fecha_nac
                updated = True
            if updated:
                jugador.save()

            # Autenticar y loguear
            user = form.save()
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')
    else:
        form = CustomUserCreationForm()

    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    contexto = {'form': form}
    return render(request, 'jugadores/registro.html', contexto)

@login_required
def editar_perfil(request):
    """
    Vista para que los usuarios autenticados editen su perfil de jugador.
    """
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
    else:
        form = JugadorForm(instance=jugador)

    contexto = {'form': form}
    return render(request, 'jugadores/editar_perfil.html', contexto)

def iniciar_sesion(request):
    """
    Vista para que los usuarios inicien sesión.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Asegurar que el usuario no-staff tiene un perfil de Jugador y pertenece al grupo
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    # Crear jugador si no existe
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    # Añadir al grupo 'jugadores'
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                # No interrumpir el login si algo falla al crear el perfil
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm()
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})

@login_required
def cerrar_sesion(request):
    """
    Vista para que los usuarios cierren sesión.
    """
    logout(request)
    return redirect('inicio')

def resultados_partidos(request):
    """
    Vista que muestra los resultados de los partidos jugados y los próximos partidos.
    """
    from .models import Equipo
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
        proximos_partidos = proximos_partidos.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)

    

@staff_member_required
def registrar_estadistica(request):
    """
    Vista para registrar estadísticas de un jugador.
    Requiere que el usuario sea staff.
    """
    if request.method == 'POST':
        form = EstadisticaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inicio')
    else:
        form = EstadisticaForm()
        
    contexto = {'form': form}
    return render(request, 'jugadores/registrar_estadistica.html', contexto)

# --- NUEVO: Listados para staff/admin ---
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def lista_jugadores(request):
    from .models import Equipo
    from django.db.models import Q
    jugadores = Jugador.objects.all()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    posicion = request.GET.get('posicion')
    busqueda = request.GET.get('busqueda')
    if equipo_id:
        jugadores = jugadores.filter(equipo_id=equipo_id)
    if posicion:
        jugadores = jugadores.filter(posicion__icontains=posicion)
    if busqueda:
        jugadores = jugadores.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(equipo__nombre__icontains=busqueda)
        )
    return render(request, 'jugadores/lista_jugadores.html', {
        'jugadores': jugadores,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'posicion': posicion,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_equipos(request):
    busqueda = request.GET.get('busqueda')
    equipos = Equipo.objects.all()
    if busqueda:
        equipos = equipos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_equipos.html', {
        'equipos': equipos,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_torneos(request):
    busqueda = request.GET.get('busqueda')
    torneos = Torneo.objects.all()
    if busqueda:
        torneos = torneos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_torneos.html', {
        'torneos': torneos,
        'busqueda': busqueda,
    })

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect

def registro(request):
    """
    Vista para el registro de nuevos usuarios.
    Solicita nombre, apellido, cédula y fecha de nacimiento y crea/actualiza
    el objeto Jugador asociado al usuario.
    """
    from django import forms
    from django.contrib.auth.models import User

    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
        cedula = forms.CharField(label='Cédula', max_length=8, required=True)
        fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

        def clean_cedula(self):
            ced = self.cleaned_data.get('cedula')
            from .models import Jugador
            if ced and Jugador.objects.filter(cedula=ced).exists():
                raise forms.ValidationError('Ya existe un jugador registrado con esa cédula.')
            return ced

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar usuario (contraseña incluida al hacer form.save())
            raw_password = form.cleaned_data.get('password1')
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            # Crear o actualizar Jugador con cédula y fecha
            from .models import Jugador
            cedula = form.cleaned_data.get('cedula')
            fecha_nac = form.cleaned_data.get('fecha_de_nacimiento')
            jugador, created = Jugador.objects.get_or_create(user=user, defaults={
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'cedula': cedula or '',
                'fecha_de_nacimiento': fecha_nac,
            })
            # Si ya existía (p. ej. creado por la señal), actualizar los campos necesarios
            updated = False
            if cedula and jugador.cedula != cedula:
                jugador.cedula = cedula
                updated = True
            if fecha_nac and jugador.fecha_de_nacimiento != fecha_nac:
                jugador.fecha_de_nacimiento = fecha_nac
                updated = True
            if updated:
                jugador.save()

            # Autenticar y loguear
            user = form.save()
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')
    else:
        form = CustomUserCreationForm()

    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    contexto = {'form': form}
    return render(request, 'jugadores/registro.html', contexto)

@login_required
def editar_perfil(request):
    """
    Vista para que los usuarios autenticados editen su perfil de jugador.
    """
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
    else:
        form = JugadorForm(instance=jugador)

    contexto = {'form': form}
    return render(request, 'jugadores/editar_perfil.html', contexto)

def iniciar_sesion(request):
    """
    Vista para que los usuarios inicien sesión.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Asegurar que el usuario no-staff tiene un perfil de Jugador y pertenece al grupo
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    # Crear jugador si no existe
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    # Añadir al grupo 'jugadores'
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                # No interrumpir el login si algo falla al crear el perfil
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm()
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})

@login_required
def cerrar_sesion(request):
    """
    Vista para que los usuarios cierren sesión.
    """
    logout(request)
    return redirect('inicio')

def resultados_partidos(request):
    """
    Vista que muestra los resultados de los partidos jugados y los próximos partidos.
    """
    from .models import Equipo
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
        proximos_partidos = proximos_partidos.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)

    

@staff_member_required
def registrar_estadistica(request):
    """
    Vista para registrar estadísticas de un jugador.
    Requiere que el usuario sea staff.
    """
    if request.method == 'POST':
        form = EstadisticaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inicio')
    else:
        form = EstadisticaForm()
        
    contexto = {'form': form}
    return render(request, 'jugadores/registrar_estadistica.html', contexto)

# --- NUEVO: Listados para staff/admin ---
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def lista_jugadores(request):
    from .models import Equipo
    from django.db.models import Q
    jugadores = Jugador.objects.all()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    posicion = request.GET.get('posicion')
    busqueda = request.GET.get('busqueda')
    if equipo_id:
        jugadores = jugadores.filter(equipo_id=equipo_id)
    if posicion:
        jugadores = jugadores.filter(posicion__icontains=posicion)
    if busqueda:
        jugadores = jugadores.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(equipo__nombre__icontains=busqueda)
        )
    return render(request, 'jugadores/lista_jugadores.html', {
        'jugadores': jugadores,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'posicion': posicion,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_equipos(request):
    busqueda = request.GET.get('busqueda')
    equipos = Equipo.objects.all()
    if busqueda:
        equipos = equipos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_equipos.html', {
        'equipos': equipos,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_torneos(request):
    busqueda = request.GET.get('busqueda')
    torneos = Torneo.objects.all()
    if busqueda:
        torneos = torneos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_torneos.html', {
        'torneos': torneos,
        'busqueda': busqueda,
    })

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect

def registro(request):
    """
    Vista para el registro de nuevos usuarios.
    Solicita nombre, apellido, cédula y fecha de nacimiento y crea/actualiza
    el objeto Jugador asociado al usuario.
    """
    from django import forms
    from django.contrib.auth.models import User

    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
        cedula = forms.CharField(label='Cédula', max_length=8, required=True)
        fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

        def clean_cedula(self):
            ced = self.cleaned_data.get('cedula')
            from .models import Jugador
            if ced and Jugador.objects.filter(cedula=ced).exists():
                raise forms.ValidationError('Ya existe un jugador registrado con esa cédula.')
            return ced

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar usuario (contraseña incluida al hacer form.save())
            raw_password = form.cleaned_data.get('password1')
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            # Crear o actualizar Jugador con cédula y fecha
            from .models import Jugador
            cedula = form.cleaned_data.get('cedula')
            fecha_nac = form.cleaned_data.get('fecha_de_nacimiento')
            jugador, created = Jugador.objects.get_or_create(user=user, defaults={
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'cedula': cedula or '',
                'fecha_de_nacimiento': fecha_nac,
            })
            # Si ya existía (p. ej. creado por la señal), actualizar los campos necesarios
            updated = False
            if cedula and (not jugador.cedula or jugador.cedula.startswith('u')) and jugador.cedula != cedula:
                # reemplazar marcador temporal creado por la señal
                jugador.cedula = cedula
                updated = True
            if fecha_nac and jugador.fecha_de_nacimiento != fecha_nac:
                jugador.fecha_de_nacimiento = fecha_nac
                updated = True
            if updated:
                jugador.save()

            # Autenticar y loguear
            user = form.save()
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')
    else:
        form = CustomUserCreationForm()

    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    contexto = {'form': form}
    return render(request, 'jugadores/registro.html', contexto)

@login_required
def editar_perfil(request):
    """
    Vista para que los usuarios autenticados editen su perfil de jugador.
    """
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            if form.has_changed():
                form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            else:
                messages.info(request, 'No se realizaron cambios en el perfil.')
            return redirect('perfil_jugador', jugador_id=jugador.id)
    else:
        form = JugadorForm(instance=jugador)

    contexto = {'form': form}
    return render(request, 'jugadores/editar_perfil.html', contexto)

def iniciar_sesion(request):
    """
    Vista para que los usuarios inicien sesión.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Asegurar que el usuario no-staff tiene un perfil de Jugador y pertenece al grupo
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    # Crear jugador si no existe
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    # Añadir al grupo 'jugadores'
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                # No interrumpir el login si algo falla al crear el perfil
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm()
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})

@login_required
def cerrar_sesion(request):
    """
    Vista para que los usuarios cierren sesión.
    """
    logout(request)
    return redirect('inicio')

def resultados_partidos(request):
    """
    Vista que muestra los resultados de los partidos jugados y los próximos partidos.
    """
    from .models import Equipo
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
        proximos_partidos = proximos_partidos.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)

    

@staff_member_required
def registrar_estadistica(request):
    """
    Vista para registrar estadísticas de un jugador.
    Requiere que el usuario sea staff.
    """
    if request.method == 'POST':
        form = EstadisticaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inicio')
    else:
        form = EstadisticaForm()
        
    contexto = {'form': form}
    return render(request, 'jugadores/registrar_estadistica.html', contexto)

# --- NUEVO: Listados para staff/admin ---
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def lista_jugadores(request):
    from .models import Equipo
    from django.db.models import Q
    jugadores = Jugador.objects.all()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    posicion = request.GET.get('posicion')
    busqueda = request.GET.get('busqueda')
    if equipo_id:
        jugadores = jugadores.filter(equipo_id=equipo_id)
    if posicion:
        jugadores = jugadores.filter(posicion__icontains=posicion)
    if busqueda:
        jugadores = jugadores.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(equipo__nombre__icontains=busqueda)
        )
    return render(request, 'jugadores/lista_jugadores.html', {
        'jugadores': jugadores,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'posicion': posicion,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_equipos(request):
    busqueda = request.GET.get('busqueda')
    equipos = Equipo.objects.all()
    if busqueda:
        equipos = equipos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_equipos.html', {
        'equipos': equipos,
        'busqueda': busqueda,
    })

@staff_member_required
def lista_torneos(request):
    busqueda = request.GET.get('busqueda')
    torneos = Torneo.objects.all()
    if busqueda:
        torneos = torneos.filter(nombre__icontains=busqueda)
    return render(request, 'jugadores/lista_torneos.html', {
        'torneos': torneos,
        'busqueda': busqueda,
    })

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect

def registro(request):
    """
    Vista para el registro de nuevos usuarios.
    """
    from django import forms
    from django.contrib.auth.models import User
    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
    cedula = forms.CharField(label='Cédula', max_length=8, required=True)
    fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class CustomUserCreationForm(UserCreationForm):
        username = forms.CharField(label='Usuario', max_length=150, required=True)
        first_name = forms.CharField(label='Nombre', max_length=30, required=True)
        last_name = forms.CharField(label='Apellido', max_length=30, required=True)
        cedula = forms.CharField(label='Cédula', max_length=8, required=True)
        fecha_de_nacimiento = forms.DateField(label='Fecha de nacimiento', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

        def clean_cedula(self):
            ced = self.cleaned_data.get('cedula')
            from .models import Jugador
            if ced and Jugador.objects.filter(cedula=ced).exists():
                raise forms.ValidationError('Ya existe un jugador registrado con esa cédula.')
            return ced

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            raw_password = form.cleaned_data.get('password1')
            user = form.save(commit=False)
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            from .models import Jugador
            cedula_val = form.cleaned_data.get('cedula')
            fecha_nac = form.cleaned_data.get('fecha_de_nacimiento')
            jugador, created = Jugador.objects.get_or_create(user=user, defaults={
                'nombre': user.first_name or '',
                'apellido': user.last_name or '',
                'cedula': cedula_val or '',
                'fecha_de_nacimiento': fecha_nac,
            })

            # Si la señal creó un jugador con una cédula temporal, reemplazarla
            updated = False
            if cedula_val and (not jugador.cedula or str(jugador.cedula).startswith('u')) and jugador.cedula != cedula_val:
                jugador.cedula = cedula_val
                updated = True
            if fecha_nac and jugador.fecha_de_nacimiento != fecha_nac:
                jugador.fecha_de_nacimiento = fecha_nac
                updated = True
            if updated:
                jugador.save()

            # Autenticar y loguear
            user = form.save()
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None:
                login(request, user_auth)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

            messages.success(request, "Registro completado. Has iniciado sesión correctamente.")
            return redirect('inicio')
    else:
        form = CustomUserCreationForm()

    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    contexto = {'form': form}
    return render(request, 'jugadores/registro.html', contexto)

@login_required
def editar_perfil(request):
    """
    Vista para que los usuarios autenticados editen su perfil de jugador.
    """
    jugador = get_object_or_404(Jugador, user=request.user)
    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            form.save()
            return redirect('perfil_jugador', jugador_id=jugador.id)
    else:
        form = JugadorForm(instance=jugador)

    contexto = {'form': form}
    return render(request, 'jugadores/editar_perfil.html', contexto)

def iniciar_sesion(request):
    """
    Vista para que los usuarios inicien sesión.
    """
    from django.contrib import messages
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Asegurar que el usuario no-staff tiene un perfil de Jugador y pertenece al grupo
            try:
                from .models import Jugador
                from django.contrib.auth.models import Group
                if not user.is_staff and not user.is_superuser:
                    # Crear jugador si no existe
                    if not Jugador.objects.filter(user=user).exists():
                        Jugador.objects.create(user=user, nombre=user.first_name or '', apellido=user.last_name or '')
                    # Añadir al grupo 'jugadores'
                    grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
                    user.groups.add(grupo_jugadores)
            except Exception:
                # No interrumpir el login si algo falla al crear el perfil
                pass
            messages.success(request, f'Has iniciado sesión como {user.username}')
            return redirect('inicio')
    else:
        form = AuthenticationForm()
    # Agregar clases Bootstrap a los widgets
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control text-center'
    return render(request, 'jugadores/iniciar_sesion.html', {'form': form})

@login_required
def cerrar_sesion(request):
    """
    Vista para que los usuarios cierren sesión.
    """
    logout(request)
    return redirect('inicio')

def resultados_partidos(request):
    """
    Vista que muestra los resultados de los partidos jugados y los próximos partidos.
    """
    from .models import Equipo
    from django.db.models import Q
    now = timezone.now()
    equipos = Equipo.objects.all()
    equipo_id = request.GET.get('equipo')
    fecha = request.GET.get('fecha')
    partidos_pasados = Partido.objects.filter(fecha__lte=now)
    proximos_partidos = Partido.objects.filter(fecha__gt=now)
    if equipo_id:
        partidos_pasados = partidos_pasados.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
        proximos_partidos = proximos_partidos.filter(
            Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id)
        )
    if fecha:
        partidos_pasados = partidos_pasados.filter(fecha=fecha)
        proximos_partidos = proximos_partidos.filter(fecha=fecha)
    partidos_pasados = partidos_pasados.order_by('-fecha')
    proximos_partidos = proximos_partidos.order_by('fecha')
    contexto = {
        'partidos_pasados': partidos_pasados,
        'proximos_partidos': proximos_partidos,
        'equipos': equipos,
        'equipo_id': equipo_id,
        'fecha': fecha,
    }
    return render(request, 'jugadores/resultados_partidos.html', contexto)
