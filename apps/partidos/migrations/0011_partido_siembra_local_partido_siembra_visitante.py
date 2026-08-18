
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0010_partido_fase_partido_orden'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='siembra_local',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Siembra del local'),
        ),
        migrations.AddField(
            model_name='partido',
            name='siembra_visitante',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Siembra del visitante'),
        ),
    ]
