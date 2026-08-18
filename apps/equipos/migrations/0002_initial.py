
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('equipos', '0001_initial'),
        ('torneos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipo',
            name='categoria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipos', to='torneos.categoria'),
        ),
    ]
