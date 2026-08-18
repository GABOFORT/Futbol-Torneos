
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torneos', '0017_torneo'),
    ]

    operations = [
        migrations.AddField(
            model_name='palmares',
            name='es_torneo',
            field=models.BooleanField(default=False, verbose_name='Torneo relámpago'),
        ),
    ]
