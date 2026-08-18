
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('equipos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Jugador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre')),
                ('apellido', models.CharField(max_length=100, verbose_name='Apellido')),
                ('documento', models.CharField(blank=True, max_length=50, verbose_name='Documento')),
                ('fecha_nacimiento', models.DateField(blank=True, null=True, verbose_name='Fecha de nacimiento')),
                ('posicion', models.CharField(choices=[('portero', 'Portero'), ('defensa', 'Defensa'), ('medio', 'Mediocampista'), ('delantero', 'Delantero')], default='medio', max_length=20, verbose_name='Posición')),
                ('numero', models.PositiveIntegerField(blank=True, null=True, verbose_name='Número')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jugadores', to='equipos.equipo')),
            ],
            options={
                'verbose_name': 'Jugador',
                'verbose_name_plural': 'Jugadores',
            },
        ),
    ]
