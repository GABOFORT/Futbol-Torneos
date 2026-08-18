
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0005_jugador_dorsal_unico_por_equipo'),
        ('partidos', '0007_alter_partido_estado'),
    ]

    operations = [
        migrations.CreateModel(
            name='Actuacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('goles', models.PositiveIntegerField(default=0, verbose_name='Goles')),
                ('goles_en_contra', models.PositiveIntegerField(default=0, help_text='Suman al marcador del rival y no cuentan para la tabla de goleo.', verbose_name='Goles en contra')),
                ('asistencias', models.PositiveIntegerField(default=0, verbose_name='Asistencias')),
                ('jugador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actuaciones', to='jugadores.jugador')),
                ('partido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actuaciones', to='partidos.partido')),
            ],
            options={
                'verbose_name': 'Actuación',
                'verbose_name_plural': 'Actuaciones',
                'ordering': ['-goles', '-asistencias'],
                'constraints': [models.UniqueConstraint(fields=('partido', 'jugador'), name='una_actuacion_por_jugador_y_partido', violation_error_message='Ese jugador ya está cargado en este partido.')],
            },
        ),
    ]
