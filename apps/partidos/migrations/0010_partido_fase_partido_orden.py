
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0009_partido_sede_partido_sede_original'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='fase',
            field=models.CharField(blank=True, choices=[('', 'Torneo regular'), ('cuartos', 'Cuartos de final'), ('semifinal', 'Semifinal'), ('tercero', 'Tercer lugar'), ('final', 'Final')], default='', help_text='Vacío es el torneo regular. Las demás son las rondas de la liguilla.', max_length=20, verbose_name='Fase'),
        ),
        migrations.AddField(
            model_name='partido',
            name='orden',
            field=models.PositiveIntegerField(default=0, help_text='Qué llave del cuadro ocupa. Define qué cruce alimenta a cuál en la ronda siguiente.', verbose_name='Posición en la ronda'),
        ),
    ]
