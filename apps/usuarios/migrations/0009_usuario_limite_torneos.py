
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0008_unaccent'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='limite_torneos',
            field=models.PositiveIntegerField(default=1, help_text='Cuántos torneos relámpago puede tener en curso a la vez. Los que ya terminaron no ocupan lugar.', verbose_name='Límite de torneos'),
        ),
    ]
