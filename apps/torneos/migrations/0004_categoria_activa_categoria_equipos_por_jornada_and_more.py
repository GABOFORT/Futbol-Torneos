
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0003_remove_partido_torneo_partido_categoria'),
        ('torneos', '0003_torneo_equipos_por_jornada_torneo_fase_grupos_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='activa',
            field=models.BooleanField(default=True, verbose_name='Categoría activa'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='equipos_por_jornada',
            field=models.PositiveIntegerField(default=2, verbose_name='Equipos por jornada'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='fase_grupos',
            field=models.BooleanField(default=False, verbose_name='Incluye fase de grupos'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='fecha_final',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de finalización'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='fecha_inicio',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de inicio'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='formato',
            field=models.CharField(choices=[('liga', 'Liga'), ('grupos', 'Fase de grupos'), ('eliminatorio', 'Eliminatorio')], default='liga', max_length=20, verbose_name='Formato de competencia'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='inscripcion_abierta',
            field=models.BooleanField(default=True, verbose_name='Inscripción abierta'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='reglas',
            field=models.TextField(blank=True, verbose_name='Reglas de la competencia'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='tiene_playoffs',
            field=models.BooleanField(default=False, verbose_name='Incluye playoffs'),
        ),
        migrations.AddField(
            model_name='liga',
            name='dias_gracia',
            field=models.PositiveIntegerField(default=3, verbose_name='Días de gracia'),
        ),
        migrations.AddField(
            model_name='liga',
            name='fecha_pago',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha del último pago'),
        ),
        migrations.DeleteModel(
            name='Torneo',
        ),
    ]
