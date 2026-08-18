
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0015_partido_no_se_presento'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='cuadro',
            field=models.CharField(choices=[('principal', 'Liguilla principal'), ('consolacion', 'Mini-liguilla')], default='principal', help_text='En qué cuadro de eliminación se juega. Los del torneo regular quedan en el principal.', max_length=20, verbose_name='Cuadro'),
        ),
    ]
