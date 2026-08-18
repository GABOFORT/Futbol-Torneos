
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0002_jugador_estado_jugador_observaciones'),
    ]

    operations = [
        migrations.AddField(
            model_name='jugador',
            name='foto',
            field=models.ImageField(blank=True, null=True, upload_to='jugadores/', verbose_name='Foto'),
        ),
    ]
