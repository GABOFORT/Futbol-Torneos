
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0008_actuacion'),
        ('torneos', '0009_sede'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='sede',
            field=models.ForeignKey(blank=True, help_text='Dónde se juega. Se marca en el mapa al programar el partido.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='partidos', to='torneos.sede', verbose_name='Cancha'),
        ),
        migrations.AddField(
            model_name='partido',
            name='sede_original',
            field=models.ForeignKey(blank=True, help_text='Se guarda la primera vez que se asigna. Si después cambia, se avisa el cambio de cancha.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='partidos_mudados', to='torneos.sede', verbose_name='Cancha asignada al principio'),
        ),
    ]
