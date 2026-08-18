
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipos', '0003_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='equipo',
            name='estado',
        ),
        migrations.AddField(
            model_name='equipo',
            name='formacion',
            field=models.CharField(blank=True, choices=[('4-4-2', '4-4-2'), ('4-3-3', '4-3-3'), ('3-5-2', '3-5-2'), ('5-3-2', '5-3-2'), ('4-2-3-1', '4-2-3-1')], max_length=20, verbose_name='Formación'),
        ),
    ]
