
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('equipos', '0002_initial'),
        ('torneos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='equipo',
            name='entrenador',
            field=models.ForeignKey(limit_choices_to={'role': 'entrenador'}, on_delete=django.db.models.deletion.PROTECT, related_name='equipos', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='equipo',
            name='liga',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipos', to='torneos.liga'),
        ),
        migrations.AlterUniqueTogether(
            name='equipo',
            unique_together={('nombre', 'liga', 'categoria')},
        ),
    ]
