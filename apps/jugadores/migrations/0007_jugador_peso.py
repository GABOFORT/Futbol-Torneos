
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0006_jugador_sexo'),
    ]

    operations = [
        migrations.AddField(
            model_name='jugador',
            name='peso',
            field=models.PositiveSmallIntegerField(blank=True, help_text='Solo hace falta en las categorías que fijan un peso mínimo.', null=True, verbose_name='Peso (kg)'),
        ),
    ]
