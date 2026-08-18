
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0007_jugador_peso'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jugador',
            name='peso',
        ),
    ]
