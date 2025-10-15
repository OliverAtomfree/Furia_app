# Generated migration: añade el campo `cedula` como nullable para permitir rellenarlo en una migración posterior.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0017_alter_pago_referencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='jugador',
            name='cedula',
            field=models.CharField(blank=True, max_length=8, null=True, unique=True, verbose_name='cédula'),
        ),
    ]
