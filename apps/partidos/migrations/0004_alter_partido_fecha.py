
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0003_remove_partido_torneo_partido_categoria'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partido',
            name='fecha',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fecha y hora'),
        ),
    ]
