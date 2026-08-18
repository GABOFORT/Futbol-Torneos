
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipos', '0006_alter_equipo_entrenador'),
        ('partidos', '0014_actuacion_goles_de_penal'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='no_se_presento',
            field=models.ForeignKey(blank=True, help_text='Si un equipo no llega, el rival gana por default 3-0.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ausencias', to='equipos.equipo', verbose_name='Equipo que no se presentó'),
        ),
    ]
