
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0003_jugador_foto'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jugador',
            name='activo',
        ),
    ]
