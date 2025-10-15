# Migration to make cedula field required (non-nullable)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0018_fill_cedula'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jugador',
            name='cedula',
            field=models.CharField(max_length=8, unique=True, verbose_name='cédula'),
        ),
    ]
