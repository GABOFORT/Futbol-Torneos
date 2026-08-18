
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0017_partido_fuera_de_jornada'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partido',
            name='fase',
            field=models.CharField(blank=True, choices=[('', 'Torneo regular'), ('octavos', 'Octavos de final'), ('cuartos', 'Cuartos de final'), ('semifinal', 'Semifinal'), ('tercero', 'Tercer lugar'), ('final', 'Final')], default='', help_text='Vacío es el torneo regular. Las demás son las rondas de la liguilla.', max_length=20, verbose_name='Fase'),
        ),
    ]
