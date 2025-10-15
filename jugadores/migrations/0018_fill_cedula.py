# Generated manually to populate cedula for existing Jugador rows
from django.db import migrations


def gen_temp_cedula(player_id):
    # Formato T + 7 dígitos -> longitud 8
    return f"T{player_id:07d}"


def fill_cedula(apps, schema_editor):
    Jugador = apps.get_model('jugadores', 'Jugador')
    from django.db.models import Q
    qs = Jugador.objects.filter(Q(cedula__isnull=True) | Q(cedula=''))
    for p in qs:
        p.cedula = gen_temp_cedula(p.id)
        p.save(update_fields=['cedula'])


def revert_fill_cedula(apps, schema_editor):
    # Restaurar a NULL aquellas cédulas temporales creadas por esta migración
    Jugador = apps.get_model('jugadores', 'Jugador')
    for p in Jugador.objects.all():
        c = getattr(p, 'cedula', None)
        if c and len(c) == 8 and c.startswith('T') and c[1:].isdigit():
            p.cedula = None
            p.save(update_fields=['cedula'])


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0018_add_cedula'),
    ]

    operations = [
        migrations.RunPython(fill_cedula, revert_fill_cedula),
    ]
