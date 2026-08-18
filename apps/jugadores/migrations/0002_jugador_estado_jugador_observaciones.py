
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jugadores', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='jugador',
            name='estado',
            field=models.CharField(choices=[('activo', 'Activo'), ('baja', 'Baja'), ('lesion', 'Lesionado'), ('sancion', 'Sancionado')], default='activo', max_length=20, verbose_name='Estado del jugador'),
        ),
        migrations.AddField(
            model_name='jugador',
            name='observaciones',
            field=models.TextField(blank=True, verbose_name='Observaciones'),
        ),
    ]
