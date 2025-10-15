from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Jugador

@receiver(post_save, sender=User)
def crear_perfil_jugador(sender, instance, created, **kwargs):
    # Solo crear perfil de Jugador para usuarios normales (no staff ni superuser)
    if created and not instance.is_staff and not instance.is_superuser:
        # Evitar crear duplicados si ya existe (por ejemplo si la vista crea el perfil)
        if not Jugador.objects.filter(user=instance).exists():
            # Use a temporary unique placeholder for `cedula` to avoid
            # UNIQUE constraint collisions (empty string) when the
            # registration view will later set the real cedula.
            # The placeholder is based on the user's PK and guaranteed
            # unique for new users. Ensure it fits the max_length=8.
            temp_cedula = f"u{instance.pk}"
            if len(temp_cedula) > 8:
                temp_cedula = temp_cedula[:8]
            jugador = Jugador.objects.create(
                user=instance,
                nombre=instance.first_name or '',
                apellido=instance.last_name or '',
                cedula=temp_cedula,
            )
        # Añadir al grupo 'jugadores'
        try:
            from django.contrib.auth.models import Group
            grupo_jugadores, _ = Group.objects.get_or_create(name='jugadores')
            instance.groups.add(grupo_jugadores)
        except Exception:
            # Si algo falla con los grupos, no interrumpir la creación del usuario
            pass

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Equipo

# Sincronizar Estadistica <-> Tarjeta
from django.db.models.signals import post_save
from .models import Estadistica, Tarjeta
from django.db.models.signals import m2m_changed

# almacenamiento temporal para pre_clear/post_clear
_pre_clear_cache = {
    'amonestados': {},
    'expulsados': {}
}


@receiver(post_save, sender=Estadistica)
def sincronizar_tarjetas_desde_estadistica(sender, instance, created, **kwargs):
    """
    Cuando se guarda una Estadistica, crear tarjetas para los jugadores en
    'amonestados' (amarilla) y 'expulsados' (roja) si no existen ya en el partido.
    """
    try:
        partido = instance.partido
        # Amarillas
        for j in instance.amonestados.all():
            # Crear tarjeta amarilla si no existe para este partido/jugador
            if not Tarjeta.objects.filter(partido=partido, jugador=j, tipo='amarilla').exists():
                Tarjeta.objects.create(partido=partido, jugador=j, tipo='amarilla')
        # Rojas
        for j in instance.expulsados.all():
            if not Tarjeta.objects.filter(partido=partido, jugador=j, tipo='roja').exists():
                Tarjeta.objects.create(partido=partido, jugador=j, tipo='roja')
    except Exception:
        # No interrumpir el guardado si algo falla en la sincronización
        pass


@receiver(m2m_changed, sender=Estadistica.amonestados.through)
def amonestados_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Crear tarjetas al añadir amonestados; eliminar tarjetas al remover/clear."""
    try:
        partido = instance.partido
        if action == 'post_add' and pk_set:
            for pk in pk_set:
                    if not Tarjeta.objects.filter(partido=partido, jugador_id=pk, tipo='amarilla', anulada=False).exists():
                        Tarjeta.objects.create(partido=partido, jugador_id=pk, tipo='amarilla', anulada=False)
        elif action == 'post_remove' and pk_set:
            for pk in pk_set:
                    Tarjeta.objects.filter(partido=partido, jugador_id=pk, tipo='amarilla', anulada=False).update(anulada=True)
        elif action == 'pre_clear':
            # guardar los ids actuales antes de limpiar
            ids = list(instance.amonestados.all().values_list('id', flat=True))
            _pre_clear_cache['amonestados'][instance.pk] = ids
        elif action == 'post_clear':
            ids = _pre_clear_cache['amonestados'].pop(instance.pk, [])
            for pk in ids:
                    Tarjeta.objects.filter(partido=partido, jugador_id=pk, tipo='amarilla', anulada=False).update(anulada=True)
    except Exception:
        pass


@receiver(m2m_changed, sender=Estadistica.expulsados.through)
def expulsados_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Crear tarjetas rojas al añadir expulsados; eliminar al remover/clear."""
    try:
        partido = instance.partido
        if action == 'post_add' and pk_set:
            for pk in pk_set:
                    if not Tarjeta.objects.filter(partido=partido, jugador_id=pk, tipo='roja', anulada=False).exists():
                        Tarjeta.objects.create(partido=partido, jugador_id=pk, tipo='roja', anulada=False)
        elif action == 'post_remove' and pk_set:
            for pk in pk_set:
                    Tarjeta.objects.filter(partido=partido, jugador_id=pk, tipo='roja', anulada=False).update(anulada=True)
        elif action == 'pre_clear':
            ids = list(instance.expulsados.all().values_list('id', flat=True))
            _pre_clear_cache['expulsados'][instance.pk] = ids
        elif action == 'post_clear':
            ids = _pre_clear_cache['expulsados'].pop(instance.pk, [])
            for pk in ids:
                    Tarjeta.objects.filter(partido=partido, jugador_id=pk, tipo='roja', anulada=False).update(anulada=True)
    except Exception:
        pass

@receiver(post_migrate)
def create_default_team(sender, **kwargs):
    """
    Crea el equipo predeterminado 'Furia Nocturna FC' si aún no existe.
    Esta función se ejecuta después de cada migración.
    """
    if sender.name == 'jugadores':
        try:
            Equipo.objects.get_or_create(nombre='Furia Nocturna FC')
            print("Equipo 'Furia Nocturna FC' creado o ya existente.")
        except Exception as e:
            print(f"Error al crear el equipo predeterminado: {e}")