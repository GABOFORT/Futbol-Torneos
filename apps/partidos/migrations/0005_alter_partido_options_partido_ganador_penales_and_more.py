
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipos', '0006_alter_equipo_entrenador'),
        ('partidos', '0004_alter_partido_fecha'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='partido',
            options={'ordering': ['jornada', 'fecha', 'id'], 'verbose_name': 'Partido', 'verbose_name_plural': 'Partidos'},
        ),
        migrations.AddField(
            model_name='partido',
            name='ganador_penales',
            field=models.ForeignKey(blank=True, help_text='Solo cuando el partido termina empatado. Suma un punto extra.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='penales_ganados', to='equipos.equipo', verbose_name='Ganador de los penales'),
        ),
        migrations.AddField(
            model_name='partido',
            name='jornada',
            field=models.PositiveIntegerField(default=1, verbose_name='Jornada'),
        ),
    ]
