
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipos', '0006_alter_equipo_entrenador'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipo',
            name='jornada_ingreso',
            field=models.PositiveSmallIntegerField(blank=True, help_text='Solo si se inscribió con el calendario ya generado. Vacío es desde el inicio.', null=True, verbose_name='Entró en la jornada'),
        ),
    ]
