# Generated migration to add archivado field to Pago
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0014_alter_pago_metodo_alter_pago_referencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='pago',
            name='archivado',
            field=models.BooleanField(default=False),
        ),
    ]
