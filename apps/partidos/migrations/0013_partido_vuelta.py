
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partidos', '0012_partido_penales_local_partido_penales_visitante'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='vuelta',
            field=models.BooleanField(default=False, help_text='La llave se juega ida y vuelta. La vuelta la recibe el mejor ubicado en la tabla.', verbose_name='Partido de vuelta'),
        ),
    ]
