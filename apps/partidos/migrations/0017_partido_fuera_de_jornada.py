
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0016_partido_cuadro'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='fuera_de_jornada',
            field=models.BooleanField(default=False, help_text='No pertenece a ninguna jornada. Se juega aparte, cuando los dos equipos puedan.', verbose_name='Partido pendiente'),
        ),
    ]
