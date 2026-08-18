
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0004_categoria_activa_categoria_equipos_por_jornada_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='categoria',
            name='equipos_por_jornada',
        ),
        migrations.RemoveField(
            model_name='categoria',
            name='fase_grupos',
        ),
        migrations.RemoveField(
            model_name='categoria',
            name='formato',
        ),
        migrations.RemoveField(
            model_name='categoria',
            name='tiene_playoffs',
        ),
    ]
