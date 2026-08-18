
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0006_partido_fecha_original'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partido',
            name='estado',
            field=models.CharField(choices=[('programado', 'Programado'), ('reprogramado', 'Reprogramado'), ('finalizado', 'Finalizado'), ('cancelado', 'Cancelado')], default='programado', max_length=20, verbose_name='Estado'),
        ),
    ]
