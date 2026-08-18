
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('equipos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Partido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(verbose_name='Fecha y hora')),
                ('goles_local', models.PositiveIntegerField(default=0, verbose_name='Goles local')),
                ('goles_visitante', models.PositiveIntegerField(default=0, verbose_name='Goles visitante')),
                ('estado', models.CharField(choices=[('programado', 'Programado'), ('finalizado', 'Finalizado'), ('cancelado', 'Cancelado')], default='programado', max_length=20, verbose_name='Estado')),
                ('equipo_local', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partidos_local', to='equipos.equipo')),
                ('equipo_visitante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partidos_visitante', to='equipos.equipo')),
            ],
            options={
                'verbose_name': 'Partido',
                'verbose_name_plural': 'Partidos',
                'ordering': ['fecha'],
            },
        ),
    ]
